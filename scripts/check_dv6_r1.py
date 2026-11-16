import sys
sys.path.insert(0, r"d:\BIOS_-TOOL")
from R1_CSME_Analyzer.r1_csme_parser import R1CSMEAnalyzer

fpath = r'D:\SDD DATA\all bios\Bios\HP\dv6 DA0LX6MB6H1 REV.H\ok clean main.bin'
parser = R1CSMEAnalyzer(fpath)
res = parser.parse()
for e in parser.info.get("fpt_entries", []):
    print(e)
print("R1 size_hex:", parser.info.get("size_hex"))
