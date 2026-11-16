import sys
sys.path.insert(0, r'd:\BIOS_-TOOL')
from scripts.benchmark_hp import run_mea

fpath = r'D:\SDD DATA\all bios\Bios\HP\6930p\read bin.bin'
res, err = run_mea(fpath)
print("MEA:", res)
