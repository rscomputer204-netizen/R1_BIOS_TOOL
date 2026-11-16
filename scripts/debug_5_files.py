import os, sys
sys.path.insert(0, r"d:\BIOS_-TOOL")
from R1_CSME_Analyzer.r1_csme_parser import R1CSMEAnalyzer

test_files = [
    r"01015fy00-388-g\dump_main.bin",
    r"10th gen_DA0X8LMB8D0 REV D\clean test ok under side ram.bin",
    r"10th gen_DA0X8LMB8D0 REV D\ec outside of ram 25B127DSIG.bin",
    r"440 G8 dax8qamb8d0 rev d\red pass ec rom unlock",
    r"450 G6 DAX8JMB16E0 Rev E ok\rr.bin"
]

HP_DIR = r"D:\SDD DATA\all bios\Bios\HP"
for rel in test_files:
    fpath = os.path.join(HP_DIR, rel)
    print("="*60)
    print(rel)
    with open(fpath, "rb") as f:
        data = f.read()
    print("File len:", hex(len(data)))
    analyzer = R1CSMEAnalyzer(fpath)
    res = analyzer.parse()
    print("Version:", res.get("version"))
    print("Size hex:", res.get("size_hex"))
    print("FPT found:", analyzer.info.get("fpt_found"))
    print("FPT entries:", len(analyzer.info.get("fpt_entries", [])))
    print("me_fd_start:", hex(analyzer.info.get("me_fd_start", 0)), "me_fd_end:", hex(analyzer.info.get("me_fd_end", 0)))
    print("Warnings:", analyzer.info.get("warnings"))
