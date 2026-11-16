import sys
sys.path.insert(0, r"d:\BIOS_-TOOL")
from R1_CSME_Analyzer.r1_csme_parser import R1CSMEAnalyzer

fpath = r'D:\SDD DATA\all bios\Bios\HP\HP ZBook 15 G5 Mobile Workstation DA0XW2MBAG0 XW2A\orginal read no power.bin'
p = R1CSMEAnalyzer(fpath)
# Let's see what cse_lt_max_end and fpt_max_end are
data = p.raw_data
print("fpt_entries:", p.info.get("fpt_entries"))
p.parse()
print("info size_hex:", p.info.get("size_hex"))
