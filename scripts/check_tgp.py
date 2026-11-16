import sys
sys.path.insert(0, r"d:\BIOS_-TOOL")
from R1_CSME_Analyzer.r1_csme_parser import R1CSMEAnalyzer
from scripts.benchmark_hp import run_mea

fpath = r'D:\SDD DATA\all bios\Bios\HP\440 G8 dax8qamb8d0 rev d\red pass ec rom.bin'
p = R1CSMEAnalyzer(fpath)
res = p.parse()
mea_res, _ = run_mea(fpath)
print("R1 mfs_state:", p.info.get("mfs_state"))
print("R1 has_ftpr:", p.info.get("has_ftpr"))
print("MEA Chipset Support:", mea_res.get("Chipset Support"))
print("MEA Chipset:", mea_res.get("Chipset"))
print("MEA Chipset Stepping:", mea_res.get("Chipset Stepping"))
