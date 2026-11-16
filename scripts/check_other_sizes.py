import sys
sys.path.insert(0, r'd:\BIOS_-TOOL')
from scripts.benchmark_hp import run_mea

files = [
    r'840 g1\25Q128_Clear me.bin',
    r'6050A2637901-MB-A02\HP_6050A2637901_Clear me.bin\HP_6050A2637901_Clear me.bin',
    r'dv6 DA0LX6MB6H1 REV.H\ok clean main.bin',
    r'6050A3059101-MB-A01 (A1)\New folder\read 9-6-22.bin'
]

HP_DIR = r"D:\SDD DATA\all bios\Bios\HP"
import os
for rel in files:
    fpath = os.path.join(HP_DIR, rel)
    res, _ = run_mea(fpath)
    print("---", rel, "---")
    print("  MEA:", res.get("Family"), res.get("Version"), res.get("SKU"), "Size:", res.get("Size"))
