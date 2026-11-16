import json, os, sys
sys.path.insert(0, r"d:\BIOS_-TOOL")
from R1_CSME_Analyzer.r1_csme_parser import R1CSMEAnalyzer
from scripts.benchmark_hp import run_mea

HP_DIR = r"D:\SDD DATA\all bios\Bios\HP"
with open(r"d:\BIOS_-TOOL\scripts\hp_benchmark_results.json") as f:
    old_data = json.load(f)

mismatches = old_data["details"]
print(f"Checking {len(mismatches)} files...")

remaining = []
for idx, item in enumerate(mismatches):
    rel_path = item["file"]
    fpath = os.path.join(HP_DIR, rel_path)
    if not os.path.exists(fpath):
        continue

    # Use run_mea to get ground truth
    mea_res, err = run_mea(fpath)
    if not mea_res:
        continue

    r1_parser = R1CSMEAnalyzer(fpath)
    r1_res = r1_parser.parse()

    mea_fam = mea_res.get("Family", "")
    mea_ver = mea_res.get("Version", "")
    mea_sku = mea_res.get("SKU", "")
    mea_chip = mea_res.get("Chipset Support") or mea_res.get("Chipset", "")
    mea_date = mea_res.get("Date", "")
    mea_size = mea_res.get("Size", "")
    mea_fitc = mea_res.get("Flash Image Tool", "")
    mea_tag = mea_res.get("MEA Database Name", "")

    r1_fam = r1_res.get("family", "")
    r1_ver = r1_res.get("version", "")
    r1_sku = r1_res.get("sku", "")
    r1_chip = r1_res.get("chipset", "")
    r1_date = r1_res.get("date", "")
    r1_size = r1_res.get("size_hex", "")
    r1_fitc = r1_res.get("fitc_ver", "")
    r1_tag = r1_res.get("full_tag", "")

    diffs = {}
    if r1_ver != mea_ver:
        diffs["version"] = f"R1={r1_ver} vs MEA={mea_ver}"
    if r1_sku != mea_sku:
        diffs["sku"] = f"R1={r1_sku} vs MEA={mea_sku}"
    if r1_chip != mea_chip:
        diffs["chipset"] = f"R1={r1_chip} vs MEA={mea_chip}"
    if r1_date != mea_date:
        diffs["date"] = f"R1={r1_date} vs MEA={mea_date}"
    if r1_size != mea_size:
        diffs["size"] = f"R1={r1_size} vs MEA={mea_size}"
    if mea_fitc and r1_fitc != mea_fitc:
        diffs["fitc"] = f"R1={r1_fitc} vs MEA={mea_fitc}"
    if r1_tag != mea_tag:
        diffs["tag"] = f"R1={r1_tag} vs MEA={mea_tag}"

    if diffs:
        remaining.append({"file": rel_path, "diffs": diffs})

print(f"Finished checking! Remaining diffs: {len(remaining)} of {len(mismatches)}")
with open(r"d:\BIOS_-TOOL\scripts\remaining_diffs.json", "w") as f:
    json.dump(remaining, f, indent=2)

for r in remaining[:15]:
    print(r["file"], r["diffs"])
