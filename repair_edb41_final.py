import os
import shutil
import subprocess
import re
from pathlib import Path

# --- CONFIGURATION ---
ROOT = Path(os.getcwd())
FIT_EXE = ROOT / "external" / "FLASH System Tools" / "CSME System Tools v13.0 r7" / "Flash Image Tool" / "WIN32" / "fit.exe"
REPO = ROOT / "Firmware_Repository"
INPUT_BIOS = ROOT / "TESTING_AREA" / "edb41_aligned.bin"
ORIGINAL_NAME = "DELL LATITUDE 5400 EDB41 CLEAN.BIN"
OUTPUT_DIR = ROOT / "TESTING_AREA" / "FINAL BIOS"
WORKSPACE = ROOT / "TESTING_AREA" / "WORK_FINAL_EDB41"

# Clean Binaries
CLEAN_ME = REPO / "ME_Region" / "13.0.72.2490_CON_LP_D_PRD_EXTR_74673E47.bin"
CLEAN_PMC = REPO / "PMC_Region" / "ICP_130.1.30.1051_LP_D_PRD.bin"
CLEAN_PCHC = REPO / "PCHC_Region" / "ICP_13.0.0.1005_PRD.bin"

def run_cmd(cmd, cwd=None):
    print(f"[EXEC] {' '.join(map(str, cmd))}")
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)

def repair():
    if WORKSPACE.exists(): shutil.rmtree(WORKSPACE)
    WORKSPACE.mkdir(parents=True)
    if not OUTPUT_DIR.exists(): OUTPUT_DIR.mkdir(parents=True)

    print("[INFO] Decompiling Aligned BIOS...")
    xml_path = WORKSPACE / "config.xml"
    res = run_cmd([FIT_EXE, "-f", str(INPUT_BIOS), "-save", str(xml_path)], cwd=WORKSPACE)
    
    if not xml_path.exists():
        print("[ERROR] Decompilation failed.")
        print(res.stdout)
        return

    # Identify decomp folder
    decomp_dir = WORKSPACE
    decomp_folders = list(WORKSPACE.glob("*decomp*")) + list(WORKSPACE.glob("*EXTRACT*"))
    if decomp_folders: decomp_dir = decomp_folders[0]

    # Replace Regions
    replacements = {
        "ME Region.bin": CLEAN_ME,
        "PMC Region.bin": CLEAN_PMC,
        "PCHC Region.bin": CLEAN_PCHC
    }
    
    for pattern, src in replacements.items():
        targets = list(decomp_dir.glob(f"*{pattern}*"))
        if not targets: # Try generic
            name = pattern.split(' ')[0]
            targets = list(decomp_dir.glob(f"*{name}*.bin"))
        
        for t in targets:
            shutil.copy2(src, t)
            print(f"[REPLACED] {t.name}")

    # Patch XML
    with open(xml_path, 'r', encoding='utf-8') as f:
        content = f.read()
    content = re.sub(r'ManufacturingMode value="Yes"', 'ManufacturingMode value="No"', content)
    content = re.sub(r'CloseManufacturingMode value="No"', 'CloseManufacturingMode value="Yes"', content)
    with open(xml_path, 'w', encoding='utf-8') as f:
        f.write(content)

    # Build
    print("[INFO] Building Final BIOS...")
    res = run_cmd([FIT_EXE, "-f", str(xml_path), "-b"], cwd=WORKSPACE)
    
    out_image = WORKSPACE / "outimage.bin"
    if out_image.exists():
        final_file = OUTPUT_DIR / ORIGINAL_NAME
        shutil.copy2(out_image, final_file)
        print(f"[SUCCESS] Final BIOS delivered: {final_file}")
    else:
        print("[ERROR] Build failed.")
        print(res.stdout)

if __name__ == "__main__":
    repair()
