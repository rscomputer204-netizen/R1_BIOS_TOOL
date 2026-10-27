#!/usr/bin/env python3
"""
=============================================================================
         R1 BIOS RESEARCH LAB - LENOVO KNOWLEDGE BUILDER
=============================================================================
This script generates the Lenovo ThinkPad and IdeaPad rules database & Bible:
  1. LENOVO_BIOS_REPAIR_BIBLE.md
  2. lenovo_rules_database.json
=============================================================================
"""

import os
import json
from datetime import datetime

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge_base")
os.makedirs(OUTPUT_DIR, exist_ok=True)

LENOVO_DOC_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "LENOVO_BIOS_REPAIR_BIBLE.md")
LENOVO_JSON_PATH = os.path.join(OUTPUT_DIR, "lenovo_rules_database.json")

LENOVO_RULES = [
    {
        "category": "PASSWORD_UNLOCK",
        "family": "ThinkPad Classic (4th to 8th Gen Intel)",
        "models": ["T440", "T450", "T460", "T460s", "T470", "T470s", "T480", "X240", "X250", "X260", "X270", "X280", "X1 Carbon Gen 2-6", "X1 Yoga"],
        "chip_size": "16 MB (Single SPI)",
        "technique": "AutoPatcher DXE Hook Method",
        "nvram_format": "EVSA (Extended Variable Storage Architecture)",
        "description": "ThinkPad stores the Supervisor Password (SVP) cryptographically linked to the embedded hardware security chip. A DXE driver patch hooks the authentication routine and forces an EVSA clear command.",
        "steps": [
            "1. Read original 16MB BIOS dump from SPI flash.",
            "2. Apply AutoPatcher DXE payload to replace auth hook and flush active NVRAM setup (0x00800000 - 0x0084C000 erased to 0xFF).",
            "3. Flash the patched binary to the motherboard.",
            "4. Power on laptop: custom screen with GIF89a banner appears. Press Space / Enter to execute SVP hardware wipe.",
            "5. Flash back the original BIOS dump. The machine boots 100% password-free."
        ],
        "target_signatures": ["EVSA", "just test", "GIF89a", "SvpVerify", "PasswordCheck"]
    },
    {
        "category": "PASSWORD_UNLOCK",
        "family": "ThinkPad Modern (8th to 11th Gen - Whiskey Lake / Tiger Lake)",
        "models": ["T490", "T490s", "T14 Gen 1", "T14 Gen 2", "X390", "X1 Carbon Gen 7-9"],
        "chip_size": "32 MB (Single SPI)",
        "technique": "32MB AutoPatcher DXE Hook Method",
        "nvram_format": "EVSA / UEFI NVRAM",
        "description": "Applied to 32MB SPI flash chips (such as MX25L25673G / W25Q256JV). Same 2-step DXE hook method tailored for 32MB address space (hook inserted at 0x01452000 - 0x01789000).",
        "target_signatures": ["EVSA", "Setup", "_FVH"]
    },
    {
        "category": "PASSWORD_UNLOCK",
        "family": "IdeaPad / Yoga Consumer (AMI / InsydeH2O)",
        "models": ["IdeaPad 320", "IdeaPad 330", "IdeaPad 3", "IdeaPad 5", "IdeaPad Gaming"],
        "chip_size": "8 MB / 16 MB",
        "technique": "Active NVRAM Flush / Donor Rebuild with DMI Transfer",
        "description": "IdeaPad series does not have an external SVP crypto chip. Password is held directly in the active NVRAM bank (AMITSESetup / Setup). Clearing the active NVRAM bank or transferring DMI to a clean vendor update binary unlocks the machine immediately.",
        "target_signatures": ["AMITSESetup", "Setup", "InsydeSetup", "LENOVO"]
    },
    {
        "category": "DMI_PROTECTION",
        "family": "All Lenovo Laptops",
        "models": ["ThinkPad & IdeaPad"],
        "chip_size": "All",
        "technique": "Lenovo DMI Block Preservation",
        "description": "Preserves Serial Number (e.g. 1S...), Machine Type Model (MTM), UUID, Board Serial and Windows OEM Product Key located in the DMI partition.",
        "target_signatures": ["LENOVO", "LNVN", "1S", "SDK0J40697"]
    }
]

def build_lenovo_knowledge():
    # Save JSON database
    with open(LENOVO_JSON_PATH, "w", encoding="utf-8") as jf:
        json.dump({"brand": "Lenovo", "rules_count": len(LENOVO_RULES), "rules": LENOVO_RULES, "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, jf, indent=2)
    print(f"[+] Lenovo JSON Database: {LENOVO_JSON_PATH}")
    
    # Save Markdown Bible
    lines = [
        "# 📖 Lenovo BIOS Forensic Repair & Unlock Bible",
        f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} by R1 BIOS Research Lab*",
        "",
        "## 📑 সূচিপত্র",
        "1. [Lenovo ThinkPad সুপারভাইজার পাসওয়ার্ড (SVP) আর্কিটেকচার](#1-lenovo-thinkpad-সুপারভাইজার-পাসওয়ার্ড-svp-আর্কিটেকচার)",
        "2. [ThinkPad AutoPatcher কাজের ধাপ ও প্রযুক্তি](#2-thinkpad-autopatcher-কাজের-ধাপ-ও-প্রযুক্তি)",
        "3. [Lenovo IdeaPad / Yoga কনজিউমার পাসওয়ার্ড আনলক](#3-lenovo-ideapad--yoga-কনজিউমার-পাসওয়ার্ড-আনলক)",
        "4. [Lenovo DMI ও মেশিন টাইপ মডেল (MTM) সুরক্ষা](#4-lenovo-dmi-ও-মেশিন-টাইপ-মডেল-mtm-সুরক্ষা)",
        "",
        "---",
        "",
        "## 1. Lenovo ThinkPad সুপারভাইজার পাসওয়ার্ড (SVP) আর্কিটেকচার",
        "",
        "- **প্ল্যাটফর্ম:** ThinkPad T440, T450, T460, T470, T480, T490, X240, X250, X260, X270, X280, X1 Carbon, X1 Yoga।",
        "- **সিকিউরিটি গঠন:** ThinkPad-এ পাসওয়ার্ড শুধুমাত্র বায়োসের ভেতরে থাকে না, এটি একটি আলাদা হার্ডওয়্যার সিকিউরিটি চিপ (EEPROM / TPM / EC) এর সাথে ক্রিপ্টোগ্রাফিক্যালি লিঙ্ক করা থাকে।",
        "- **NVRAM আর্কিটেকচার:** থিঙ্কপ্যাড ব্যবহার করে **EVSA (Extended Variable Storage Architecture)**।",
        "",
        "---",
        "",
        "## 2. ThinkPad AutoPatcher কাজের ধাপ ও প্রযুক্তি",
        "",
        "বাস্তব টেকনিশিয়ান ডাম্প (`read pass.bin` বনাম `read pass_PATCHED.bin`) বিশ্লেষণ করে দেখা গেছে:",
        "1. **প্যাচ ইনজেকশন:** বায়োস ডাম্পের DXE ড্রাইভার অংশে একটি স্পেশাল হুক কোড ইনজেক্ট করা হয় এবং ডার্টি এনভিরাম (`0x00800000 - 0x0084C000`) অংশটি `0xFF` করে দেওয়া হয়।",
        "2. **ফার্স্ট বুট ও ইরেজ:** প্যাচ করা বায়োস ফ্ল্যাশ করে অন করলে স্ক্রিনে `GIF89a` ব্যানার আসে। তখন Space / Enter চাপলে প্যাচ করা ড্রাইভারটি হার্ডওয়্যার সিকিউরিটি চিপে কমান্ড পাঠিয়ে সুপারভাইজার পাসওয়ার্ড মুছে ফেলে।",
        "3. **অরিজিনাল রিস্টোর:** ল্যাপটপ বন্ধ করে কাস্টমারের মূল বায়োস ডাম্পটি আবার ফ্ল্যাশ করে দিলে ল্যাপটপ চিরতরে ১০০% আনলক হয়ে যায়!",
        "",
        "---",
        "",
        "## 3. Lenovo IdeaPad / Yoga কনজিউমার পাসওয়ার্ড আনলক",
        "",
        "- **পার্থক্য:** IdeaPad (যেমন IdeaPad 320, 330, IdeaPad 3, 5)-এ ThinkPad-এর মতো জটিল হার্ডওয়্যার ক্রিপ্টো চিপ থাকে না।",
        "- **সমাধান:** এর পাসওয়ার্ড থাকে AMI Aptio বা InsydeH2O এর অ্যাক্টিভ এনভিরাম স্টোরে (`AMITSESetup` / `Setup`)।",
        "- **আনলক নিয়ম:** অ্যাক্টিভ NVRAM ব্যাংক ফ্ল্যাশ (`0xFF`) করে দিলে বা DMI রেখে ক্লিন স্টক আপডেট বসিয়ে দিলে পাসওয়ার্ড সরাসরি খুলে যায়।",
        "",
        "---",
        "",
        "## 4. Lenovo DMI ও মেশিন টাইপ মডেল (MTM) সুরক্ষা",
        "",
        "- লেনোভো ল্যাপটপে Machine Type Model (MTM যেমন: `20JD`, `20L5`), সিরিয়াল নাম্বার (`1S...`) এবং Windows Key সংরক্ষিত থাকে DMI ব্লকে।",
        "- যেকোনো প্যাচ বা আপডেটের সময় এই DMI ব্লক অপরিবর্তিত রাখতে হয়, যাতে ল্যাপটপ তার মূল পরিচয় ধরে রাখতে পারে।"
    ]
    
    with open(LENOVO_DOC_PATH, "w", encoding="utf-8") as df:
        df.write("\n".join(lines))
    print(f"[+] Lenovo Bible: {LENOVO_DOC_PATH}")

if __name__ == "__main__":
    build_lenovo_knowledge()
