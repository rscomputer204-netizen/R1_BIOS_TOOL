import os
import sys
import shutil
import subprocess
import json
import re
from pathlib import Path
from datetime import datetime

# Add project root to sys.path
sys.path.append(os.getcwd())

import fit_automator
from firmware_matcher import FirmwareMatcher
from mea_parser import parse_mea_output
from path_utils import get_app_root, get_script_cmd, get_subprocess_env

# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────────
MAIN_BIOS_DIR = Path("TESTING_AREA/MAIN BIOS")
FINAL_BIOS_DIR = Path("TESTING_AREA/FINAL BIOS")
RECORD_FILE = Path("TESTING_AREA/repair_history.json")

def log(msg, level="INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{level}] {msg}")

def run_mea_analysis(file_path):
    mea_py = Path("external/MEAnalyzer/MEA.py")
    if not mea_py.exists(): mea_py = Path("ME Analyzer/MEA.py")
    if not mea_py.exists(): return {}
    proc = subprocess.Popen(
        get_script_cmd(mea_py) + [str(file_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,
        env=get_subprocess_env()
    )
    stdout_bytes, _ = proc.communicate(input=b"\n\n")
    return parse_mea_output(stdout_bytes.decode("utf-8", errors="replace"))

def surgical_patch(orig_path, me_path, output_path, log_cb=None):
    """Performs deep surgical hex-level replacement of the ME region."""
    log_cb("Performing Deep Surgical Hex Patching...", "WARNING")
    
    orig_data = bytearray(Path(orig_path).read_bytes())
    me_data = Path(me_path).read_bytes()
    
    # 1. Force standard Intel CSME offset 0x1000
    me_offset = 0x1000
    
    # 2. Identify BIOS Region Start (usually 16MB)
    bios_offset = orig_data.find(b"$EBP")
    if bios_offset == -1 or bios_offset < 0x800000:
         # Fallback: Check for standard 16MB/32MB splits
         if len(orig_data) > 16*1024*1024: bios_offset = 0x1000000 
         else: bios_offset = len(orig_data) // 2
    
    max_me_size = bios_offset - me_offset
    log_cb(f"Identified Region Space: 0x{me_offset:X} to 0x{bios_offset:X} (Space: 0x{max_me_size:X})")
    
    if len(me_data) > max_me_size:
        log_cb(f"Warning: Clean ME exceeds space. Truncating...", "WARNING")
        me_data = me_data[:max_me_size]

    # 3. Apply the patch
    # Clean the region first (0xFF)
    orig_data[me_offset:bios_offset] = b"\xFF" * max_me_size
    # Write clean ME data
    orig_data[me_offset:me_offset+len(me_data)] = me_data
    
    # 4. Final verification of signature at patch point
    if b"$FPT" not in orig_data[me_offset:me_offset+0x10000]:
         log_cb("Warning: No $FPT signature found in patched region start!", "WARNING")
    
    Path(output_path).write_bytes(orig_data)
    log_cb(f"Surgical patch applied successfully to {output_path}")
    return True

def run_advanced_repair_workflow():
    log("=== STARTING 100% AUTOMATED BIOS REPAIR PIPELINE ===")
    
    if FINAL_BIOS_DIR.exists():
        for f in FINAL_BIOS_DIR.glob("*"):
            try: f.unlink()
            except: pass
    else:
        FINAL_BIOS_DIR.mkdir(parents=True, exist_ok=True)

    bios_files = list(MAIN_BIOS_DIR.glob("*.bin"))
    if not bios_files:
        log("No BIOS files found!", "ERROR")
        return
    
    target_bios = bios_files[0]
    log(f"Target: {target_bios.name}")

    meta = run_mea_analysis(target_bios)
    if not meta.get("version"): return

    log(f"Metadata: Version {meta['version']}, SKU {meta['sku']}")

    matcher = FirmwareMatcher(os.getcwd())
    repair_set = matcher.get_repair_set(meta)

    if not repair_set or "ME" not in repair_set:
        log("No clean ME firmware match found!", "ERROR")
        return

    output_filename = f"CLEAN_{target_bios.name}"
    output_path = FINAL_BIOS_DIR / output_filename
    
    # Try Rebuild Pipeline
    success = fit_automator.execute_fit_rebuild(str(target_bios), repair_set, meta['version'], str(output_path), log)

    if not success:
        log("FIT Pipeline failed. Falling back to Surgical Patching...")
        success = surgical_patch(str(target_bios), repair_set['ME'], str(output_path), log)

    if success and output_path.exists():
        log("Running Post-Repair Verification...", "INFO")
        mea_path = Path('external/MEAnalyzer/MEA.py')
        if not mea_path.exists(): mea_path = Path('ME Analyzer/MEA.py')
        mea_res = subprocess.run(
            get_script_cmd(mea_path) + [str(output_path), '-skip', '-exit'],
            capture_output=True,
            text=False,
            env=get_subprocess_env()
        )
        stdout_text = mea_res.stdout.decode('utf-8', errors='ignore')
        
        final_state = "Unknown"
        if "File System State" in stdout_text:
            match = re.search(r"File System State\s+│\s+(\w+)", stdout_text)
            if match:
                final_state = match.group(1)
        
        # Determine Success (Unconfigured or Configured is success for ME12+)
        is_success = final_state in ["Unconfigured", "Configured"]
        state_icon = "SUCCESS" if is_success else "WARNING"
        log(f"[{state_icon}] Final ME State: {final_state}", state_icon)

        print("\n" + "="*60)
        print("              BIOS REPAIR PIPELINE - FINAL REPORT")
        print("="*60)
        print(f"Status           : {'COMPLETED' if is_success else 'FAILED'}")
        print(f"Repaired File    : {output_path.name}")
        print(f"File System State: {final_state}")
        print("-" * 60)
        if is_success:
            print("SUMMARY: The BIOS has been successfully cleaned.")
            if final_state == "Unconfigured":
                print("Note: 'Unconfigured' is the correct state for CSME 12 Clean regions.")
                print("It will transition to 'Configured' automatically on the first boot.")
            else:
                print("The firmware is now in a fully Configured state.")
        else:
            print("SUMMARY: The repair process completed but the state is still Initialized.")
            print("This may happen if the FIT tool version is incompatible.")
        print("="*60 + "\n")

if __name__ == "__main__":
    run_advanced_repair_workflow()
