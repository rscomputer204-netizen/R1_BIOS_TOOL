import os, glob, json, sys
sys.path.insert(0, r"d:\BIOS_-TOOL")
from R1_CSME_Analyzer.r1_csme_parser import R1CSMEAnalyzer
from scripts.benchmark_hp import run_mea

LENOVO_DIR = r"D:\SDD DATA\all bios\Bios\LENOVO"
files = glob.glob(os.path.join(LENOVO_DIR, "**", "*.*"), recursive=True)
valid_exts = {".bin", ".rom", ".fl1", ".fd", ""}
files = [f for f in files if os.path.splitext(f)[1].lower() in valid_exts and not f.endswith(".txt")]

count_unconf = 0
for f in files[:50]:
    r1 = R1CSMEAnalyzer(f).parse()
    if r1.get("family") == "CSE ME":
        mfs = r1.get("mfs_state")
        if mfs in ("Error", "Unconfigured"):
            count_unconf += 1
            mea_res, _ = run_mea(f)
            print(os.path.basename(f), "MFS:", mfs)
            print("MEA Chipset Support:", mea_res.get("Chipset Support"))
            print("MEA Chipset:", mea_res.get("Chipset"))
            print("R1 Chipset:", r1.get("chipset"))
print(f"Total unconfigured/error in first 50: {count_unconf}")
