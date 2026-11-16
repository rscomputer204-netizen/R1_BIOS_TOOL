import sys
sys.path.insert(0, r'd:\BIOS_-TOOL')
from R1_CSME_Analyzer.r1_csme_parser import R1CSMEAnalyzer

fpath = r'D:\SDD DATA\all bios\Bios\HP\6050A3059101-MB-A01 (A1)\New folder\read 9-6-22.bin'
a = R1CSMEAnalyzer(fpath)
a.parse()
print("me_fd_start:", hex(a.info.get("me_fd_start", 0)))
print("me_fd_end:", hex(a.info.get("me_fd_end", 0)))
print("me_fd_size:", hex(a.info.get("me_fd_end", 0) - a.info.get("me_fd_start", 0)))
print("size_hex:", a.info.get("size_hex"))
