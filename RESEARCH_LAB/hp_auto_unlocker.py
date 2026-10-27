#!/usr/bin/env python3
"""
=============================================================================
             R1 BIOS RESEARCH LAB - HP SURE START PASSWORD UNLOCKER
=============================================================================
This engine automatically detects and removes the BIOS Administrator Password
from HP EliteBook, ProBook, and ZBook (Intel & AMD) BIOS dumps.

Technique:
  - Scans for HP Security NVRAM sectors ('NvramActiveRegn')
  - Targets specifically the sector containing 'H_AuthVar' & 'H_Hmacslt'
  - Safely preserves 'L_MpmPolcy' (MPM) and Platform Keys ('PKheaders')
  - Safely preserves DMI, Windows keys, and ME / PSP regions
  - Erases only the targeted 4KB Auth sector with 0xFF
=============================================================================
"""

import os
import sys
import re
import argparse
from datetime import datetime

def unlock_hp_bios(input_file: str, output_file: str = None) -> bool:
    print("=" * 80)
    print("      R1 BIOS RESEARCH LAB - HP SURE START AUTOMATED UNLOCKER")
    print("=" * 80)
    
    if not os.path.exists(input_file):
        print(f"[ERROR] File not found: {input_file}")
        return False
        
    file_size = os.path.getsize(input_file)
    print(f"[*] Input File: {input_file} ({file_size:,} bytes)")
    
    with open(input_file, "rb") as f:
        data = bytearray(f.read())
        
    print("[*] Scanning for HP Security NVRAM sectors ('NvramActiveRegn')...")
    
    pattern = b"NvramActiveRegn"
    matches = [m.start() for m in re.finditer(pattern, data)]
    
    if not matches:
        print("[!] No 'NvramActiveRegn' signatures found. This file may not be an HP Sure Start BIOS or has a different format.")
        return False
        
    print(f"[*] Found {len(matches)} 'NvramActiveRegn' sector(s) at offsets:")
    for m in matches:
        print(f"    - 0x{m:08X}")
        
    # Find the specific sector containing password auth variables: H_AuthVar, H_Hmacslt
    target_sector = None
    for m in matches:
        # Check 4KB sector (0x1000 bytes)
        sector_data = data[m : m + 0x1000]
        has_auth = (b"H_AuthVar" in sector_data) or (b"H_Hmacslt" in sector_data)
        is_mpm = (b"L_MpmPolcy" in sector_data)
        is_keys = (b"PKheaders" in sector_data)
        
        if has_auth and not is_mpm and not is_keys:
            target_sector = m
            print(f"\n[+] TARGET AUTH SECTOR IDENTIFIED: 0x{target_sector:08X} (4KB)")
            print(f"    - Contains: 'H_AuthVar' / 'H_Hmacslt'")
            print(f"    - Excludes MPM and Platform Keys (SAFE TO ERASE)")
            break
            
    if target_sector is None:
        print("\n[!] Could not locate an auth sector with H_AuthVar/H_Hmacslt.")
        print("    The BIOS might already be unlocked, or password is stored elsewhere.")
        return False
        
    # Safety Check: ensure sector size is 0x1000 (4KB)
    sector_len = 0x1000
    original_sector = data[target_sector : target_sector + sector_len]
    non_ff_bytes = sum(1 for b in original_sector if b != 0xFF)
    
    print(f"[*] Sector contains {non_ff_bytes:,} bytes of active data to be erased.")
    
    # Perform erase (fill with 0xFF)
    data[target_sector : target_sector + sector_len] = b'\xFF' * sector_len
    print(f"[+] Sector 0x{target_sector:08X} to 0x{target_sector + sector_len - 1:08X} wiped with 0xFF.")
    
    if not output_file:
        base, ext = os.path.splitext(input_file)
        output_file = f"{base}_UNLOCKED{ext}"
        
    with open(output_file, "wb") as f_out:
        f_out.write(data)
        
    print(f"\n[SUCCESS] Unlocked BIOS saved to:\n  -> {output_file}")
    print("=" * 80)
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HP Sure Start Automated Password Unlocker")
    parser.add_argument("input", nargs="?", default=r"C:\Users\R1 LAB\Desktop\LOCK BIOS\MX25L25633F@WSON8__Read pass__U365.BIN", help="Path to locked HP BIOS")
    parser.add_argument("-o", "--output", help="Path for unlocked output file")
    
    args = parser.parse_args()
    unlock_hp_bios(args.input, args.output)
