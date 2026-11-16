import sys
sys.path.insert(0, r"d:\BIOS_-TOOL")
from R1_CSME_Analyzer.r1_csme_parser import R1CSMEAnalyzer

fpath = r'D:\SDD DATA\all bios\Bios\HP\6050A3059101-MB-A01 (A1)\ok 100\read raju.bin'
parser = R1CSMEAnalyzer(fpath)
res = parser.parse()
print("size_hex:", res.get("size_hex"))
print("fw_type:", res.get("fw_type"))
print("fpt_found:", parser.info.get("fpt_found"))
print("me_fd_start:", hex(parser.info.get("me_fd_start", 0)))
print("has_ftpr:", parser.info.get("has_ftpr"))
print("cse_layout_table:", parser.info.get("cse_layout_table"))
