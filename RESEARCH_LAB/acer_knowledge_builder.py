#!/usr/bin/env python3
"""
=============================================================================
         R1 BIOS RESEARCH LAB - ACER KNOWLEDGE BUILDER
=============================================================================
This script generates the ACER rules database & Bible:
  1. ACER_BIOS_REPAIR_BIBLE.md
  2. acer_rules_database.json
=============================================================================
"""

import os
import json
from datetime import datetime

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge_base")
os.makedirs(OUTPUT_DIR, exist_ok=True)

ACER_DOC_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ACER_BIOS_REPAIR_BIBLE.md")
ACER_JSON_PATH = os.path.join(OUTPUT_DIR, "acer_rules_database.json")

ACER_RULES = [
    {
        "category": "PASSWORD_UNLOCK",
        "family": "Acer Aspire / Nitro / Predator / Swift / Spin",
        "models": ["Aspire 3", "Aspire 5", "Aspire 7", "Nitro 5", "Predator Helios", "Swift 3", "Spin 5"],
        "chip_size": "8 MB / 16 MB / 32 MB",
        "bios_vendor": "InsydeH2O (Insyde Software)",
        "technique": "Insyde NVRAM VSS / Active Variable Bank Reset",
        "description": "Acer exclusively utilizes InsydeH2O UEFI BIOS across almost all consumer and gaming laptops. Passwords and security flags are maintained in the Insyde Variable Storage Subsystem (VSS).",
        "mechanisms": [
            "Method 1 (NVRAM Flush): Locate the dirty active NVRAM variable bank containing 'PasswordCheck' and 'AdminPassword'. Erasing this bank to 0xFF forces InsydeH2O upon next cold boot to regenerate pristine NVRAM defaults (Password Disabled).",
            "Method 2 (Clean Factory Update Rebuild): Official Acer update packages (.fd / .bin) contain clean decompressed BIOS volumes without passwords. Technicians inject the user's DMI partition (Serial Number, SNID, UUID, Windows Key) into the clean factory image and flash."
        ],
        "target_signatures": ["$H2O", "Insyde", "PasswordCheck", "AdminPassword", "UserPassword", "CustomSetup"]
    },
    {
        "category": "DMI_PROTECTION",
        "family": "All Acer Laptops",
        "models": ["Aspire, Nitro, Predator, Swift, Spin, Extensa"],
        "chip_size": "All",
        "technique": "Acer DMI & SNID Extraction & Preservation",
        "description": "Preserves Acer 22-character Serial Number (e.g. NXM... / NHM...), 11-digit numeric SNID, Motherboard UUID and Windows OEM license key.",
        "target_signatures": ["$DMI$", "NX.", "NH.", "SNID", "Acer"]
    }
]

def build_acer_knowledge():
    with open(ACER_JSON_PATH, "w", encoding="utf-8") as jf:
        json.dump({"brand": "Acer", "rules_count": len(ACER_RULES), "rules": ACER_RULES, "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, jf, indent=2)
    print(f"[+] Acer JSON Database: {ACER_JSON_PATH}")
    
    lines = [
        "# 📖 ACER BIOS Forensic Repair & Unlock Bible",
        f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} by R1 BIOS Research Lab*",
        "",
        "## 📑 সূচিপত্র",
        "1. [ACER InsydeH2O পাসওয়ার্ড আর্কিটেকচার](#1-acer-insydeh2o-পাসওয়ার্ড-আর্কিটেকচার)",
        "2. [ACER পাসওয়ার্ড আনলক মেকানিজম (২টি কার্যকর পদ্ধতি)](#2-acer-পাসওয়ার্ড-আনলক-মেকানিজম)",
        "3. [ACER DMI, SNID এবং সিরিয়াল নাম্বার সুরক্ষা](#3-acer-dmi-snid-এবং-সিরিয়াল-নাম্বার-সুরক্ষা)",
        "",
        "---",
        "",
        "## 1. ACER InsydeH2O পাসওয়ার্ড আর্কিটেকচার",
        "",
        "- **প্ল্যাটফর্ম:** Acer Aspire, Nitro, Predator, Swift, Spin, Extensa, TravelMate।",
        "- **কোর ইঞ্জিন:** এসার ল্যাপটপের ৯৫% মডেলেই **InsydeH2O (Insyde Software)** UEFI বায়োস ফ্রেমওয়ার্ক ব্যবহার করা হয়।",
        "- **পাসওয়ার্ড স্টোরেজ:** এসার কোনো হার্ডওয়্যার সিকিউরিটি চিপে পাসওয়ার্ড রাখে না। পাসওয়ার্ড জমা থাকে **Insyde NVRAM VSS (Variable Storage Subsystem)** ব্লকের ভেতর `PasswordCheck`, `AdminPassword` এবং `InsydeSetup` ভেরিয়েবলে।",
        "",
        "---",
        "",
        "## 2. ACER পাসওয়ার্ড আনলক মেকানিজম",
        "",
        "বাস্তব ডাম্প পর্যালোচনায় টেকনিশিয়ানরা এসারে ২টি প্রমাণিত মেথড ব্যবহার করে:",
        "",
        "### মেথড ১: অ্যাক্টিভ NVRAM ব্যাংক ফ্ল্যাশ (Direct NVRAM Reset)",
        "- **পদ্ধতি:** এনভিরাম ভলিউমের ভেতরে যে সেক্টরে ইউজার ডার্টি সেটিংস এবং `PasswordCheck` জমা হয় (যেমন অফসেট `0x007F8000` - `0x007F9000`), সেই নির্দিষ্ট ব্যাংকটি **`0xFF`** করে দেওয়া হয়।",
        "- **ফলাফল:** প্রথম কোল্ড বুটে InsydeH2O বায়োস কোনো ইউজার পাসওয়ার্ড খুঁজে না পেয়ে ফ্যাক্টরি ডিফল্ট কনফিগারেশন রিস্টোর করে সরাসরি পাসওয়ার্ড ছাড়া অন হয়।",
        "",
        "### মেথড ২: ক্লিন ফ্যাক্টরি বায়োস + DMI ইনজেকশন (Clean Update Rebuild)",
        "- এসার অফিশিয়াল ওয়েবসাইট থেকে রিলিজ করা ফার্মওয়্যার (`.fd` বা `.bin`) ১০০% ফ্রেশ ও পাসওয়ার্ডমুক্ত থাকে।",
        "- কাস্টমারের মূল বায়োস থেকে DMI ব্লক (সিরিয়াল, SNID, UUID, উইন্ডোজ কি) কেটে এনে ক্লিন ফ্যাক্টরি ফাইলে ইনজেক্ট করে ফ্ল্যাশ করলেই ল্যাপটপ একদম নতুনের মতো পাসওয়ার্ড-মুক্ত হয়ে যায়।",
        "",
        "---",
        "",
        "## 3. ACER DMI, SNID এবং সিরিয়াল নাম্বার সুরক্ষা",
        "",
        "- **সিরিয়াল নাম্বার ফরম্যাট:** এসারের সিরিয়াল সাধারণত ২২ ক্যারেক্টারের হয় (যেমন `NX...` বা `NH...`)।",
        "- **SNID:** ১১ ডিজিটের নিউমেরিক কোড যা ব্যাক কভারে লেখা থাকে।",
        "- এই তথ্যগুলো বায়োসের DMI ভলিউমে সংরক্ষিত থাকে। আনলক বা রিপেয়ারের সময় এই ব্লকটি অক্ষত রাখতে হয়।"
    ]
    
    with open(ACER_DOC_PATH, "w", encoding="utf-8") as df:
        df.write("\n".join(lines))
    print(f"[+] Acer Bible: {ACER_DOC_PATH}")

if __name__ == "__main__":
    build_acer_knowledge()
