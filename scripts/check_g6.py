import sys
sys.path.insert(0, r"d:\BIOS_-TOOL")
from R1_CSME_Analyzer.r1_csme_parser import R1CSMEAnalyzer

fpath = r'D:\SDD DATA\all bios\Bios\HP\hp 840 g6 Crescent-6050A3022501-MB-A01 (A1)\HP 840 G6 crescent-6050a3022501-mb-a01\New folder\Orig+R70_010600\nasir\g6.bin'
p = R1CSMEAnalyzer(fpath)
res = p.parse()
print("fpt_found:", p.info.get("fpt_found"))
print("fw_type:", p.info.get("fw_type"))
print("full_tag:", p.info.get("full_tag"))
