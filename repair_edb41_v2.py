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
WORKSPACE = ROOT / "TESTING_AREA" / "WORK_EDB41_V2"

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

    # 1. Decompile using -save flag (Modern FIT style)
    print("[INFO] Decompiling/Extracting original BIOS...")
    temp_bios = WORKSPACE / "image.bin"
    shutil.copy2(INPUT_BIOS, temp_bios)
    
    xml_path = WORKSPACE / "config.xml"
    # Modern FIT: -f to load, -save to export config
    res = run_cmd([FIT_EXE, "-f", str(temp_bios), "-save", str(xml_path)], cwd=WORKSPACE)
    
    if not xml_path.exists():
        print("[ERROR] Decompilation failed. config.xml not found.")
        print(f"STDOUT: {res.stdout}")
        print(f"STDERR: {res.stderr}")
        return

    # 2. Extract Folder Identification
    # FIT creates a subfolder usually named 'image.bin.decomp' or similar
    # In some versions, it just extracts to the current folder.
    # We'll check for a 'Decomp' or similar.
    decomp_dirs = list(WORKSPACE.glob("*decomp*")) + list(WORKSPACE.glob("*EXTRACT*"))
    if not decomp_dirs:
        # Check current folder for .bin files
        print("[INFO] No specific decomp folder found, checking root...")
        decomp_dir = WORKSPACE
    else:
        decomp_dir = decomp_dirs[0]
    
    print(f"[INFO] Working in decomp folder: {decomp_dir.name}")

    # 3. Replace Regions
    replacements = {
        "ME Region.bin": CLEAN_ME,
        "PMC Region.bin": CLEAN_PMC,
        "PCHC Region.bin": CLEAN_PCHC
    }
    
    for pattern, clean_src in replacements.items():
        # Version 13 names might vary, using glob
        targets = list(decomp_dir.glob(f"*{pattern}*"))
        if not targets:
            # Try partial matching
            short_name = pattern.split(' ')[0]
            targets = list(decomp_dir.glob(f"*{short_name}*.bin"))
            
        if targets:
            for t in targets:
                shutil.copy2(clean_src, t)
                print(f"[REPLACED] {t.name}")
        else:
            print(f"[WARN] Region matching '{pattern}' not found.")

    # 4. Patch XML for Manufacturing Mode
    import re
    with open(xml_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    content = re.sub(r'ManufacturingMode value="Yes"', 'ManufacturingMode value="No"', content)
    content = re.sub(r'CloseManufacturingMode value="No"', 'CloseManufacturingMode value="Yes"', content)
    
    with open(xml_path, 'w', encoding='utf-8') as f:
        f.write(content)

    # 5. Rebuild
    print("[INFO] Rebuilding Final Image...")
    res = run_cmd([FIT_EXE, "-f", str(xml_path), "-b"], cwd=WORKSPACE)
    
    out_image = WORKSPACE / "outimage.bin"
    if out_image.exists():
        final_path = OUTPUT_DIR / (INPUT_BIOS.stem + "_REPAIRED.BIN")
        shutil.copy2(out_image, final_path)
        print(f"[SUCCESS] Repaired BIOS saved to: {final_path}")
    else:
        print("[ERROR] Rebuild failed. outimage.bin not found.")
        print(res.stdout)
        print(res.stderr)

if __name__ == "__main__":
    repair()
