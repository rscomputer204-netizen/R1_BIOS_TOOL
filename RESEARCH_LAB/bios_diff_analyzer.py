#!/usr/bin/env python3
"""
=============================================================================
             R1 BIOS RESEARCH LAB - ADVANCED FIRMWARE DIFF ANALYZER
=============================================================================
This tool compares a LOCKED BIOS dump with an UNLOCKED (or modified) BIOS dump.
It pinpoints:
  - Exact changed offsets and 4KB/64KB flash sector boundaries
  - Change patterns (e.g. ALL 0xFF / Flash Erased, ALL 0x00, Custom Replacement)
  - Security signatures (NvramActiveRegn, H_AuthVar, Setup, Passwords, etc.)
  - Detailed forensic hex dumps and ASCII/UTF-16 string inspection
  - Auto-generated Markdown report for documentation
=============================================================================
"""

import os
import sys
import re
import argparse
from datetime import datetime
from pathlib import Path

SECURITY_KEYWORDS = [
    # HP Security & NVRAM
    b"NvramActiveRegn", b"H_AuthVar", b"H_Hmacslt", b"H_SsStts", b"H_FbPolicy",
    b"H_IvtCtr", b"L_MpmPolcy", b"L_MudHash", b"H_Bup", b"PKheaders", b"MUKdata",
    # Generic UEFI & Password variables
    b"AdminPassword", b"SupervisorPassword", b"UserPassword", b"Setup",
    b"AMITSESetup", b"PasswordCheck", b"SysPassword", b"HddPassword",
    b"ClearPassword", b"LockState", b"SecurityConfig", b"AdminPasswordHash",
    # Dell / Lenovo / Asus / Acer signatures
    b"DellSecurity", b"LenovoSecurity", b"AsusSecurity", b"InsydeSetup",
    b"SystemAccess", b"PasswordSalt", b"SecurityFlashBox",
]

def format_size(bytes_val: int) -> str:
    if bytes_val < 1024:
        return f"{bytes_val} B"
    elif bytes_val < 1024 * 1024:
        return f"{bytes_val / 1024:.2f} KB"
    else:
        return f"{bytes_val / (1024 * 1024):.2f} MB"

def extract_strings(data: bytes, min_len: int = 4):
    ascii_re = rb"[A-Za-z0-9_\-\.\:\/\$\@\#\%\*\&]{" + str(min_len).encode() + rb",}"
    utf16_re = rb"(?:[A-Za-z0-9_\-\.\:\/]\x00){" + str(min_len).encode() + rb",}"
    
    ascii_matches = [m.decode('latin1', errors='ignore') for m in re.findall(ascii_re, data)]
    utf16_matches = [m.decode('utf-16le', errors='ignore') for m in re.findall(utf16_re, data)]
    return list(dict.fromkeys(ascii_matches + utf16_matches))

def hex_dump(data: bytes, base_offset: int, max_bytes: int = 256) -> str:
    lines = []
    length = min(len(data), max_bytes)
    for i in range(0, length, 16):
        chunk = data[i:i+16]
        hex_str = " ".join(f"{b:02X}" for b in chunk)
        ascii_str = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
        lines.append(f"{base_offset + i:08X}  {hex_str:<48}  |{ascii_str}|")
    if len(data) > max_bytes:
        lines.append(f"... ({len(data) - max_bytes:,} additional bytes truncated)")
    return "\n".join(lines)

def analyze_diff(locked_path: str, unlocked_path: str, report_dir: str = None):
    print("=" * 80)
    print("      R1 BIOS RESEARCH LAB - ADVANCED FIRMWARE DIFF ANALYZER")
    print("=" * 80)
    
    if not os.path.exists(locked_path):
        print(f"[ERROR] Locked file not found: {locked_path}")
        return
    if not os.path.exists(unlocked_path):
        print(f"[ERROR] Unlocked file not found: {unlocked_path}")
        return
        
    size1 = os.path.getsize(locked_path)
    size2 = os.path.getsize(unlocked_path)
    
    print(f"[*] Locked File:   {locked_path}")
    print(f"    Size:          {size1:,} bytes ({format_size(size1)})")
    print(f"[*] Unlocked File: {unlocked_path}")
    print(f"    Size:          {size2:,} bytes ({format_size(size2)})")
    
    if size1 != size2:
        print("[!] WARNING: Files have different sizes!")
        
    print("\n[*] Reading files into memory...")
    with open(locked_path, "rb") as f1, open(unlocked_path, "rb") as f2:
        d1 = f1.read()
        d2 = f2.read()
        
    min_len = min(len(d1), len(d2))
    diff_indices = [i for i in range(min_len) if d1[i] != d2[i]]
    total_diffs = len(diff_indices)
    
    print(f"[*] Total differing bytes: {total_diffs:,} bytes ({total_diffs / min_len * 100:.4f}% of image)")
    
    if total_diffs == 0:
        print("[SUCCESS] Files are 100% IDENTICAL. No changes detected.")
        return

    # Group into continuous blocks (merge gaps <= 16 bytes for cleaner block views)
    blocks = []
    start = diff_indices[0]
    prev = diff_indices[0]
    
    for idx in diff_indices[1:]:
        if idx - prev <= 16:  # merge small gaps (e.g. single 0xFF bytes)
            prev = idx
        else:
            blocks.append((start, prev, prev - start + 1))
            start = idx
            prev = idx
    blocks.append((start, prev, prev - start + 1))
    
    print(f"[*] Found {len(blocks)} distinct diff block(s):\n")
    
    report_lines = []
    report_lines.append("# R1 BIOS Security Analysis Report")
    report_lines.append(f"- **Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"- **Locked File:** `{locked_path}` ({format_size(size1)})")
    report_lines.append(f"- **Unlocked File:** `{unlocked_path}` ({format_size(size2)})")
    report_lines.append(f"- **Total Changed Bytes:** {total_diffs:,} bytes ({total_diffs / min_len * 100:.4f}%)")
    report_lines.append(f"- **Total Changed Blocks:** {len(blocks)}\n")
    report_lines.append("## Changed Blocks Summary Table\n")
    report_lines.append("| Block | Start Offset | End Offset | Length | Flash 4KB Sector | Modification Pattern |")
    report_lines.append("|:---:|:---:|:---:|:---:|:---:|:---|")
    
    block_details = []
    
    for idx, (b_start, b_end, b_len) in enumerate(blocks):
        sub1 = d1[b_start:b_end+1]
        sub2 = d2[b_start:b_end+1]
        
        # Sector alignment
        sector_start = (b_start // 0x1000) * 0x1000
        sector_end = ((b_end // 0x1000) + 1) * 0x1000 - 1
        sector_info = f"0x{sector_start:08X} - 0x{sector_end:08X}"
        
        # Check patterns
        if all(b == 0xFF for b in sub2):
            pattern = "ALL 0xFF (FLASH ERASED)"
        elif all(b == 0x00 for b in sub2):
            pattern = "ALL 0x00 (ZEROED)"
        elif all(b == 0xFF for b in sub1):
            pattern = "ORIGINAL WAS 0xFF (DATA WRITTEN)"
        else:
            ff_pct = sum(1 for b in sub2 if b == 0xFF) / b_len * 100
            pattern = f"Custom Replacement ({ff_pct:.1f}% 0xFF)"
            
        print(f"--- Block #{idx+1} ----------------------------------------------------")
        print(f"  Range:         0x{b_start:08X} to 0x{b_end:08X} ({b_len:,} bytes)")
        print(f"  Flash Sector:  {sector_info} (4KB alignment)")
        print(f"  Pattern:       {pattern}")
        
        # Keywords check in locked vs unlocked
        found_kw_locked = [kw.decode('latin1') for kw in SECURITY_KEYWORDS if kw in sub1]
        found_kw_unlocked = [kw.decode('latin1') for kw in SECURITY_KEYWORDS if kw in sub2]
        
        if found_kw_locked:
            print(f"  [!] SECURITY SIGNATURES ERASED/MODIFIED: {found_kw_locked}")
        if found_kw_unlocked:
            print(f"  [!] SECURITY SIGNATURES ADDED IN UNLOCKED: {found_kw_unlocked}")
            
        # Strings found
        strings_locked = extract_strings(sub1)
        strings_unlocked = extract_strings(sub2)
        
        if strings_locked:
            print(f"  Strings in Locked Block (Sample): {strings_locked[:10]}")
            
        report_lines.append(f"| #{idx+1} | `0x{b_start:08X}` | `0x{b_end:08X}` | {b_len:,} B | `{sector_info}` | **{pattern}** |")
        
        block_details.append({
            "idx": idx + 1,
            "start": b_start,
            "end": b_end,
            "len": b_len,
            "sector": sector_info,
            "pattern": pattern,
            "kw_locked": found_kw_locked,
            "kw_unlocked": found_kw_unlocked,
            "strings_locked": strings_locked,
            "sub1": sub1,
            "sub2": sub2,
        })
        print()

    # Detailed section in report
    report_lines.append("\n## Detailed Block Analysis & Forensics\n")
    for b in block_details:
        report_lines.append(f"### Block #{b['idx']}: Offset `0x{b['start']:08X}` - `0x{b['end']:08X}`")
        report_lines.append(f"- **Size:** {b['len']:,} bytes")
        report_lines.append(f"- **Flash Sector (4KB):** `{b['sector']}`")
        report_lines.append(f"- **Modification Type:** {b['pattern']}")
        if b['kw_locked']:
            report_lines.append(f"- **Security Signatures Found (in Locked):** `{', '.join(b['kw_locked'])}`")
        if b['strings_locked']:
            report_lines.append(f"- **Extracted Variables/Strings:** `{', '.join(b['strings_locked'][:20])}`")
        report_lines.append("\n#### Hex Dump of Original (Locked):\n```text")
        report_lines.append(hex_dump(b['sub1'], b['start'], max_bytes=256))
        report_lines.append("```\n")
        report_lines.append("#### Hex Dump of Modified (Unlocked):\n```text")
        report_lines.append(hex_dump(b['sub2'], b['start'], max_bytes=256))
        report_lines.append("```\n")

    # Save report
    if report_dir:
        os.makedirs(report_dir, exist_ok=True)
        report_file = os.path.join(report_dir, f"diff_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
        with open(report_file, "w", encoding="utf-8") as rf:
            rf.write("\n".join(report_lines))
        print("=" * 80)
        print(f"[SUCCESS] Complete Markdown Report saved to:\n  -> {report_file}")
        print("=" * 80)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="R1 BIOS Research Lab - Firmware Diff Analyzer")
    parser.add_argument("-l", "--locked", help="Path to locked BIOS dump")
    parser.add_argument("-u", "--unlocked", help="Path to unlocked BIOS dump")
    parser.add_argument("-o", "--outdir", default=None, help="Directory to save markdown report")
    
    args = parser.parse_args()
    
    # Default test paths if no args given
    default_locked = r"C:\Users\R1 LAB\Desktop\LOCK BIOS\MX25L25633F@WSON8__Read pass__U365.BIN"
    default_unlocked = r"C:\Users\R1 LAB\Desktop\LOCK BIOS\unlock1__U365.bin"
    default_report_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
    
    locked = args.locked if args.locked else default_locked
    unlocked = args.unlocked if args.unlocked else default_unlocked
    outdir = args.outdir if args.outdir else default_report_dir
    
    analyze_diff(locked, unlocked, outdir)
