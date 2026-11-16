import sys
sys.path.insert(0, r"d:\BIOS_-TOOL")
from R1_CSME_Analyzer.r1_csme_parser import R1CSMEAnalyzer

fpath = r'D:\SDD DATA\all bios\Bios\HP\6050A3059101-MB-A01 (A1)\New folder\read 9-6-22.bin'
p = R1CSMEAnalyzer(fpath)
p.parse()
print("me_fd_start:", hex(p.info.get("me_fd_start", 0)))
