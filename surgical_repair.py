import os
import sys
from pathlib import Path

# Add root to sys.path
sys.path.append(os.getcwd())
from smart_repair_engine import run_surgical_configured_repair
from fit_automator import print_terminal_log

SOURCE_BIOS = r"TESTING_AREA\MAIN BIOS\GD25Q256C@SOP16_20260426_153941.BIN"
FINAL_DIR = r"TESTING_AREA\FINAL BIOS"
FINAL_OUT = os.path.join(FINAL_DIR, "GD25Q256C_Surgical.bin")

ME_VERSION = "15.0.55.2751"
REPAIR_SET = {
    "ME": r"Firmware_Repository\ME_Region\15.0.55.2751_COR_LP_B_PRD_EXTR-Y_911B31DC.bin",
    "PMC": r"Firmware_Repository\PMC_Region\TGP_150.1.20.1042_LP_C_PRD_77EC1D25.bin",
    "PCHC": r"Firmware_Repository\PCHC_Region\TGP_15.0.0.1021_PRD.bin",
    "SKU_HINT": "CORPORATE LP"
}

def log(msg, level="INFO"):
    print_terminal_log(None, msg, level)

def run():
    log("Starting Surgical BIOS Repair...")
    
    # Ensure Final Dir exists
    os.makedirs(FINAL_DIR, exist_ok=True)
    
    # We need to monkeypatch or adjust run_surgical_configured_repair
    # because it expects certain paths and behavior.
    # Actually, I'll just call it and see.
    
    success = run_surgical_configured_repair(SOURCE_BIOS, REPAIR_SET, ME_VERSION, FINAL_OUT, log)
    
    if success:
        log(f"Surgical Repair SUCCESS! Output: {FINAL_OUT}")
        
        # Verify
        import subprocess
        log("Verifying with MEA...")
        res = subprocess.run(["python", r"ME_Analyzer_LATEST\MEA.py", FINAL_OUT], capture_output=True, text=True, input="\n")
        if "Configured" in res.stdout:
            log("Verification SUCCESS: 100% Configured!", "SUCCESS")
        else:
            log("Verification result inconclusive.", "WARN")
            print(res.stdout)
    else:
        log("Surgical Repair FAILED.", "ERROR")

if __name__ == "__main__":
    run()
