#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import glob
import json
import subprocess
from pathlib import Path

# Add project root to path
sys.path.insert(0, r"d:\BIOS_-TOOL")
from R1_CSME_Analyzer.r1_csme_parser import R1CSMEAnalyzer

LENOVO_DIR = r"D:\SDD DATA\all bios\Bios\LENOVO"
MEA_PY = r"d:\BIOS_-TOOL\external\MEAnalyzer\MEA.py"

def get_candidate_files():
    valid_exts = {".bin", ".rom", ".fl1", ".fd", ""}
    files = []
    for root, _, fnames in os.walk(LENOVO_DIR):
        for f in fnames:
            ext = os.path.splitext(f)[1].lower()
            if ext in valid_exts and not f.endswith(".txt") and not f.endswith(".json") and not f.endswith(".zip") and not f.endswith(".rar"):
                files.append(os.path.join(root, f))
    return sorted(files)

def run_mea(file_path):
    base_name = os.path.basename(file_path)
    json_path = os.path.join(r"d:\BIOS_-TOOL\external\MEAnalyzer", f"{base_name}.json")
    if os.path.exists(json_path):
        try:
            os.remove(json_path)
        except Exception:
            pass

    cmd = [sys.executable, MEA_PY, file_path, "-skip", "-exit", "-json"]
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
    except Exception as e:
        return None, f"Timeout/Error: {e}"

    if not os.path.exists(json_path):
        return None, "No JSON generated"

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Structure: { "<filepath>": { "Management Engine": [ {...} ] } }
        for k, v in data.items():
            if isinstance(v, dict) and "Management Engine" in v and v["Management Engine"]:
                return v["Management Engine"][0], None
        return None, "No Management Engine entry"
    except Exception as e:
        return None, f"JSON parse error: {e}"

def run_benchmark(limit=None):
    files = get_candidate_files()
    if limit:
        files = files[:limit]

    print(f"Total candidate files to test: {len(files)}")
    results = {
        "total_files": len(files),
        "mea_valid": 0,
        "mea_invalid_or_non_me": 0,
        "matched": 0,
        "mismatched": 0,
        "details": []
    }

    for idx, fpath in enumerate(files):
        fname = os.path.relpath(fpath, LENOVO_DIR)
        mea_res, err = run_mea(fpath)
        if not mea_res:
            results["mea_invalid_or_non_me"] += 1
            # print(f"[{idx+1}/{len(files)}] [SKIP/NON-ME] {fname} ({err})")
            continue

        results["mea_valid"] += 1

        # Run R1CSMEAnalyzer
        try:
            r1_parser = R1CSMEAnalyzer(fpath)
            r1_res = r1_parser.parse()
        except Exception as e:
            results["mismatched"] += 1
            results["details"].append({
                "file": fname,
                "error": f"R1CSMEAnalyzer crashed: {e}"
            })
            print(f"[{idx+1}/{len(files)}] [CRASH] {fname}: {e}")
            continue

        # Extract MEA ground truth fields
        mea_fam = mea_res.get("Family", "")
        mea_ver = mea_res.get("Version", "")
        mea_sku = mea_res.get("SKU", "")
        mea_chip = mea_res.get("Chipset Support") or mea_res.get("Chipset", "")
        mea_date = mea_res.get("Date", "")
        mea_size = mea_res.get("Size", "")
        mea_fitc = mea_res.get("Flash Image Tool", "")
        mea_tag = mea_res.get("MEA Database Name", "")

        # R1 fields
        r1_fam = r1_res.get("family", "")
        r1_ver = r1_res.get("version", "")
        r1_sku = r1_res.get("sku", "")
        r1_chip = r1_res.get("chipset", "")
        r1_date = r1_res.get("date", "")
        r1_size = r1_res.get("size_hex", "")
        r1_fitc = r1_res.get("fitc_ver", "")
        r1_tag = r1_res.get("full_tag", "")

        # Compare
        diffs = {}
        if r1_ver != mea_ver:
            diffs["version"] = f"R1={r1_ver} vs MEA={mea_ver}"
        if r1_sku != mea_sku:
            diffs["sku"] = f"R1={r1_sku} vs MEA={mea_sku}"
        if mea_chip and r1_chip != mea_chip:
            diffs["chipset"] = f"R1={r1_chip} vs MEA={mea_chip}"
        if r1_date != mea_date and r1_date != "Unknown":
            diffs["date"] = f"R1={r1_date} vs MEA={mea_date}"
        if r1_size.upper() != mea_size.upper() and r1_size != "0x0":
            diffs["size"] = f"R1={r1_size} vs MEA={mea_size}"
        if mea_fitc and r1_fitc != mea_fitc and r1_fitc != "N/A":
            diffs["fitc"] = f"R1={r1_fitc} vs MEA={mea_fitc}"
        if mea_tag and r1_tag != mea_tag and r1_tag != "Unknown":
            diffs["tag"] = f"R1={r1_tag} vs MEA={mea_tag}"

        if diffs:
            results["mismatched"] += 1
            results["details"].append({
                "file": fname,
                "version": mea_ver,
                "diffs": diffs
            })
            print(f"[{idx+1}/{len(files)}] [MISMATCH] {fname} ({mea_ver}): {diffs}")
        else:
            results["matched"] += 1
            print(f"[{idx+1}/{len(files)}] [PERFECT MATCH] {fname} ({mea_ver})")

    print("\n" + "="*60)
    print(f"BENCHMARK SUMMARY (Tested {len(files)} files)")
    print(f"MEA Valid Firmware: {results['mea_valid']}")
    print(f"Invalid / Non-ME / EC: {results['mea_invalid_or_non_me']}")
    print(f"100% Perfect Matches: {results['matched']}")
    print(f"Mismatches: {results['mismatched']}")
    print("="*60)

    with open(r"d:\BIOS_-TOOL\scripts\lenovo_benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    run_benchmark(args.limit)
