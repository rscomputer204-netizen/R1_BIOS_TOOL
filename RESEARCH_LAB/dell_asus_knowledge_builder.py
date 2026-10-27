#!/usr/bin/env python3
"""
=============================================================================
         R1 BIOS RESEARCH LAB - DELL & ASUS KNOWLEDGE BUILDER
=============================================================================
This script processes empirical Dell and ASUS technician dumps to build:
  1. DELL_BIOS_REPAIR_BIBLE.md & dell_rules_database.json
  2. ASUS_BIOS_REPAIR_BIBLE.md & asus_rules_database.json
=============================================================================
"""

import os
import json
from datetime import datetime

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge_base")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# DELL DATABASE
DELL_DOC_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "DELL_BIOS_REPAIR_BIBLE.md")
DELL_JSON_PATH = os.path.join(OUTPUT_DIR, "dell_rules_database.json")

# ASUS DATABASE
ASUS_DOC_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ASUS_BIOS_REPAIR_BIBLE.md")
ASUS_JSON_PATH = os.path.join(OUTPUT_DIR, "asus_rules_database.json")

DELL_RULES = [
    {
        "category": "PASSWORD_UNLOCK",
        "platform": "Dell Inspiron / Vostro / Latitude (AMI Aptio V NVAR)",
        "model": "Dell 18827-1 (Latitude / Inspiron)",
        "chip_size": "32 MB",
        "technique": "AMI NVAR Security Variable Zeroing",
        "description": "Zeros AMITSESetup and __KEYM__ variables in the active NVRAM bank, removing Administrator & System passwords.",
        "target_signatures": ["AMITSESetup", "__KEYM__", "DellVar01", "NVAR"],
        "action": "Zero out (0x00) the password token / hash payload inside AMITSESetup and Key Manager (__KEYM__) while preserving DMI block (_WB_)."
    },
    {
        "category": "TPM_ERROR_FIX",
        "platform": "Dell Latitude 7480 / 7280 / 5480 (Skylake / Kaby Lake)",
        "model": "Latitude 7480",
        "chip_size": "16 MB",
        "technique": "CSME PTT Partition Re-initialization",
        "description": "Fixes 'Alert! TPM device is not detected' error by restoring clean Intel CSME 11.8 Corporate LP firmware and clearing initialized/corrupt PTT state.",
        "target_signatures": ["FTPM", "INTEL_PTT", "CSE", "CSME"],
        "action": "Clean Intel CSME Region (replace dirty ME region with clean configured repository donor binary). TPM 2.0 re-initializes upon next boot."
    },
    {
        "category": "DMI_PROTECTION",
        "platform": "Dell Latitude 5400 / 5500 (EDC41 / EDC50)",
        "model": "Latitude 5500",
        "chip_size": "32 MB",
        "technique": "Dell _WB_ Private Configuration Preservation",
        "description": "Dell Service Tag, PPID, Asset Tag and Windows Product Key are stored in the _WB_ block (typically at 0x010C4000 - 0x010C6FFF).",
        "target_signatures": ["_WB_", "PPID", "CN0M14W7CMK0001T17ACA01"],
        "action": "Never erase or overwrite the _WB_ block during Dell BIOS rebuilding/patching."
    }
]

ASUS_RULES = [
    {
        "category": "PASSWORD_UNLOCK",
        "platform": "ASUS ZenBook / VivoBook (AMI Aptio V)",
        "model": "ASUS UX310UV / UX3410U",
        "chip_size": "8 MB",
        "technique": "ASUS NVRAM Active Bank Flush",
        "description": "Clears administrator and user BIOS passwords by erasing the dirty NVRAM variable bank (offset 0x007BC000 - 0x007C5FFF) to 0xFF.",
        "target_signatures": ["AMITSESetup", "Setup", "_FVH"],
        "action": "Locate the primary active NVRAM bank containing user-modified AMITSESetup, and fill with 0xFF. BIOS automatically recovers default (password-free) setup from the default store upon next boot."
    },
    {
        "category": "DMI_PROTECTION",
        "platform": "ASUS Modern Laptops",
        "model": "ASUS VivoBook / ZenBook / ROG",
        "chip_size": "8 MB / 16 MB",
        "technique": "ASUS DMI Preservation ($ASUS$ / _SM_)",
        "description": "Preserves Serial Number, Motherboard UUID, MAC Address and Windows Product Key located in the DMI area.",
        "target_signatures": ["$ASUS$", "_DMI_", "_SM_"],
        "action": "Ensure the DMI block remains untouched during password clearing or donor injection."
    }
]

def build_all():
    # Write Dell JSON
    with open(DELL_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump({"brand": "Dell", "rules": DELL_RULES, "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, f, indent=2)
    print(f"[+] Dell JSON Database: {DELL_JSON_PATH}")
    
    # Write Dell Markdown
    dell_md = [
        "# 📖 Dell BIOS Forensic Repair & Unlock Bible",
        f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} by R1 BIOS Research Lab*",
        "",
        "## 1. Dell পাসওয়ার্ড আনলক আর্কিটেকচার",
        "- **প্ল্যাটফর্ম:** Dell Inspiron, Vostro, Latitude (AMI Aptio V NVAR আর্কিটেকচার)।",
        "- **পাসওয়ার্ড লোকেশন:** AMI NVAR ভেরিয়েবল স্টোরের ভেতরে `AMITSESetup` এবং `__KEYM__` (Key Manager)।",
        "- **আনলক মেকানিজম:** `AMITSESetup` এবং `__KEYM__` এর ভেতরে পাসওয়ার্ড হ্যাশ বাইটগুলোকে **`0x00` (Zeroed)** করতে হয়।",
        "- **সুরক্ষা:** DMI ও সার্ভিস ট্যাগ ব্লক (`_WB_`) অক্ষত থাকে।",
        "",
        "## 2. Dell 'TPM Not Detected' এরর ফিক্স",
        "- **লক্ষণ:** অন করার পর স্ক্রিনে আসে: `Alert! TPM device is not detected` অথবা বায়োসে TPM সেকশন সম্পূর্ণ গায়েব থাকে।",
        "- **কারণ:** Intel ME/CSME এর অভ্যন্তরীণ PTT (Platform Trust Technology) / FTPM এনভিরাম পার্টিশন করাপ্ট হয়ে যাওয়া।",
        "- **সমাধান:** Intel CSME Region ক্লিন করে `Configured` স্টেটে রি-বিল্ড করলে প্রথম বুটেই TPM 2.0 স্বয়ংক্রিয়ভাবে সক্রিয় হয়ে যায়।",
        "",
        "## 3. Dell DMI ও সার্ভিস ট্যাগ সুরক্ষা (_WB_ Block)",
        "- Dell ল্যাপটপে Service Tag, PPID এবং Windows Product Key সংরক্ষিত থাকে **`_WB_`** ব্লকে।",
        "- যেকোনো রিপেয়ারের সময় এই ব্লকটি ১০০% অক্ষত রাখতে হয়।",
    ]
    with open(DELL_DOC_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(dell_md))
    print(f"[+] Dell Bible: {DELL_DOC_PATH}")
    
    # Write ASUS JSON
    with open(ASUS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump({"brand": "ASUS", "rules": ASUS_RULES, "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, f, indent=2)
    print(f"[+] ASUS JSON Database: {ASUS_JSON_PATH}")
    
    # Write ASUS Markdown
    asus_md = [
        "# 📖 ASUS BIOS Forensic Repair & Unlock Bible",
        f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} by R1 BIOS Research Lab*",
        "",
        "## 1. ASUS পাসওয়ার্ড আনলক আর্কিটেকচার",
        "- **প্ল্যাটফর্ম:** ASUS ZenBook, VivoBook, ROG (AMI Aptio V)।",
        "- **পাসওয়ার্ড লোকেশন:** অ্যাক্টিভ NVRAM ভেরিয়েবল ব্যাংক (যেমন: `AMITSESetup`, `Setup`)।",
        "- **আনলক মেকানিজম:** অ্যাক্টিভ ডার্টি NVRAM ব্যাংকটি **`0xFF`** করে দিলে, ল্যাপটপ অন হওয়ার সময় ডিফল্ট রম স্টোর থেকে ফ্রেশ কনফিগারেশন নিয়ে পাসওয়ার্ড মুক্ত হয়ে বুট করে।",
        "- **DMI সুরক্ষা:** `$ASUS$` DMI ব্লক (সিরিয়াল, ম্যাক, উইন্ডোজ কি) অক্ষত রেখে কাজ করতে হয়।",
    ]
    with open(ASUS_DOC_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(asus_md))
    print(f"[+] ASUS Bible: {ASUS_DOC_PATH}")

if __name__ == "__main__":
    build_all()
