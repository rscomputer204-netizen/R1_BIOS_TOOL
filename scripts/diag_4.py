import os, sys
sys.path.insert(0, r"d:\BIOS_-TOOL")
from R1_CSME_Analyzer.r1_csme_parser import R1CSMEAnalyzer
from scripts.benchmark_hp import run_mea

fpaths = [
    r"D:\SDD DATA\all bios\Bios\HP\10th gen_DA0X8LMB8D0 REV D\ec outside of ram 25B127DSIG.bin",
    r"D:\SDD DATA\all bios\Bios\HP\440 G8 dax8qamb8d0 rev d\red pass ec rom.bin",
    r"D:\SDD DATA\all bios\Bios\HP\450 G6 DAX8JMB16E0 Rev E ok\rr.bin",
    r"D:\SDD DATA\all bios\Bios\HP\6050A2637901-MB-A02\HP_6050A2637901_Clear me.bin\HP_6050A2637901_Clear me.bin"
]

for fp in fpaths:
    print("="*60)
    print(os.path.basename(fp))
    mea_res, _ = run_mea(fp)
    r1 = R1CSMEAnalyzer(fp).parse()
    print("MEA:", mea_res.get("Chipset Support") or mea_res.get("Chipset"), mea_res.get("Size"), mea_res.get("MEA Database Name"))
    print("R1 :", r1.get("chipset"), r1.get("size_hex"), r1.get("full_tag"))
