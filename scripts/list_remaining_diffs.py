import json, os, sys
sys.path.insert(0, r"d:\BIOS_-TOOL")
from R1_CSME_Analyzer.r1_csme_parser import R1CSMEAnalyzer
from scripts.benchmark_hp import run_mea

HP_DIR = r"D:\SDD DATA\all bios\Bios\HP"
with open(r"d:\BIOS_-TOOL\scripts\hp_benchmark_results.json") as f:
    old_data = json.load(f)

mismatches = old_data["details"]

diff_summary = {}
for item in mismatches:
    rel_path = item["file"]
    fpath = os.path.join(HP_DIR, rel_path)
    if not os.path.exists(fpath): continue

    mea_res, _ = run_mea(fpath)
    if not mea_res: continue

    r1_parser = R1CSMEAnalyzer(fpath)
    r1_res = r1_parser.parse()

    mea_ver = mea_res.get("Version", "")
    mea_sku = mea_res.get("SKU", "")
    mea_chip = mea_res.get("Chipset Support") or mea_res.get("Chipset", "")
    mea_size = mea_res.get("Size", "")
    mea_tag = mea_res.get("MEA Database Name", "")

    r1_ver = r1_res.get("version", "")
    r1_sku = r1_res.get("sku", "")
    r1_chip = r1_res.get("chipset", "")
    r1_size = r1_res.get("size_hex", "")
    r1_tag = r1_res.get("full_tag", "")

    diffs = {}
    if r1_ver != mea_ver: diffs["version"] = f"R1={r1_ver} vs MEA={mea_ver}"
    if r1_sku != mea_sku: diffs["sku"] = f"R1={r1_sku} vs MEA={mea_sku}"
    if mea_chip and r1_chip != mea_chip: diffs["chipset"] = f"R1={r1_chip} vs MEA={mea_chip}"
    if mea_size and r1_size.upper() != mea_size.upper() and r1_size != "0x0": diffs["size"] = f"R1={r1_size} vs MEA={mea_size}"
    if mea_tag and r1_tag != mea_tag and r1_tag != "Unknown": diffs["tag"] = f"R1={r1_tag} vs MEA={mea_tag}"

    if diffs:
        # group by diff signature
        sig = tuple(sorted(diffs.keys()))
        diff_summary.setdefault(sig, []).append((rel_path, diffs))

for sig, items in diff_summary.items():
    print(f"=== Diff: {sig} (Count: {len(items)}) ===")
    for p, d in items[:5]:
        print(f"  {p}: {d}")
