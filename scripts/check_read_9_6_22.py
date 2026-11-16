import sys
sys.path.insert(0, r'd:\BIOS_-TOOL')
from scripts.benchmark_hp import run_mea

fpath = r'D:\SDD DATA\all bios\Bios\HP\6050A3059101-MB-A01 (A1)\New folder\read 9-6-22.bin'
res, err = run_mea(fpath)
print("MEA result for read 9-6-22.bin:")
for k, v in res.items():
    print(f"  {k}: {v}")
