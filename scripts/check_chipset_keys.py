import json, os, sys
sys.path.insert(0, r"d:\BIOS_-TOOL")
from scripts.benchmark_hp import run_mea

files = [
    r"10th gen_DA0X8LMB8D0 REV D\clean test ok under side ram.bin",
    r"hp 840 g6 Crescent-6050A3022501-MB-A01 (A1)\read orginal bin.bin",
    r"840_G5_6050A2945601-MB-A01(A1)\840 G4 7 JEN\g4 auto start.bin",
    r"HP ZBook 15 G5 Mobile Workstation DA0XW2MBAG0 XW2A\orginal read no power.bin",
    r"dv6 DA0LX6MB6H1 REV.H\ok clean main.bin"
]

HP_DIR = r"D:\SDD DATA\all bios\Bios\HP"
for rel in files:
    fpath = os.path.join(HP_DIR, rel)
    mea_res, _ = run_mea(fpath)
    print("="*50)
    print("FILE:", rel)
    print("Chipset Support:", mea_res.get("Chipset Support"))
    print("Chipset:", mea_res.get("Chipset"))
    print("Chipset Stepping:", mea_res.get("Chipset Stepping"))
