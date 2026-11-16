import json, os, sys
sys.path.insert(0, r"d:\BIOS_-TOOL")
from R1_CSME_Analyzer.r1_csme_parser import R1CSMEAnalyzer
from scripts.benchmark_hp import run_mea

HP_DIR = r"D:\SDD DATA\all bios\Bios\HP"
with open(r"d:\BIOS_-TOOL\scripts\remaining_diffs.json") as f:
    diffs_list = json.load(f)

print(f"Re-checking {len(diffs_list)} files with fixed parser...")
still_bad = []
for item in diffs_list:
    rel = item["file"]
    fpath = os.path.join(HP_DIR, rel)
    if not os.path.exists(fpath): continue

    mea_res, _ = run_mea(fpath)
    if not mea_res: continue
    r1 = R1CSMEAnalyzer(fpath).parse()

    cur_diffs = {}
    if r1.get("version") != mea_res.get("Version", ""):
        cur_diffs["version"] = f"R1={r1.get('version')} vs MEA={mea_res.get('Version')}"
    if r1.get("sku") != mea_res.get("SKU", ""):
        cur_diffs["sku"] = f"R1={r1.get('sku')} vs MEA={mea_res.get('SKU')}"
    mea_chip = mea_res.get("Chipset Support") or mea_res.get("Chipset", "")
    if mea_chip and r1.get("chipset") != mea_chip:
        cur_diffs["chipset"] = f"R1={r1.get('chipset')} vs MEA={mea_chip}"
    mea_size = mea_res.get("Size", "")
    if mea_size and r1.get("size_hex", "").upper() != mea_size.upper():
        cur_diffs["size"] = f"R1={r1.get('size_hex')} vs MEA={mea_size}"
    mea_tag = mea_res.get("MEA Database Name", "")
    if mea_tag and r1.get("full_tag") != mea_tag:
        cur_diffs["tag"] = f"R1={r1.get('full_tag')} vs MEA={mea_tag}"

    if cur_diffs:
        still_bad.append({"file": rel, "diffs": cur_diffs})

print(f"Still diff: {len(still_bad)} of {len(diffs_list)}")
for b in still_bad[:20]:
    print(b["file"], b["diffs"])
