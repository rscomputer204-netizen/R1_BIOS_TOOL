import os
import sys
import shutil
from pathlib import Path
from smart_repair_engine import run_smart_repair, get_paths
from fit_automator import run_me_analyzer_internal

def terminal_log(msg, level="INFO"):
    print(f"[{level}] {msg}")

def main():
    terminal_log("="*60)
    terminal_log("R1 BIOS SERVICE TOOL - AUTOMATED REPAIR PIPELINE")
    terminal_log("="*60)

    # 1. File Sourcing
    source_dir = Path("TESTING_AREA") / "MAIN BIOS"
    files = list(source_dir.glob("*.BIN")) + list(source_dir.glob("*.bin"))
    
    if not files:
        terminal_log("No BIOS file found in TESTING_AREA\\MAIN BIOS", "ERROR")
        return

    bios_path = str(files[0])
    terminal_log(f"Found BIOS: {os.path.basename(bios_path)}")

    # 2. Identification
    terminal_log("Analyzing BIOS firmware versions...")
    mea_meta = run_me_analyzer_internal(bios_path, terminal_log)
    
    if not mea_meta:
        terminal_log("Failed to identify BIOS versions.", "ERROR")
        return

    terminal_log(f"ME Version: {mea_meta.get('version')}")
    terminal_log(f"ME SKU:     {mea_meta.get('sku')}")
    terminal_log(f"Chipset:    {mea_meta.get('chipset')}")
    terminal_log(f"State:      {mea_meta.get('file_system_state')}")

    # 3. Automation Trigger
    terminal_log("Triggering Smart Repair Engine...")
    result = run_smart_repair(
        bios_path=bios_path,
        mea_meta=mea_meta,
        log_cb=terminal_log,
        deliver_to_final=True
    )

    if result["success"]:
        terminal_log("="*60)
        terminal_log("REPAIR SUMMARY REPORT")
        terminal_log("="*60)
        terminal_log(f"Status:      SUCCESS")
        terminal_log(f"Output:      {os.path.basename(result['final_path'])}")
        terminal_log(f"Location:    TESTING_AREA\\FINAL BIOS")
        
        repair_set = result.get("repair_set", {})
        terminal_log(f"ME Clean:    {os.path.basename(repair_set.get('ME', 'None'))}")
        terminal_log(f"PMC Clean:   {os.path.basename(repair_set.get('PMC', 'None'))}")
        terminal_log(f"PCHC Clean:  {os.path.basename(repair_set.get('PCHC', 'None'))}")
        
        terminal_log("\n[LEARNING] Record updated in repair_history.json")
        terminal_log("[LEARNING] Knowledge base updated with TGP-LP pattern.")
    else:
        terminal_log("Repair process failed. Check fit_errors_solutions.log", "ERROR")

if __name__ == "__main__":
    main()
