import os
import sys
import subprocess
import json
from pathlib import Path
from firmware_matcher import FirmwareMatcher
from mea_parser import parse_mea_output
from fit_automator import execute_fit_rebuild

ROOT = Path(os.getcwd())
MEA_PY = ROOT / "ME Analyzer" / "MEA.py"
MAIN_BIOS_DIR = ROOT / "TESTING_AREA" / "MAIN BIOS"
FINAL_BIOS_DIR = ROOT / "TESTING_AREA" / "FINAL BIOS"
TARGET_FILE = "HP 280 G3  FX ISL-4 REV A BSCKUP.BIN"
TARGET_PATH = MAIN_BIOS_DIR / TARGET_FILE
OUTPUT_PATH = FINAL_BIOS_DIR / TARGET_FILE

HISTORY_FILE = ROOT / "TESTING_AREA" / "repair_history.json"
ERROR_LOG = ROOT / "TESTING_AREA" / "fit_errors_solutions.log"

def log_error(err_msg, solution="None provided yet"):
    with open(ERROR_LOG, "a") as f:
        f.write(f"ERROR: {err_msg}\nSOLUTION: {solution}\n\n")

def main():
    if not TARGET_PATH.exists():
        print(f"Target file not found: {TARGET_PATH}")
        return

    FINAL_BIOS_DIR.mkdir(parents=True, exist_ok=True)

    print("1. Running ME Analyzer...")
    cmd = get_script_cmd(MEA_PY) + [str(TARGET_PATH), "-skip", "-exit", "-duc"]
    res = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
    
    print("2. Parsing logic...")
    import re
    
    version = None
    sku = None
    
    # Extract version
    ver_match = re.search(r"(\d{1,2}\.\d{1,2}\.\d{1,3}\.\d{4})", res.stdout)
    if ver_match:
        version = ver_match.group(1)
        
    # Extract SKU
    sku_match = re.search(r"SKU\s*│\s*([a-zA-Z\s]+?)\s*║", res.stdout)
    if sku_match:
        sku = sku_match.group(1).strip()
    
    if not version:
        print("Failed to detect version from ME Analyzer!")
        log_error("Failed to detect ME Version from MEA output.", "Check if MEA is running correctly.")
        return
        
    print(f"Identified Version: {version}, SKU: {sku}")

    print("3. Matching clean files...")
    matcher = FirmwareMatcher(ROOT)
    
    # We pass mea_metadata manually
    mea_metadata = {"version": version, "sku": sku}
    clean_paths = matcher.get_repair_set(mea_metadata)
    
    print(f"Found matches: {json.dumps(clean_paths, indent=2)}")

    if not clean_paths.get("ME"):
        print("NO CLEAN ME FOUND! Cannot rebuild safely.")
        log_error(f"Missing Clean ME for {version} {sku}", "Download correct clean ME version from firmware repository.")
        return

    print("4. Executing FIT Rebuild...")
    rebuild_success = execute_fit_rebuild(
        corrupt_bios_path=str(TARGET_PATH),
        clean_paths_dict=clean_paths,
        version_string=version,
        output_path=str(OUTPUT_PATH),
        terminal_callback=print,
        external_dir="external"
    )

    if rebuild_success:
        print("\n\n5. Adding to record keeping...")
        record = {
            "Original_File": TARGET_FILE,
            "Detected_Version": version,
            "SKU": sku,
            "Clean_Files_Used": clean_paths,
            "Status": "Success (100% Configured)",
            "Output": str(OUTPUT_PATH)
        }
        history = []
        if HISTORY_FILE.exists():
            with open(HISTORY_FILE, "r") as f:
                try:
                    history = json.load(f)
                except:
                    pass
        history.append(record)
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=4)
        
        print("\n=== REPAIR SUMMARY REPORT ===")
        print(f"File Source: {TARGET_PATH}")
        print(f"File Destination: {OUTPUT_PATH}")
        print(f"Firmware Version: {version}")
        print(f"State: 100% CONFIGURED (Manufacturing Mode Disabled)")
        print(f"Clean Files Injected: {json.dumps(clean_paths, indent=2)}")
        print(f"\n[CONFIRMATION] File has been securely stored in TESTING_AREA\\FINAL BIOS folder.")
    else:
        print("REBUILD FAILED.")
        log_error("execute_fit_rebuild failed", "Check FIT tool logs and fit.log in workspace.")

if __name__ == '__main__':
    main()
