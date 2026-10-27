#!/usr/bin/env python3
"""
=============================================================================
         R1 BIOS RESEARCH LAB - HP KNOWLEDGE BASE & REPAIR RULES ENGINE
=============================================================================
This script scans real technician BIOS dumps from D:\SDD DATA\all bios\HP,
extracts ground-truth forensic repair patterns (Password, Error 34, MPM),
and writes a structured JSON database and an authoritative Markdown knowledge base.
=============================================================================
"""

import os
import sys
import json
import re
from datetime import datetime

HP_ROOT = r"D:\SDD DATA\all bios\HP"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge_base")
os.makedirs(OUTPUT_DIR, exist_ok=True)

JSON_DB_PATH = os.path.join(OUTPUT_DIR, "hp_rules_database.json")
DOC_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "HP_BIOS_REPAIR_BIBLE.md")

# Selected high-value test pairs across generations
KNOWN_PAIRS = [
    {
        "category": "PASSWORD_UNLOCK",
        "generation": "HP G6 (Whiskey Lake)",
        "model": "ZBook 14u G6 / 15u G6",
        "board": "6050A3022501-MB-A01",
        "chip_type": "EC_BIOS_16MB",
        "file_locked": r"D:\SDD DATA\all bios\HP\CRESCENT_G6 Editable Bios\Touch_zbook_creacent_14u_ g6_gfx_4bg_8th gen\read ec pass_W25Q128FV_ touch_GFX 4GB.bin",
        "file_fixed":  r"D:\SDD DATA\all bios\HP\CRESCENT_G6 Editable Bios\Touch_zbook_creacent_14u_ g6_gfx_4bg_8th gen\read ec edit_W25Q128FV_ touch_GFX 4GB",
        "description": "EC Password removal via 0x00037000 sector wipe"
    },
    {
        "category": "PASSWORD_UNLOCK",
        "generation": "HP G8 (Tiger Lake 11th Gen)",
        "model": "ProBook 440 G8",
        "board": "DAX8QAMB8D0 REV D",
        "chip_type": "EC_BIOS_32MB",
        "file_locked": r"D:\SDD DATA\all bios\HP\HP_ProBook_440 G8_DAX8QAMB8D0 REV D_11th gen\EC_Read ok_ Pass_.bin",
        "file_fixed":  r"D:\SDD DATA\all bios\HP\HP_ProBook_440 G8_DAX8QAMB8D0 REV D_11th gen\EC_Read ok_ Pass Unlock_.bin",
        "description": "G8 32MB EC Password removal via 0x00037000 sector wipe"
    },
    {
        "category": "PASSWORD_UNLOCK",
        "generation": "HP G8 (Tiger Lake 11th Gen)",
        "model": "ProBook 450 G8",
        "board": "Intel 11th Gen",
        "chip_type": "MAIN_BIOS_32MB",
        "file_locked": r"D:\SDD DATA\all bios\HP\ph probook 450 g8\read main pass.bin",
        "file_fixed":  r"D:\SDD DATA\all bios\HP\ph probook 450 g8\read main unpass.bin",
        "description": "ProBook 450 G8 password removal via 0x00037000 & 0x00038000 wipe"
    },
    {
        "category": "ERROR_34_FIX",
        "generation": "HP G6 (Whiskey Lake)",
        "model": "EliteBook x360 1040 G6",
        "board": "6050A3037501-MB-A01",
        "chip_type": "MAIN_BIOS_32MB",
        "file_locked": r"D:\SDD DATA\all bios\HP\HP EliteBook x360 1040 G6_6050A3037501-MB-A01\34 MESSAGE.BIN",
        "file_fixed":  r"D:\SDD DATA\all bios\HP\HP EliteBook x360 1040 G6_6050A3037501-MB-A01\read.bin",
        "description": "Error 34 fix: restored missing 16KB Secure Platform Certificate block at 0x018F4000"
    },
    {
        "category": "ERROR_34_FIX",
        "generation": "HP G6 (Whiskey Lake)",
        "model": "ZBook G6 Crescent",
        "board": "6050A3022501-MB-A01",
        "chip_type": "MAIN_BIOS_32MB",
        "file_locked": r"D:\SDD DATA\all bios\HP\CRESCENT_G6 Editable Bios\zBOOK\34 mess build.bin",
        "file_fixed":  r"D:\SDD DATA\all bios\HP\CRESCENT_G6 Editable Bios\zBOOK\r.bin",
        "description": "Error 34 fix: restored missing 16KB volume at 0x018F4000"
    },
    {
        "category": "ERROR_34_FIX",
        "generation": "HP G5 (Kaby Lake R)",
        "model": "EliteBook x360 1030 G5",
        "board": "6050A2930901-MB-A01",
        "chip_type": "MAIN_BIOS_32MB",
        "file_locked": r"D:\SDD DATA\all bios\HP\HP 1030_G5\333 34 message.bin",
        "file_fixed":  r"D:\SDD DATA\all bios\HP\HP 1030_G5\333.bin",
        "description": "Error 34 fix: restored missing Secure Boot Variable Signer block at 0x01AFC160"
    },
    {
        "category": "MPM_CLEAR",
        "generation": "HP G7 (Comet Lake 10th Gen)",
        "model": "ZBook Firefly 14 G7",
        "board": "6050A3136201-MB-A01",
        "chip_type": "MAIN_BIOS_32MB",
        "file_locked": r"D:\SDD DATA\all bios\HP\HP ZBook Firefly 14 G7 Mobile Workstation (2V1J6US)\5CG1206D1T_read no touch_cor i7 10th gen.bin",
        "file_fixed":  r"D:\SDD DATA\all bios\HP\HP ZBook Firefly 14 G7 Mobile Workstation (2V1J6US)\read no touch_MPM_Cleared.bin",
        "description": "MPM Mode clear: flipped UEFI UserCred state flag from 0x3F to 0x3C and payload 0x01 to 0x00"
    }
]

def analyze_pair(pair_info):
    f1 = pair_info["file_locked"]
    f2 = pair_info["file_fixed"]
    
    if not (os.path.exists(f1) and os.path.exists(f2)):
        return None
        
    s1 = os.path.getsize(f1)
    s2 = os.path.getsize(f2)
    if s1 != s2:
        return None
        
    with open(f1, "rb") as fp1, open(f2, "rb") as fp2:
        d1 = fp1.read()
        d2 = fp2.read()
        
    diffs = [i for i in range(len(d1)) if d1[i] != d2[i]]
    if not diffs:
        return None
        
    blocks = []
    start = diffs[0]
    prev = diffs[0]
    for idx in diffs[1:]:
        if idx - prev <= 16:
            prev = idx
        else:
            blocks.append((start, prev, prev - start + 1))
            start = idx
            prev = idx
    blocks.append((start, prev, prev - start + 1))
    
    analyzed_blocks = []
    for b_start, b_end, b_len in blocks:
        sub1 = d1[b_start:b_end+1]
        sub2 = d2[b_start:b_end+1]
        
        if all(b == 0xFF for b in sub2):
            pat = "ERASE_ALL_FF"
        elif all(b == 0x00 for b in sub2):
            pat = "ZERO_ALL_00"
        elif all(b == 0xFF for b in sub1):
            pat = "RESTORED_FROM_FF"
        else:
            pat = "BYTE_PATCH"
            
        # extract signatures
        sigs = []
        for s in [b"NvramActiveRegn", b"H_AuthVar", b"H_Hmacslt", b"H_SsStts", b"L_MpmPolcy", b"_FVH", b"UserCred"]:
            if s in sub1 or s in sub2:
                sigs.append(s.decode('latin1'))
                
        analyzed_blocks.append({
            "start_offset": f"0x{b_start:08X}",
            "end_offset": f"0x{b_end:08X}",
            "length": b_len,
            "pattern": pat,
            "signatures": sigs
        })
        
    return {
        "metadata": pair_info,
        "total_diff_bytes": len(diffs),
        "total_blocks": len(blocks),
        "blocks": analyzed_blocks
    }

def main():
    print("Building HP Forensic Knowledge Base from empirical dumps...")
    results = []
    for p in KNOWN_PAIRS:
        print(f"[*] Analyzing: {p['category']} -> {p['model']} ({p['chip_type']})...")
        res = analyze_pair(p)
        if res:
            results.append(res)
            print(f"    -> Success: {res['total_diff_bytes']:,} diff bytes in {res['total_blocks']} block(s)")
        else:
            print("    -> Skipped (files missing or identical)")
            
    # Write JSON database
    db_payload = {
        "generator": "R1 BIOS Tool - Forensic Knowledge Extractor",
        "date_created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "target_brand": "HP",
        "rules_count": len(results),
        "rules": results
    }
    
    with open(JSON_DB_PATH, "w", encoding="utf-8") as jf:
        json.dump(db_payload, jf, indent=2)
    print(f"\n[+] JSON Database saved to: {JSON_DB_PATH}")
    
    # Write authoritative Markdown Bible
    doc_lines = [
        "# 📖 HP BIOS Forensic Repair & Unlock Bible",
        f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} by R1 BIOS Research Lab*",
        "",
        "এই ডকুমেন্টে HP ল্যাপটপের বাস্তব ডাম্প (Real Dumps) বিশ্লেষণ করে পাসওয়ার্ড আনলক, Error 34 ফিক্স এবং MPM ক্লিয়ারিং-এর সার্বজনীন নিয়ম ও অফসেট লিপিবদ্ধ করা হয়েছে।",
        "",
        "---",
        "",
        "## 📑 সূচিপত্র",
        "1. [HP পাসওয়ার্ড আনলক নিয়মাবলী (G5, G6, G7, G8, G9, G10)](#1-hp-পাসওয়ার্ড-আনলক-নিয়মাবলী)",
        "2. [Error 34 / Endpoint Security Controller সমাধান](#2-error-34--endpoint-security-controller-সমাধান)",
        "3. [Manufacturing Programming Mode (MPM) আনলক স্টেট ক্লিয়ার](#3-manufacturing-programming-mode-mpm-আনলক-স্টেট-ক্লিয়ার)",
        "4. [পরীক্ষিত বাস্তব কেস হিস্ট্রি ও ডাটাবেস](#4-পরীক্ষিত-বাস্তব-কেস-হিস্ট্রি)",
        "",
        "---",
        "",
        "## 1. HP পাসওয়ার্ড আনলক নিয়মাবলী",
        "",
        "### 🎯 মূল আর্কিটেকচার:",
        "- **সিঙ্গেল চিপ (Single SPI):** সাধারণত ৩২ MB চিপ থাকে। পাসওয়ার্ড `0x00037000` অফসেটে `NvramActiveRegn` ব্লকে থাকে।",
        "- **ডুয়াল চিপ (Dual SPI):** ১৬ MB (EC) + ৩২ MB (Main)। **পাসওয়ার্ড কখনো ৩২ MB মেইন বায়োসে থাকে না!** পাসওয়ার্ড থাকে **১৬ MB EC চিপের `0x00037000` অফসেটে**।",
        "",
        "### ⚡ আনলক অ্যাকশন (Rule):",
        "1. চিপের **`0x00037000`** হতে **`0x00037FFF`** (৪ KB সেক্টর) অংশটি পরীক্ষা করুন।",
        "2. যদি এতে `NvramActiveRegn`, `H_AuthVar`, `H_Hmacslt` থাকে, তবে এই ৪ KB অংশকে সম্পূর্ণ **`0xFF`** করে দিন।",
        "3. **সাবধানতা:** `0x00038000` (`L_MpmPolcy`) এবং `0x00064000` (`PKheaders`) স্পর্শ করবেন না। এতে DMI, Serial Number ও Windows Key শতভাগ অক্ষত থাকে।",
        "",
        "---",
        "",
        "## 2. Error 34 / Endpoint Security Controller সমাধান",
        "",
        "### 🔍 সমস্যার লক্ষণ:",
        "ল্যাপটপ অন করলে ৩ মিনিট ফ্যান ফুল স্পিডে ঘুরে বা স্ক্রিনে ওয়ার্নিং মেসেজ দেয়:  ",
        "`HP Sure Start detected an unauthorized change / Endpoint Security Controller 34 error`",
        "",
        "### 💡 মূল কারণ ও সমাধান:",
        "- বায়োস বিল্ড বা ক্লিন করার সময় মেইন বায়োসের **`0x018F4000` হতে `0x018F7FFF`** (বা ১০৩০ G5 এ `0x01AFC000`) অংশে থাকা **১৬ KB Secure Platform Certificate / Volume** মুছে গিয়ে `0xFF` হয়ে যায়।",
        "- **সমাধান রুল:** অফিসিয়াল ক্লিন ডাম্প থেকে এই ১৬ KB অংশ কপি করে ক্ষতিগ্রস্ত ফাইলের `0x018F4000` এ পেস্ট করলেই Error 34 চিরতরে দূর হয়ে যায়।",
        "",
        "---",
        "",
        "## 3. Manufacturing Programming Mode (MPM) আনলক স্টেট ক্লিয়ার",
        "",
        "### 🔍 সমস্যার লক্ষণ:",
        "প্রতিবার অন করার সময় লাল অক্ষরে ওয়ার্নিং আসে: *\"Manufacturing Programming Mode is in Unlock State\"*।",
        "",
        "### 💡 সমাধান রুল:",
        "UEFI NVRAM Variable স্টোরে `UserCred` ভেরিয়েবলের স্টেট ফ্ল্যাগ **`0x3F`** (`VAR_ADDED`) থেকে কমিয়ে **`0x3C`** (`VAR_DELETED`) করে দিলে সিস্টেম MPM মোড লক করে দেয় এবং ওয়ার্নিং চলে যায়।",
        "",
        "---",
        "",
        "## 4. পরীক্ষিত বাস্তব কেস হিস্ট্রি\n"
    ]
    
    for r in results:
        meta = r["metadata"]
        doc_lines.append(f"### 📌 কেস: {meta['model']} ({meta['generation']})")
        doc_lines.append(f"- **ক্যাটাগরি:** `{meta['category']}`")
        doc_lines.append(f"- **মাদারবোর্ড:** `{meta['board']}`")
        doc_lines.append(f"- **টার্গেট চিপ:** `{meta['chip_type']}`")
        doc_lines.append(f"- **মোট পরিবর্তিত বাইট:** {r['total_diff_bytes']:,} বাইট ({r['total_blocks']} টি ব্লকে)")
        doc_lines.append(f"- **বর্ণনা:** {meta['description']}")
        doc_lines.append("\n| ব্লক | শুরুর অফসেট | শেষের অফসেট | সাইজ | প্যাটার্ন | সিগনেচার |")
        doc_lines.append("|:---:|:---:|:---:|:---:|:---:|:---|")
        for b in r["blocks"]:
            sigs = ", ".join(b["signatures"]) if b["signatures"] else "None"
            doc_lines.append(f"| {b['start_offset']} | {b['end_offset']} | {b['length']:,} B | **{b['pattern']}** | `{sigs}` |")
        doc_lines.append("\n---\n")
        
    with open(DOC_PATH, "w", encoding="utf-8") as df:
        df.write("\n".join(doc_lines))
    print(f"[+] Knowledge Base Markdown Bible saved to: {DOC_PATH}")

if __name__ == "__main__":
    main()
