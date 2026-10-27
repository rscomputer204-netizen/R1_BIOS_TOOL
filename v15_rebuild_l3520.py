import os
import sys
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(r"c:\Users\R1 LAB\Desktop\BIOS_TOOL")
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

TEMPLATE_XML = ROOT / "TESTING_AREA" / "tgp_template.xml"
REBUILD_XML = ROOT / "TESTING_AREA" / "rebuild_l3520.xml"
DCOMP_DIR = ROOT / "TESTING_AREA" / "DCOMP"
REPO_DIR = ROOT / "Firmware_Repository"
OUTPUT_BIN = ROOT / "TESTING_AREA" / "FINAL BIOS" / "DELL_LATITUDE_3520_REPAIRED_CONFIGURED.BIN"
FIT_EXE = ROOT / "external" / "FLASH System Tools" / "CSME System Tools v15.0 r15" / "Flash Image Tool" / "WIN32" / "fit.exe"

CLEAN_ME = REPO_DIR / "ME_Region" / "15.0.55.2751_CON_LP_B_PRD_EXTR_0DB49713.bin"
CLEAN_PMC = REPO_DIR / "PMC_Region" / "TGP_150.1.20.1042_LP_C_PRD_77EC1D25.bin"
CLEAN_PCHC = REPO_DIR / "PCHC_Region" / "TGP_15.0.0.1021_PRD.bin"
CLEAN_PHY = REPO_DIR / "PHY_Region" / "TGP_P_12.14.215.2015_PRD.bin"
CHIP_INIT = ROOT / "TESTING_AREA" / "ChipInitBinary.bin"
DUMMY_IOM = ROOT / "TESTING_AREA" / "dummy_iom.bin"

def patch_xml():
    print(f"[INFO] Patching XML template: {TEMPLATE_XML}")
    tree = ET.parse(TEMPLATE_XML)
    root = tree.getroot()
    
    # 1. Update Output path
    for elem in root.findall(".//BuildOutputFilename"):
        elem.set("value", str(OUTPUT_BIN))
        
    # 2. Update Flash Component Size to 32MB
    for elem in root.findall(".//FlashComponent1Size"):
        elem.set("value", "32MB")
        
    # 3. Update Region Files
    # BIOS
    for elem in root.findall(".//BiosRegion/InputFile"):
        elem.set("value", str(DCOMP_DIR / "bios.bin"))
    
    # ME
    for elem in root.findall(".//MeRegionFile"):
        elem.set("value", str(CLEAN_ME))
        
    # PMC
    for elem in root.findall(".//PmcBinary"):
        elem.set("value", str(CLEAN_PMC))
        
    # Chipset Init
    for elem in root.findall(".//ChipInitBinary"):
        elem.set("value", str(CHIP_INIT))
        
    # PCHC
    for elem in root.findall(".//PchcSubPartitionData/InputFile"):
        elem.set("value", str(CLEAN_PCHC))
        
    # PHY
    for elem in root.findall(".//PhyBinaryFile"):
        elem.set("value", str(CLEAN_PHY))
        
    # IOM
    for elem in root.findall(".//IomBinaryFile"):
        elem.set("value", str(DUMMY_IOM))
        
    # EC
    for elem in root.findall(".//EcRegion/InputFile"):
        elem.set("value", str(DCOMP_DIR / "ec.bin"))
    for elem in root.findall(".//EcRegion/Enabled"):
        elem.set("value", "Enabled")
        
    # 4. Disable Missing/Optional Components
    # ISH
    for elem in root.findall(".//IshSupported"):
        elem.set("value", "No")
    
    # Thunderbolt
    for elem in root.findall(".//TboltEnable"):
        elem.set("value", "No")
        
    # 5. Force Manufacturing Mode -> No
    for elem in root.findall(".//ManufacturingMode"):
        elem.set("value", "No")
    
    for elem in root.findall(".//CloseManufacturingMode"):
        elem.set("value", "Yes")
        
    tree.write(REBUILD_XML, encoding='utf-8', xml_declaration=True)
    print(f"[INFO] Saved rebuild XML to: {REBUILD_XML}")

def run_build():
    print(f"[INFO] Running FIT build...")
    import subprocess
    cmd = [str(FIT_EXE), "-b", "-f", str(REBUILD_XML)]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
    print(result.stdout)
    if result.stderr:
        print(f"[ERROR] {result.stderr}")
    
    if OUTPUT_BIN.exists():
        print(f"[SUCCESS] Repaired BIOS created at: {OUTPUT_BIN}")
        return True
    else:
        print("[FAILED] Output image not found.")
        return False

def main():
    if not OUTPUT_BIN.parent.exists():
        OUTPUT_BIN.parent.mkdir(parents=True)
    patch_xml()
    run_build()

if __name__ == "__main__":
    main()
