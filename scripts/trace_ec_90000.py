import sys
sys.path.insert(0, r"d:\BIOS_-TOOL")
from R1_CSME_Analyzer.r1_csme_parser import R1CSMEAnalyzer

a = R1CSMEAnalyzer(r'D:\SDD DATA\all bios\Bios\HP\10th gen_DA0X8LMB8D0 REV D\ec outside of ram 25B127DSIG.bin')
a.parse()
print("fpt_entries max end:", a.info.get("fpt_entries")[-1])
print("size_hex:", a.info.get("size_hex"))
