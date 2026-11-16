import json, os, random
from scripts.benchmark_hp import run_mea, get_candidate_files
from R1_CSME_Analyzer.r1_csme_parser import R1CSMEAnalyzer

with open(r"d:\BIOS_-TOOL\scripts\hp_benchmark_results.json", "r", encoding="utf-8") as f:
    old_res = json.load(f)

mismatched_files = {d["file"] for d in old_res.get("details", [])}
all_files = get_candidate_files()
HP_DIR = r"D:\SDD DATA\all bios\Bios\HP"

matched_files = [f for f in all_files if os.path.relpath(f, HP_DIR) not in mismatched_files]
print("Total previously matched files:", len(matched_files))

random.seed(42)
sample = random.sample(matched_files, 50)

regressions = 0
for fpath in sample:
    mea_res, _ = run_mea(fpath)
    if not mea_res: continue
    r1 = R1CSMEAnalyzer(fpath).parse()
    diffs = {}
    if r1.get("version") != mea_res.get("Version"):
        diffs["ver"] = f"{r1.get('version')} vs {mea_res.get('Version')}"
    if r1.get("sku") != mea_res.get("SKU"):
        diffs["sku"] = f"{r1.get('sku')} vs {mea_res.get('SKU')}"
    mea_chip = mea_res.get("Chipset") or mea_res.get("Chipset Support", "")
    if mea_chip and r1.get("chipset") != mea_chip:
        diffs["chip"] = f"{r1.get('chipset')} vs {mea_chip}"
    mea_size = mea_res.get("Size", "")
    if mea_size and r1.get("size_hex", "").upper() != mea_size.upper():
        diffs["size"] = f"{r1.get('size_hex')} vs {mea_size}"
    mea_tag = mea_res.get("MEA Database Name", "")
    if mea_tag and r1.get("full_tag") != mea_tag:
        diffs["tag"] = f"{r1.get('full_tag')} vs {mea_tag}"
    if diffs:
        print("REGRESSION in", os.path.basename(fpath), diffs)
        regressions += 1

print(f"Tested {len(sample)} sample files. Regressions: {regressions}")
