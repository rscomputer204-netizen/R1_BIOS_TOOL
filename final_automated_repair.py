import os
import sys
import shutil
import subprocess
from pathlib import Path

# Add root to sys.path
sys.path.append(os.getcwd())
from fit_automator import print_terminal_log

# ──────────────────────────────────────────────────────────────────────────────
# PATHS
# ──────────────────────────────────────────────────────────────────────────────
SOURCE_BIOS = r"TESTING_AREA\MAIN BIOS\GD25Q256C@SOP16_20260426_153941.BIN"
TEMPLATE_XML = r"TESTING_AREA\tgp_template.xml"
WORK_DIR = r"TESTING_AREA\WORKSPACE_FINAL"
CLEAN_ME = r"Firmware_Repository\ME_Region\15.0.55.2751_COR_LP_B_PRD_EXTR-Y_911B31DC.bin"
CLEAN_PMC = r"Firmware_Repository\PMC_Region\TGP_150.1.20.1042_LP_C_PRD_77EC1D25.bin"
AUX_DIR = r"image\Decomp"
FIT_EXE = r"external\FLASH System Tools\CSME System Tools v15.0 r15\Flash Image Tool\WIN32\fit.exe"

def log(msg, level="INFO"):
    print_terminal_log(None, msg, level)

def run_final_repair():
    log("Starting FINAL Automated Repair Workflow...")
    
    if not os.path.exists(WORK_DIR):
        os.makedirs(WORK_DIR)
        
    # 1. Create Dummy BIOS
    dummy_bios = os.path.join(WORK_DIR, "dummy_bios.bin")
    Path(dummy_bios).write_bytes(b"\xFF" * (16 * 1024 * 1024))
    
    # 2. Prepare XML
    log("Configuring XML from template...")
    xml_content = Path(TEMPLATE_XML).read_text(encoding="utf-8")
    
    # Map paths (Absolute paths for FIT)
    abs_me = os.path.abspath(CLEAN_ME).replace("\\", "/")
    abs_pmc = os.path.abspath(CLEAN_PMC).replace("\\", "/")
    abs_pchc = os.path.abspath(os.path.join(AUX_DIR, "PCH Configuration Region.bin")).replace("\\", "/")
    abs_iom = os.path.abspath(os.path.join(AUX_DIR, "Type C IOM Region.bin")).replace("\\", "/")
    abs_phy = os.path.abspath(os.path.join(AUX_DIR, "Type C North PHY Region.bin")).replace("\\", "/")
    abs_chipinit = os.path.abspath(os.path.join(AUX_DIR, "ChipInitBinary.bin")).replace("\\", "/")
    abs_iomoem = os.path.abspath(os.path.join(AUX_DIR, "IomOemConfigDataFile.bin")).replace("\\", "/")
    abs_trchub = os.path.abspath(os.path.join(AUX_DIR, "IntelTrcHubBinary.bin")).replace("\\", "/")
    abs_dummy = os.path.abspath(dummy_bios).replace("\\", "/")
    
    # Update XML (Regex replacement to avoid double values)
    import re
    
    replacements = {
        'Intel(R) ME Binary File': abs_me,
        'PMC Binary File': abs_pmc,
        'PCH Configuration File': abs_pchc,
        'IO Manageability Engine Binary File': abs_iom,
        'PHY Binary File': abs_phy,
        'Chipset Initialization Binary': abs_chipinit,
        'IO Manageability Engine OEM configuration Binary File': abs_iomoem,
        'Intel(R) Trace Hub Binary': abs_trchub,
        'BIOS Binary File': abs_dummy,
        'BIOS Length': '0x1000000',
    }
    
    for label, val in replacements.items():
        # Replace value="[^"]*" on the line containing the label
        pattern = rf'(<[^>]*label="{re.escape(label)}"[^>]*?)value="[^"]*"'
        xml_content = re.sub(pattern, rf'\g<1>value="{val}"', xml_content)
        # Handle cases where value might be after label
        pattern = rf'(<[^>]*?value=")[^"]*("[^>]*label="{re.escape(label)}")'
        xml_content = re.sub(pattern, rf'\g<1>{val}\g<2>', xml_content)

    # Disable ISH
    xml_content = re.sub(r'(<IshSupported[^>]*?)value="[^"]*"', r'\1value="No"', xml_content)
    # Disable TBT (Thunderbolt)
    xml_content = re.sub(r'(<TboltEnable[^>]*?)value="[^"]*"', r'\1value="No"', xml_content)
    # Disable GbE
    xml_content = re.sub(r'(<GbeRegion[^>]*?)(<Enabled[^>]*?)value="[^"]*"', r'\1\2value="Disabled"', xml_content, flags=re.DOTALL)
    
    # Adjust Flash Sizes
    xml_content = re.sub(r'(<FlashComponent1Size[^>]*?)value="[^"]*"', r'\1value="32MB"', xml_content)
    xml_content = re.sub(r'(<NumberOfComponents[^>]*?)value="[^"]*"', r'\1value="1"', xml_content)
    
    config_xml = os.path.join(WORK_DIR, "config.xml")
    Path(config_xml).write_text(xml_content, encoding="utf-8")
    
    # 3. Run FIT
    log("Executing FIT Build...")
    fit_log = os.path.join(WORK_DIR, "fit_build.log")
    cmd = [FIT_EXE, "-f", config_xml, "-b", "-d", os.path.abspath(WORK_DIR)]
    
    with open(fit_log, "w") as f:
        subprocess.run(cmd, stdout=f, stderr=f)
        
    out_image = os.path.join(WORK_DIR, "outimage.bin")
    if not os.path.exists(out_image):
        log("FIT Build failed! Check WORKSPACE_FINAL\\fit_build.log", "ERROR")
        return
    
    log("FIT Build Successful! Extracting configured ME region...")
    
    # 4. Extract Configured ME Region from outimage.bin
    built_data = Path(out_image).read_bytes()
    log("Injecting Configured IFWI into original BIOS...")
    orig_data = bytearray(Path(SOURCE_BIOS).read_bytes())
    
    # Replace first 16MB
    ifwi_size = 16 * 1024 * 1024
    orig_data[0:ifwi_size] = built_data[0:ifwi_size]
    
    final_output = os.path.join(r"TESTING_AREA\FINAL BIOS", "GD25Q256C_Configured_Final.bin")
    Path(final_output).write_bytes(orig_data)
    
    log(f"Repair SUCCESS! Final file: {final_output}")
    
    # 5. Verification
    log("Verifying with ME Analyzer...")
    res = subprocess.run(["python", r"ME_Analyzer_LATEST\MEA.py", final_output], capture_output=True, text=True, input="\n")
    if "Configured" in res.stdout:
        log("Verification: 100% Configured!", "SUCCESS")
    else:
        log("Verification failed or inconclusive.", "WARN")

if __name__ == "__main__":
    run_final_repair()
