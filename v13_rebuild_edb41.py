import os
import shutil
import subprocess
from pathlib import Path

# --- CONFIGURATION ---
ROOT = Path(os.getcwd())
FIT_EXE = ROOT / "external" / "FLASH System Tools" / "CSME System Tools v13.0 r7" / "Flash Image Tool" / "WIN32" / "fit.exe"
REPO = ROOT / "Firmware_Repository"
INPUT_BIOS = ROOT / "TESTING_AREA" / "MAIN BIOS" / "EDB41 LA-G441P Rev1 A00 backup.BIN"
OUTPUT_DIR = ROOT / "TESTING_AREA" / "FINAL BIOS"
WORKSPACE = ROOT / "TESTING_AREA" / "WORK_EDB41"

# Clean Binaries
CLEAN_ME = REPO / "ME_Region" / "13.0.72.2490_CON_LP_D_PRD_EXTR_74673E47.bin"
CLEAN_PMC = REPO / "PMC_Region" / "ICP_130.1.30.1051_LP_D_PRD.bin"
CLEAN_PCHC = REPO / "PCHC_Region" / "ICP_13.0.0.1005_PRD.bin"

def run_cmd(cmd, cwd=None):
    print(f"[EXEC] {' '.join(map(str, cmd))}")
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)

def repair():
    if not WORKSPACE.exists(): WORKSPACE.mkdir(parents=True)
    if not OUTPUT_DIR.exists(): OUTPUT_DIR.mkdir(parents=True)

    # 1. Decompile
    print("[INFO] Decompiling original BIOS...")
    res = run_cmd([FIT_EXE, "-f", str(INPUT_BIOS), "-o", str(WORKSPACE)])
    
    xml_path = WORKSPACE / "config.xml"
    if not xml_path.exists():
        print("[ERROR] Decompilation failed. config.xml not found.")
        print(res.stderr)
        return

    # 2. Patch XML and Replace Files
    print("[INFO] Patching regions and configuration...")
    # The 'Decomp' folder usually contains the extracted regions
    decomp_dir = WORKSPACE / "Decomp"
    
    # Files to replace in Decomp
    replacements = {
        "ME Region.bin": CLEAN_ME,
        "PMC Region.bin": CLEAN_PMC,
        "PCHC Region.bin": CLEAN_PCHC
    }
    
    for filename, clean_src in replacements.items():
        dst = decomp_dir / filename
        if dst.exists():
            shutil.copy2(clean_src, dst)
            print(f"[REPLACED] {filename}")
        else:
            print(f"[WARN] {filename} not found in Decomp, skipping replacement.")

    # 3. Force Manufacturing Mode = Disabled
    import xml.etree.ElementTree as ET
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    # Manufacturing Mode -> No
    for elem in root.findall(".//ManufacturingMode"):
        elem.set("value", "No")
    for elem in root.findall(".//CloseManufacturingMode"):
        elem.set("value", "Yes")
        
    tree.write(xml_path)

    # 4. Rebuild
    print("[INFO] Rebuilding BIOS...")
    res = run_cmd([FIT_EXE, "-b", "-f", str(xml_path)], cwd=WORKSPACE)
    
    out_image = WORKSPACE / "outimage.bin"
    if out_image.exists():
        final_path = OUTPUT_DIR / (INPUT_BIOS.stem + "_CLEAN.BIN")
        shutil.copy2(out_image, final_path)
        print(f"[SUCCESS] Repaired BIOS saved to: {final_path}")
    else:
        print("[ERROR] Rebuild failed. outimage.bin not found.")
        print(res.stdout)
        print(res.stderr)

if __name__ == "__main__":
    repair()
