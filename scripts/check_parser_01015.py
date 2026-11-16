import sys
sys.path.insert(0, r"d:\BIOS_-TOOL")
from R1_CSME_Analyzer.r1_csme_parser import R1CSMEAnalyzer

fpath = r'D:\SDD DATA\all bios\Bios\HP\01015fy00-388-g\dump_main.bin'
parser = R1CSMEAnalyzer(fpath)
res = parser.parse()
print("me_fd_start:", hex(parser.info.get("me_fd_start", -1)))
print("me_fd_end:", hex(parser.info.get("me_fd_end", -1)))
print("found_fpts:", [hex(p) for p in parser.info.get("found_fpts", [])])
print("fw_type:", parser.info.get("fw_type"))
print("full_tag:", parser.info.get("full_tag"))
