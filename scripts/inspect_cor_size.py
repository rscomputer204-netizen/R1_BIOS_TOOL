import sys, os
sys.path.insert(0, r"d:\BIOS_-TOOL")
from R1_CSME_Analyzer.r1_csme_parser import R1CSMEAnalyzer

f = r"D:\SDD DATA\all bios\Bios\HP\17817-1\CSME 11.8 Repository r34\CSME 11.8 Repository r34\11.8.50.3399_COR_H_DA_PRD_RGN.bin"
p = R1CSMEAnalyzer(f)
p.parse()

print("File size:", hex(p.file_size))
print("FD start:", hex(p.info['me_fd_start']), "end:", hex(p.info['me_fd_end']))
print("FPT entries:")
for e in p.info['fpt_entries']:
    print(" ", e)
