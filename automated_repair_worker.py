import os
import shutil
import subprocess
import sys
from pathlib import Path
import mea_parser
import smart_repair_engine

def log(msg):
    print(f"[WORKER] {msg}")

def run_automated_task():
    root = Path(os.getcwd())
    main_bios_dir = root / "TESTING_AREA" / "MAIN BIOS"
    final_bios_dir = root / "TESTING_AREA" / "FINAL BIOS"
    final_bios_dir.mkdir(parents=True, exist_ok=True)

    # 1. Find the BIOS file
    bios_files = list(main_bios_dir.glob("*.bin"))
    if not bios_files:
        log("No .bin files found in TESTING_AREA\\MAIN BIOS")
        return

    bios_path = bios_files[0]
    log(f"Found BIOS: {bios_path.name}")

    # 2. Analyze with ME Analyzer
    mea_py = root / "ME Analyzer" / "MEA.py"
    if not mea_py.exists():
        log("MEA.py not found!")
        return

    log("Running ME Analyzer...")
    proc = subprocess.Popen(
        get_script_cmd(mea_py) + [str(bios_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(mea_py.parent)
    )
    stdout, _ = proc.communicate(input=b"\n\n")
    mea_output = stdout.decode("utf-8", errors="replace")

    # 3. Parse Metadata
    meta = mea_parser.parse_mea_output(mea_output)
    if not meta or not meta.get("version"):
        log("Failed to parse MEA output.")
        return

    log(f"Metadata: Version {meta['version']}, SKU {meta.get('sku')}, Chipset {meta.get('chipset')}")

    # 4. Run Smart Repair Engine
    log("Starting Smart Repair Engine...")
    result = smart_repair_engine.run_smart_repair(
        bios_path=str(bios_path),
        mea_meta=meta,
        log_cb=log,
        deliver_to_final=False # We handle delivery ourselves
    )

    if result["success"] and result["output_path"]:
        repaired_file = Path(result["output_path"])
        dest_path = final_bios_dir / f"CLEAN_{repaired_file.name}"
        shutil.copy2(repaired_file, dest_path)
        log(f"REPAIR SUCCESSFUL! File saved to: {dest_path}")
        
        # Create Summary Report
        report_path = final_bios_dir / "REPAIR_SUMMARY.txt"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("=== BIOS REPAIR SUMMARY ===\n")
            f.write(f"Original File : {bios_path.name}\n")
            f.write(f"ME Version    : {meta['version']}\n")
            f.write(f"Status        : {result['status']}\n")
            f.write(f"Clean Binaries: {result['repair_set']}\n")
            f.write(f"Timestamp     : {smart_repair_engine.datetime.now()}\n")
            f.write("===========================\n")
    else:
        log("Repair failed or output not produced.")

if __name__ == "__main__":
    run_automated_task()
