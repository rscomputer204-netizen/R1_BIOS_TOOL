import json, os, sys
sys.path.insert(0, r"d:\BIOS_-TOOL")
from R1_CSME_Analyzer.r1_csme_parser import R1CSMEAnalyzer
from scripts.benchmark_hp import run_mea

HP_DIR = r"D:\SDD DATA\all bios\Bios\HP"

files_to_check = [
    r"01015fy00-388-g\dump_main.bin",
    r"6050A3059101-MB-A01 (A1)\New folder\read 9-6-22.bin",
    r"6050A3059101-MB-A01 (A1)\ok 100\read raju.bin",
    r"840_G5_6050A2945601-MB-A01(A1)\840 G4 7 JEN\g4 auto start.bin",
    r"850 g3\read bin.bin",
    r"HP ZBook 15 G5 Mobile Workstation DA0XW2MBAG0 XW2A\orginal read no power.bin",
    r"dv6 DA0LX6MB6H1 REV.H\ok clean main.bin",
    r"hp 840 g6 Crescent-6050A3022501-MB-A01 (A1)\read orginal bin.bin",
]

for rel in files_to_check:
    fpath = os.path.join(HP_DIR, rel)
    print("="*60)
    print("FILE:", rel)
    mea_res, _ = run_mea(fpath)
    r1 = R1CSMEAnalyzer(fpath).parse()
    print("MEA:", json.dumps(mea_res, indent=2))
    print("R1 :", json.dumps({
        "family": r1.get("family"),
        "version": r1.get("version"),
        "sku": r1.get("sku"),
        "chipset": r1.get("chipset"),
        "size_hex": r1.get("size_hex"),
        "full_tag": r1.get("full_tag"),
        "fw_type": r1.get("fw_type"),
        "has_ftpr": r1.get("has_ftpr")
    }, indent=2))
