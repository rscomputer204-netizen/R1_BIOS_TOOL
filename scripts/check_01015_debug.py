import sys
sys.path.insert(0, r"d:\BIOS_-TOOL")
from R1_CSME_Analyzer.r1_csme_parser import R1CSMEAnalyzer

fpath = r'D:\SDD DATA\all bios\Bios\HP\01015fy00-388-g\dump_main.bin'
p = R1CSMEAnalyzer(fpath)
res = p.parse()
print("fpt_found:", p.info.get("fpt_found"))
print("fw_type:", p.info.get("fw_type"))
print("full_tag:", p.info.get("full_tag"))
print("size_hex:", p.info.get("size_hex"))
