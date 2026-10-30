"""
Smart Repair Engine — R1 BIOS Service Tool
==========================================
Fully automated BIOS repair pipeline. Handles selection, 
rebuild (via FIT), and manual fallback (Hex injection).

ERROR HANDLING POLICY:
  Any critical error during the pipeline raises PipelineHaltError.
  This immediately stops ALL further processing — no fallback will
  be attempted. The caller must catch this and display a UI popup.
"""

import os
import re
import sys
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from bios_parser import find_flash_descriptor, parse_spi_regions
from path_utils import get_app_root


class PipelineHaltError(Exception):
    """
    Raised when a critical, unrecoverable error occurs during the repair pipeline.
    
    When this is raised, the pipeline MUST stop immediately.
    No fallback or subsequent step should be attempted.
    The UI layer should catch this and display an error popup to the user.
    
    Attributes:
        message   : Human-readable error description shown to user
        error_code: Short identifier for the type of failure
        step      : Which pipeline step failed (e.g. 'DECOMPILE', 'FIT_BUILD')
    """
    def __init__(self, message: str, error_code: str = "PIPELINE_HALT", step: str = "UNKNOWN"):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.step = step
    
    def __str__(self):
        return f"[{self.step}] {self.message}"

# ──────────────────────────────────────────────────────────────────────────────
# PATHS
# ──────────────────────────────────────────────────────────────────────────────
def _root() -> Path:
    return Path(get_app_root())

def get_paths():
    root = _root()
    return {
        "fw_repo_me":   root / "Firmware_Repository" / "ME_Region",
        "fw_repo_pmc":  root / "Firmware_Repository" / "PMC_Region",
        "fw_repo_pchc": root / "Firmware_Repository" / "PCHC_Region",
        "fw_repo_phy":  root / "Firmware_Repository" / "PHY_Region",
        "fit_tools":    root / "external" / "FLASH System Tools",
        "mea_py":       root / "ME Analyzer" / "MEA.py",
        "repaired_dir": root / "REPAIRED_BIOS",
        "final_dir":    root / "TESTING_AREA" / "FINAL BIOS",
        "fit_workspace":root / "FIT_WORKSPACE",
        "history_file": root / "TESTING_AREA" / "repair_history.json",
        "error_log":    root / "TESTING_AREA" / "fit_errors_solutions.log",
        "knowledge_base": root / "TESTING_AREA" / "repair_knowledge.json",
    }

# ──────────────────────────────────────────────────────────────────────────────
# SELECTION LOGIC
# ──────────────────────────────────────────────────────────────────────────────
def select_clean_me(major: int, minor: int, sku: str, log_cb) -> str | None:
    me_dir = get_paths()["fw_repo_me"]
    sku_target = sku.upper().strip()
    candidates = []
    
    major_dir = me_dir / str(major)
    if not major_dir.exists():
        # Safety fallback
        major_dir = me_dir
        
    for meta_file in major_dir.rglob("metadata.json"):
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            continue
            
        score = 0
        f_minor = meta.get("minor", 0)
        if f_minor == minor: score += 500
        elif f_minor > minor: score += 100
        
        meta_sku = meta.get("sku", "UNKNOWN")
        meta_power = meta.get("power", "UNKNOWN")
        
        # Strict SKU match
        if meta_sku != "UNKNOWN" and meta_sku in sku_target:
            score += 200
        elif meta_sku == "UNKNOWN" and ("1.5MB" not in sku_target and "5MB" not in sku_target):
            score += 50
            
        if "LP" in sku_target and meta_power == "LP": score += 100
        elif "H" in sku_target and meta_power == "H": score += 100
        elif "N" in sku_target and meta_power == "N": score += 100
        elif "V" in sku_target and meta_power == "V": score += 100
            
        status = meta.get("status", "")
        if status == "PRODUCTION": score += 20
        
        origin = meta.get("origin", "")
        if origin == "REGION": score += 10
        elif origin == "EXTRACTED": score += 5
        elif origin == "UPDATE": score += 15
        
        bin_file = meta_file.parent / meta.get("original_filename", "")
        if bin_file.exists():
            candidates.append((score, bin_file))
            
    if not candidates: return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    log_cb(f"[INFO] Selected ME (via Metadata): {candidates[0][1].name}")
    return str(candidates[0][1])

def select_pmc(chipset_hint: str, sku: str, log_cb, mea_meta: dict) -> str | None:
    pmc_dir = get_paths()["fw_repo_pmc"]
    c, s = chipset_hint.upper(), sku.upper()
    
    v_parts = mea_meta.get("version", "0.0").split(".")
    v_maj = int(v_parts[0])
    v_min = v_parts[1] if len(v_parts) > 1 else "0"
    
    # Strict mapping by major version first — prevents CNP/CMP ambiguity
    target_prefix = ""
    if v_maj == 16: target_prefix = "ADP"
    elif v_maj == 15: target_prefix = "TGP"
    elif v_maj == 14: target_prefix = "CMP"
    elif v_maj == 13:
        if "LKF" in c: target_prefix = "LKF"
        elif "JSP" in c: target_prefix = "JSP"
        else: target_prefix = "ICP"
    elif v_maj == 12: target_prefix = "CNP"

    # Fallback to string prefix matching only if major version didn't give a strict mapping
    if not target_prefix:
        prefixes = ["ADP", "RPL", "TGP", "ICP", "CNP", "CMP", "CML", "TGL", "MCC"]
        for p in prefixes:
            if p in c:
                target_prefix = p
                break
    
    if not target_prefix:
        return None
            
    matches = []
    for f in pmc_dir.glob(f"{target_prefix}*.bin"):
        n = f.name.upper()
        score = 0
        v_str = f"{v_maj}{v_min}"
        if f"{target_prefix}_{v_str}" in n or f"{target_prefix}{v_str}" in n: score += 1000
        elif f"{target_prefix}_{v_maj}" in n or f"{target_prefix}{v_maj}" in n: score += 500
            
        if "_LP_" in n and "LP" in s: score += 100
        elif "_H_" in n and "H" in s: score += 100
        matches.append((score, f))
    
    if matches:
        matches.sort(key=lambda x: (x[0], x[1].name), reverse=True)
        if matches[0][0] >= 100:
            log_cb(f"[INFO] Selected PMC: {matches[0][1].name}")
            return str(matches[0][1])
    return None

def select_pchc(chipset_hint: str, log_cb, mea_meta: dict) -> str | None:
    pchc_dir = get_paths()["fw_repo_pchc"]
    c = chipset_hint.upper()
    v_parts = mea_meta.get("version", "0.0").split(".")
    v_maj = int(v_parts[0])
    v_min = v_parts[1] if len(v_parts) > 1 else "0"

    target = ""
    # Map strict targets by major version first to avoid ambiguous chipset hints (like CNP/CMP)
    if v_maj == 16: target = "ADP"
    elif v_maj == 15: target = "TGP"
    elif v_maj == 14: target = "CMP"
    elif v_maj == 13: 
        if "LKF" in c: target = "LKF"
        elif "JSP" in c: target = "JSP"
        else: target = "ICP"
    
    # Fallback to string prefix matching only if major version didn't give a strict mapping
    if not target:
        prefixes = ["ADP", "RPL", "TGP", "ICP", "CNP", "CMP", "MCC"]
        for p in prefixes:
            if p in c: target = p; break
            
    if not target:
        return None
    
    candidates = []
    for f in pchc_dir.glob(f"{target}*.bin"):
        n, score = f.name.upper(), 0
        if f"{target}_{v_maj}.{v_min}" in n: score += 1000
        elif f"{target}_{v_maj}" in n: score += 500
        if "PRD" in n: score += 50
        candidates.append((score, f))

    if candidates:
        candidates.sort(key=lambda x: (x[0], x[1].name), reverse=True)
        if candidates[0][0] >= 100:
            log_cb(f"[INFO] Selected PCHC: {candidates[0][1].name}")
            return str(candidates[0][1])
    return None

def select_phy(chipset_hint: str, log_cb, mea_meta: dict) -> str | None:
    phy_dir = get_paths()["fw_repo_phy"]
    c = chipset_hint.upper()
    v_parts = mea_meta.get("version", "0.0").split(".")
    v_maj = int(v_parts[0])
    v_min = v_parts[1] if len(v_parts) > 1 else "0"

    target = ""
    # Map strict targets by major version first
    if v_maj == 16: target = "ADP_P"
    elif v_maj == 15: target = "TGP_P"
    elif v_maj == 14: target = "CMP_P"
    elif v_maj == 13: target = "LKF_S" # Assuming LKF for v13 based on PHY repo
    
    if not target:
        prefixes = ["ADP", "RPL", "TGP", "ICP", "CNP", "CMP", "MCC", "LKF"]
        for p in prefixes:
            if p in c: 
                target = f"{p}_P"
                break
            
    if not target:
        return None
    
    candidates = []
    for f in phy_dir.glob(f"{target}*.bin"):
        n, score = f.name.upper(), 0
        if f"{target}_{v_maj}.{v_min}" in n: score += 1000
        elif f"{target}_{v_maj}" in n: score += 500
        if "PRD" in n: score += 50
        candidates.append((score, f))

    if candidates:
        candidates.sort(key=lambda x: (x[0], x[1].name), reverse=True)
        log_cb(f"[INFO] Selected PHY: {candidates[0][1].name}")
        return str(candidates[0][1])
    return None

def build_repair_set(mea_meta: dict, log_cb) -> dict:
    version = mea_meta.get("version", "")
    sku = mea_meta.get("sku", "")
    chipset = mea_meta.get("chipset", "")
    parts = version.split(".")
    major = int(parts[0]) if parts[0].isdigit() else 0
    minor = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    
    repair_set = {"ME": select_clean_me(major, minor, sku, log_cb), "SKU_HINT": sku.upper(), "CHIPSET": chipset}
    if major >= 12:
        repair_set["PMC"] = select_pmc(chipset, sku, log_cb, mea_meta)
        repair_set["PCHC"] = select_pchc(chipset, log_cb, mea_meta)
        repair_set["PHY"] = select_phy(chipset, log_cb, mea_meta)
    return repair_set

# ──────────────────────────────────────────────────────────────────────────────
# CORE ENGINE LOGIC
# ──────────────────────────────────────────────────────────────────────────────
def log_repair_event(status: str, meta: dict, repair_set: dict, error_msg: str = None):
    paths = get_paths()
    kb_path = paths["knowledge_base"]
    event = {
        "timestamp": datetime.now().isoformat(), "status": status,
        "firmware": {"version": meta.get("version"), "sku": meta.get("sku"), "chipset": meta.get("chipset")},
        "solution_applied": {
            "me_file": os.path.basename(repair_set.get("ME", "")) if repair_set.get("ME") else None,
            "pmc_file": os.path.basename(repair_set.get("PMC", "")) if repair_set.get("PMC") else None,
            "pchc_file": os.path.basename(repair_set.get("PCHC", "")) if repair_set.get("PCHC") else None,
            "phy_file": os.path.basename(repair_set.get("PHY", "")) if repair_set.get("PHY") else None
        }
    }
    if error_msg: event["error_details"] = error_msg
    history = []
    if kb_path.exists():
        try:
            with open(kb_path, "r") as f: history = json.load(f)
        except: pass
    history.append(event)
    with open(kb_path, "w") as f: json.dump(history[-100:], f, indent=4)

def run_full_fit_rebuild(bios_path, repair_set, me_version, output_path, log_cb, custom_fit_exe=None):
    try:
        from fit_automator import execute_fit_rebuild
        success = execute_fit_rebuild(bios_path, repair_set, me_version, output_path, log_cb, custom_fit_exe=custom_fit_exe)
        return success
    except PipelineHaltError:
        raise
    except Exception as e: 
        log_cb(f"[ERROR] {e}")
        return False

def find_me_offset_by_signature(bios_path, log_cb) -> int:
    try:
        data = Path(bios_path).read_bytes()
        pos = data.find(b"$CPD")
        if pos != -1:
            potential_start = pos - 0x2000
            if potential_start >= 0: return potential_start
        pos = data.find(b"FTPR")
        if pos != -1: return (pos >> 12) << 12
    except: pass
    return -1

def run_surgical_modern_repair(bios_path, repair_set, version_string, output_path, log_cb, platform_hint=None, custom_fit_exe=None):
    major = int(version_string.split(".")[0])
    platform = "Tiger Lake" if major == 15 else "Alder Lake"
    log_cb(f"[ACTION] Starting Surgical Modern ({platform}) Repair...")
    try:
        from fit_automator import find_fit_executable, get_short_path, mapped_drive_context
        root = get_app_root()
        with mapped_drive_context(root) as virtual_root:
            v_work_dir = virtual_root / "FIT_WORKSPACE" / "modern_surgical"
            # Save all auxiliary binaries BEFORE clearing the workspace
            # These files are mandatory for FIT builds on TGP/ADP
            aux_names = ["ChipInitBinary.bin", "ISHC.bin", "IntelTrcHubBinary.bin", "Type C IOM Region.bin", "PHY.bin"]
            saved_aux = {}
            
            from fit_automator import execute_fit_decompile, run_me_analyzer_internal
            log_cb("[INFO] Extracting correct auxiliary files from original BIOS...")
            
            # Determine original BIOS version to use the right FIT for decompilation
            orig_mea = run_me_analyzer_internal(bios_path, log_cb)
            orig_version = orig_mea.get("version", version_string) if orig_mea and orig_mea.get("version") else version_string
            
            temp_decomp_dir = virtual_root / "FIT_WORKSPACE" / "temp_decomp_original"
            if temp_decomp_dir.exists():
                shutil.rmtree(temp_decomp_dir, ignore_errors=True)
                
            decomp_res = execute_fit_decompile(str(bios_path), orig_version, str(temp_decomp_dir), log_cb, custom_fit_exe=custom_fit_exe)
            
            if not decomp_res:
                log_cb("[WARN] Flash Image Tool (FIT) was unable to decompile this firmware image (Error 179 / Decompose Failure).")
                log_cb("[ACTION] Switching automatically to Direct Hex Injection (Cut & Paste System)...")
                inj_ok = manual_hex_repair(bios_path, repair_set, output_path, log_cb)
                if inj_ok:
                    log_cb("[SUCCESS] Direct Hex Injection (Cut & Paste) completed successfully! [OK]")
                    return True
                else:
                    err_msg = (
                        "Decompile & Direct Injection Failed.\n\n"
                        "The Flash Image Tool (FIT) was unable to decompile the original BIOS,\n"
                        "and Direct Hex Injection could not locate valid SPI regions.\n\n"
                        "Action required: Check the file integrity or try an alternative method."
                    )
                    log_cb("[ERROR] CRITICAL: Both Decompile and Direct Injection failed.")
                    raise PipelineHaltError(
                        message=err_msg,
                        error_code="DECOMPILE_PROCESS_FAIL",
                        step="DECOMPILE"
                    )
                
            if decomp_res:
                for p in Path(decomp_res).rglob("*.bin"):
                    if p.is_file() and p.stat().st_size > 0:
                        saved_aux[p.name] = p.read_bytes()
                        base = p.name.split("#")[-1]
                        if base not in saved_aux:
                            saved_aux[base] = saved_aux[p.name]
                        if "IOM" in p.name.upper():
                            saved_aux["Type C IOM Region.bin"] = saved_aux[p.name]
                        if "NPHY" in p.name.upper() or p.name.upper().endswith("PHY.BIN"):
                            saved_aux["PHY.bin"] = saved_aux[p.name]
                        if "CHIPINIT" in p.name.upper():
                            saved_aux["ChipInitBinary.bin"] = saved_aux[p.name]
                        if "TRACEHUB" in p.name.upper():
                            saved_aux["IntelTrcHubBinary.bin"] = saved_aux[p.name]
                        if "OEM_KM" in p.name.upper():
                            saved_aux["OEM_KM.bin"] = saved_aux[p.name]
                        if "PMC" in p.name.upper():
                            saved_aux["PMC.bin"] = saved_aux[p.name]
                        if "PCHC" in p.name.upper():
                            saved_aux["PCHC.bin"] = saved_aux[p.name]
                        if "SUBPARTITIONME" in p.name.upper().replace(" ", "") or p.name == "ME Sub Partition.bin":
                            saved_aux["ME Sub Partition.bin"] = saved_aux[p.name]
                            log_cb(f"[INFO] Successfully extracted ME Sub Partition ({p.stat().st_size} bytes).")
            
            # Fallback: Robust direct IFWI carving for OEM partitions if FIT missed them
            try:
                with open(bios_path, 'rb') as f: data = f.read()
                idx = 0
                cpds = []
                while True:
                    idx = data.find(b'\x24\x43\x50\x44', idx) # $CPD
                    if idx == -1: break
                    if idx + 0x40 <= len(data):
                        cpds.append((data[idx+12:idx+16], idx))
                    idx += 4
                
                cpds.sort(key=lambda x: x[1])
                targets = {b'IOMP': 'Type C IOM Region.bin', b'NPHY': 'PHY.bin', b'ISHC': 'ISHC.bin'}
                
                for i, (name, offset) in enumerate(cpds):
                    if name in targets:
                        fname = targets[name]
                        if fname not in saved_aux:
                            next_offset = cpds[i+1][1] if i+1 < len(cpds) else offset + 0x40000
                            saved_aux[fname] = data[offset:next_offset]
                            log_cb(f"[INFO] Successfully carved {fname} directly from IFWI.")
            except Exception as e:
                log_cb(f"[WARN] Failed to carve directly from IFWI: {e}")
            
            if not saved_aux and not decomp_res:
                log_cb("[ERROR] Failed to extract auxiliary files. Both Original BIOS and Clean ME failed to decompile.")
            
            if v_work_dir.exists():
                shutil.rmtree(v_work_dir, ignore_errors=True)
            v_work_dir.mkdir(parents=True, exist_ok=True)
            
            if major >= 16:
                decomp_xml = None
                if decomp_res:
                    for cand_xml in [Path(decomp_res).parent / "config.xml", Path(decomp_res) / "config.xml"]:
                        if cand_xml.exists():
                            decomp_xml = cand_xml
                            break
                if decomp_xml and decomp_xml.exists():
                    v_template_xml = decomp_xml
                else:
                    v_template_xml = virtual_root / "TESTING_AREA" / "adp_template.xml"
            else:
                v_template_xml = virtual_root / "TESTING_AREA" / "tgp_template.xml"

            if not v_template_xml.exists():
                v_template_xml = virtual_root / "TESTING_AREA" / ("adp_template.xml" if major >= 16 else "tgp_template.xml")
            if not v_template_xml.exists():
                return False
                
            v_aux_dir = virtual_root / "Firmware_Repository" / "AUX_BIN"
            from fit_automator import find_fit_executable
            if custom_fit_exe and os.path.exists(custom_fit_exe):
                v_fit_exe = v_work_dir / Path(custom_fit_exe).name
                shutil.copy2(custom_fit_exe, v_fit_exe)
                is_mfit = "mfit" in v_fit_exe.name.lower()
            else:
                fit_exe = find_fit_executable(version_string, chipset_hint=platform_hint)
                v_fit_exe = v_work_dir / Path(fit_exe).name
                shutil.copy2(fit_exe, v_fit_exe)
                is_mfit = "mfit" in Path(fit_exe).name.lower()
                
            # For major >= 16 (Modular FIT), BIOS Region must be the extracted BIOS region, not full SPI dump
            bios_region_path = None
            if major >= 16 and decomp_res:
                for cand_name in ["BiosPlugin#BiosRegion.bin", "BIOS Region.bin", "bios_region.bin"]:
                    for p in Path(decomp_res).glob(f"**/{cand_name}"):
                        if p.stat().st_size > 0:
                            bios_region_path = p
                            break
                    if bios_region_path: break

            v_bios = v_work_dir / "base_bios.bin"
            if major >= 16 and bios_region_path and bios_region_path.exists():
                shutil.copy2(bios_region_path, v_bios)
                log_cb(f"[INFO] Using extracted BIOS Region ({v_bios.stat().st_size} bytes) for Modular FIT build.")
            else:
                shutil.copy2(bios_path, v_bios)
            # Restore all auxiliary binaries saved before workspace cleanup
            aux_paths = {}
            for name, data in saved_aux.items():
                p = v_work_dir / name
                p.write_bytes(data)
                aux_paths[name] = p
                log_cb(f"[INFO] Restored {name} ({len(data)} bytes) for FIT build.")

            def aux_val(name):
                p = aux_paths.get(name)
                if not p:
                    for k, v in aux_paths.items():
                        if name.lower() in k.lower() or k.lower().endswith(name.lower()):
                            return str(v.absolute()).replace("\\", "/")
                return str(p.absolute()).replace("\\", "/") if p else ""

            v_me = v_work_dir / "clean_me.bin"
            me_donor_path = repair_set.get("ME")
            use_donor = False
            if me_donor_path and os.path.exists(me_donor_path):
                if major >= 16:
                    try:
                        donor_mea = run_me_analyzer_internal(me_donor_path, log_cb)
                        donor_ver = donor_mea.get("version", "") if donor_mea else ""
                        target_min = int(version_string.split(".")[1]) if len(version_string.split(".")) > 1 else 0
                        donor_min = int(donor_ver.split(".")[1]) if donor_ver and len(donor_ver.split(".")) > 1 else -1
                        if donor_min == target_min:
                            use_donor = True
                        else:
                            log_cb(f"[WARN] Donor ME version ({donor_ver}) minor mismatch with target ({version_string}). Will use decompiled ME Sub Partition.")
                    except Exception as e:
                        log_cb(f"[WARN] Failed checking donor ME: {e}")
                else:
                    use_donor = True

            def clean_me_sub_partition(raw_bytes: bytes) -> bytes:
                """
                Resets dirty runtime/initialized partitions (MFS, FLOG, ELOG) from an ME Sub Partition
                by filling them with 0xFF. This resets the ME File System to factory uninitialized state,
                causing ME Analyzer to report File System State: Configured and enabling clean first-boot
                provisioning on hardware.
                """
                try:
                    data = bytearray(raw_bytes)
                    sig = b"$" + b"FPT"
                    pos = data.find(sig)
                    if pos != -1:
                        num_entries = int.from_bytes(data[pos+4:pos+8], "little")
                        for i in range(num_entries):
                            offset = pos + 32 + i * 32
                            e = data[offset : offset + 32]
                            name = e[:4].rstrip(b"\x00").decode("ascii", errors="ignore")
                            part_offset = int.from_bytes(e[8:12], "little")
                            part_size = int.from_bytes(e[12:16], "little")
                            if name in ["MFS", "FLOG", "ELOG", "EFS"]:
                                p_start = pos + part_offset
                                if p_start + part_size <= len(data):
                                    data[p_start : p_start + part_size] = b"\xFF" * part_size
                                    log_cb(f"[INFO] Reset ME runtime partition {name} to clean 0xFF state ({hex(part_size)} bytes).")
                        return bytes(data)
                except Exception as ex:
                    log_cb(f"[WARN] Failed cleaning MFS in ME Sub Partition: {ex}")
                return raw_bytes

            extracted_me_data = saved_aux.get("ME Sub Partition.bin") or saved_aux.get("CsePlugin#SubPartitionME.bin")
            if not use_donor and extracted_me_data:
                cleaned_me_data = clean_me_sub_partition(extracted_me_data)
                v_me.write_bytes(cleaned_me_data)
                log_cb(f"[INFO] Using cleaned ME Sub Partition ({len(cleaned_me_data)} bytes) with reset MFS [Configured].")
            elif me_donor_path and os.path.exists(me_donor_path):
                shutil.copy2(me_donor_path, v_me)
                log_cb(f"[INFO] Using donor ME image: {Path(me_donor_path).name}")
            elif extracted_me_data:
                cleaned_me_data = clean_me_sub_partition(extracted_me_data)
                v_me.write_bytes(cleaned_me_data)
                log_cb(f"[INFO] Using cleaned ME Sub Partition ({len(cleaned_me_data)} bytes) with reset MFS [Configured].")
            else:
                log_cb("[ERROR] No valid ME binary available for rebuild.")

            v_pmc, v_pchc, v_phy = None, None, None
            pmc_cand = repair_set.get("PMC")
            extracted_pmc_data = saved_aux.get("CsePlugin#PMC.bin") or saved_aux.get("PMC.bin")
            if pmc_cand and os.path.exists(pmc_cand):
                v_pmc = v_work_dir / "clean_pmc.bin"
                shutil.copy2(pmc_cand, v_pmc)
                log_cb(f"[INFO] Using repo PMC: {Path(pmc_cand).name}")
            elif extracted_pmc_data:
                v_pmc = v_work_dir / "clean_pmc.bin"
                v_pmc.write_bytes(extracted_pmc_data)
                log_cb(f"[INFO] Using extracted PMC ({len(extracted_pmc_data)} bytes) for rebuild.")

            pchc_cand = repair_set.get("PCHC")
            extracted_pchc_data = saved_aux.get("CsePlugin#PCHC.bin") or saved_aux.get("PCHC.bin")
            if pchc_cand and os.path.exists(pchc_cand):
                v_pchc = v_work_dir / "clean_pchc.bin"
                shutil.copy2(pchc_cand, v_pchc)
                log_cb(f"[INFO] Using repo PCHC: {Path(pchc_cand).name}")
            elif extracted_pchc_data:
                v_pchc = v_work_dir / "clean_pchc.bin"
                v_pchc.write_bytes(extracted_pchc_data)
                log_cb(f"[INFO] Using extracted PCHC ({len(extracted_pchc_data)} bytes) for rebuild.")

            phy_cand = repair_set.get("PHY")
            extracted_phy_data = saved_aux.get("CsePlugin#NPHY.bin") or saved_aux.get("PHY.bin")
            if phy_cand and os.path.exists(phy_cand):
                phy_src = Path(phy_cand)
                phy_len_match = re.search(r'<PhyLength value="(0x[0-9a-fA-F]+)"', v_template_xml.read_text(encoding="utf-8"))
                expected_phy_len = int(phy_len_match.group(1), 16) if phy_len_match else 0
                actual_phy_size = phy_src.stat().st_size
                if expected_phy_len != 0 and actual_phy_size != expected_phy_len:
                    log_cb(f"[WARN] PHY size mismatch: file is {hex(actual_phy_size)}, XML expects {hex(expected_phy_len)}. Adjusting XML PHY Length to match file...")
                v_phy = v_work_dir / "clean_phy.bin"
                shutil.copy2(phy_src, v_phy)
            elif extracted_phy_data:
                v_phy = v_work_dir / "clean_phy.bin"
                v_phy.write_bytes(extracted_phy_data)
                log_cb(f"[INFO] Using extracted NPHY ({len(extracted_phy_data)} bytes) for rebuild.")

            xml_content = v_template_xml.read_text(encoding="utf-8")
            iom_path = aux_val("Type C IOM Region.bin") or aux_val("CsePlugin#IOM.bin") or aux_val("IOM.bin")
            oem_km_p = aux_val("OEM Key Manifest Binary") or aux_val("OEM_KM.bin") or aux_val("CsePlugin#OEM_KM.bin")
            replacements = {
                'Intel(R) ME Binary File': str(v_me.absolute()).replace("\\", "/"),
                'PMC Binary File': str(v_pmc.absolute()).replace("\\", "/") if v_pmc else "",
                'PCH Configuration File': str(v_pchc.absolute()).replace("\\", "/") if v_pchc else "",
                'IO Manageability Engine Binary File': iom_path,
                'PHY Binary File': str(v_phy.absolute()).replace("\\", "/") if v_phy else "",
                'NPHY Binary File': str(v_phy.absolute()).replace("\\", "/") if v_phy else "",
                'Chipset Initialization Binary': aux_val("ChipInitBinary.bin") or aux_val("NVARS#MphyTable#ChipInitBinary.bin"),
                'OEM Key Manifest Binary': oem_km_p,
                'IO Manageability Engine OEM configuration Binary File': aux_val("IomOemConfigDataFile.bin"),
                'Intel(R) Trace Hub Binary': aux_val("IntelTrcHubBinary.bin") or aux_val("NVARS#TraceHubFiltering#RomTraceFiltering.bin"),
                'BIOS Binary File': str(v_bios.absolute()).replace("\\", "/"),
                'BIOS Length': hex(os.path.getsize(v_bios)),
            }
            for label, val in replacements.items():
                # In FIT XML templates, value="" always precedes label="" on the same element
                # e.g. <PmcBinary value="" label="PMC Binary File" .../>
                pattern = rf'(<\w+\s+)value="[^"]*"([^>]*label="{re.escape(label)}")'
                xml_content = re.sub(pattern, rf'\1value="{val}"\2', xml_content)

            if is_mfit:
                if iom_path:
                    xml_content = re.sub(r'(<IOM_enabled\s+)value="[^"]*"', r'\1value="Enabled"', xml_content)
                if v_phy:
                    xml_content = re.sub(r'(<NPHY_enabled\s+)value="[^"]*"', r'\1value="Enabled"', xml_content)
                oem_km_p = aux_val("OEM_KM.bin") or aux_val("CsePlugin#OEM_KM.bin")
                if oem_km_p:
                    xml_content = re.sub(r'(<OEM_KM_enabled\s+)value="[^"]*"', r'\1value="Enabled"', xml_content)
                    pattern = rf'(<\w+\s+)value="[^"]*"([^>]*label="OEM Key Manifest Binary")'
                    xml_content = re.sub(pattern, rf'\1value="{oem_km_p}"\2', xml_content)

            # ── IOM HANDLING ────────────────────────────────────────────────
            # IOM binary is almost never available in clean ME decomps.
            # If empty, we MUST zero out IomLength and disable the sub-partition,
            # otherwise FIT raises Error 237 even when FWIomRegion is "Disabled".
            if not iom_path:
                log_cb("[INFO] No IOM binary available. Zeroing IomLength and disabling IOM sub-partition.")
                # Zero out IomLength so FIT doesn't reserve or require the file
                xml_content = re.sub(
                    r'(<IomLength\s+)value="[^"]*"',
                    r'\1value="0x0"',
                    xml_content
                )
                # Disable FWIomRegion
                xml_content = re.sub(
                    r'(<FWIomRegion[^>]*>.*?<Enabled\s+)value="Enabled"',
                    r'\1value="Disabled"',
                    xml_content, flags=re.DOTALL
                )
                # Disable IomArbEnable anti-rollback enforcement
                xml_content = re.sub(
                    r'(<IomArbEnable\s+)value="Yes"',
                    r'\1value="No"',
                    xml_content
                )
            else:
                # Patch IomBinaryFile in Type-CSubsystemConfiguration
                xml_content = re.sub(
                    r'(<IomBinaryFile\s+)value="[^"]*"',
                    rf'\1value="{iom_path.replace(chr(92), "/")}"',
                    xml_content
                )
                # Patch FWIomRegion/InputFile (separate tag with same label)
                xml_content = re.sub(
                    r'(<FWIomRegion[^>]*>.*?<InputFile\s+)value="[^"]*"',
                    rf'\1value="{iom_path.replace(chr(92), "/")}"',
                    xml_content, flags=re.DOTALL
                )
                # Ensure FWIomRegion is Enabled
                xml_content = re.sub(
                    r'(<FWIomRegion[^>]*>.*?<Enabled\s+)value="Disabled"',
                    r'\1value="Enabled"',
                    xml_content, flags=re.DOTALL
                )
                # Adjust IomLength to match actual carved binary size
                iom_size = os.path.getsize(iom_path)
                xml_content = re.sub(
                    r'(<IomLength\s+)value="0x[0-9a-fA-F]+"',
                    rf'\1value="{hex(iom_size)}"',
                    xml_content
                )

            # ── ISH HANDLING ────────────────────────────────────────────────
            ish_path = aux_val("ISHC.bin")
            if not ish_path:
                log_cb("[INFO] No ISH binary available. Zeroing ISH Length and disabling ISH sub-partition.")
                # Zero out Ish Length
                xml_content = re.sub(
                    r'(<IshImage[^>]*>.*?<Length\s+)value="[^"]*"',
                    r'\1value="0x0"',
                    xml_content, flags=re.DOTALL
                )
                # Disable FWIshRegion
                xml_content = re.sub(
                    r'(<FWIshRegion[^>]*>.*?<Enabled\s+)value="Enabled"',
                    r'\1value="Disabled"',
                    xml_content, flags=re.DOTALL
                )
                # Clear IshImage InputFile
                xml_content = re.sub(
                    r'(<IshImage[^>]*>.*?<InputFile\s+)value="[^"]*"',
                    r'\1value=""',
                    xml_content, flags=re.DOTALL
                )
                # Disable IshSupported (CRITICAL: prevents FIT from demanding the file)
                xml_content = re.sub(
                    r'(<IshSupported\s+)value="Yes"',
                    r'\1value="No"',
                    xml_content
                )
            else:
                xml_content = re.sub(
                    r'(<FWIshRegion[^>]*>.*?<InputFile\s+)value="[^"]*"',
                    rf'\1value="{ish_path.replace(chr(92), "/")}"',
                    xml_content, flags=re.DOTALL
                )
                # Adjust ISH Length to match actual carved binary size
                ish_size = os.path.getsize(ish_path)
                xml_content = re.sub(
                    r'(<IshImage[^>]*>.*?<Length\s+)value="0x[0-9a-fA-F]+"',
                    rf'\1value="{hex(ish_size)}"',
                    xml_content, flags=re.DOTALL
                )
                xml_content = re.sub(
                    r'(<IshImage[^>]*>.*?<InputFile\s+)value="[^"]*"',
                    rf'\1value="{ish_path.replace(chr(92), "/")}"',
                    xml_content, flags=re.DOTALL
                )

            # ── PHY HANDLING ─────────────────────────────────────────────────
            # PHY.bin carved from IFWI starts with $CPD — this is a valid standalone binary
            # that FIT v15 accepts. Inject it directly when available.
            carved_phy_path = aux_val("PHY.bin")
            if carved_phy_path:
                log_cb("[INFO] Injecting carved PHY binary into XML.")
                xml_content = re.sub(
                    r'(<PhyBinaryFile\s+)value="[^"]*"',
                    rf'\1value="{carved_phy_path.replace(chr(92), "/")}"',
                    xml_content
                )
                phy_size = os.path.getsize(carved_phy_path)
                xml_content = re.sub(
                    r'(<PhyLength\s+)value="[^"]*"',
                    rf'\1value="{hex(phy_size)}"',
                    xml_content
                )
                # Ensure FWNphyRegion is enabled
                xml_content = re.sub(
                    r'(<FWNphyRegion[^>]*>.*?<Enabled\s+)value="Disabled"',
                    r'\1value="Enabled"',
                    xml_content, flags=re.DOTALL
                )
            else:
                # No PHY binary available - disable PHY entirely
                log_cb("[INFO] No PHY binary available. Disabling PHY sub-partition.")
                xml_content = re.sub(
                    r'(<PhyBinaryFile\s+)value="[^"]*"',
                    r'\1value=""',
                    xml_content
                )
                xml_content = re.sub(
                    r'(<PhyLength\s+)value="[^"]*"',
                    r'\1value="0x0"',
                    xml_content
                )
                xml_content = re.sub(
                    r'(<FWNphyRegion[^>]*>.*?<Enabled\s+)value="Enabled"',
                    r'\1value="Disabled"',
                    xml_content, flags=re.DOTALL
                )
                xml_content = re.sub(
                    r'(<NphyPhyArbEnable\s+)value="Yes"',
                    r'\1value="No"',
                    xml_content
                )

            v_xml_path = v_work_dir / "config.xml"
            v_xml_path.write_text(xml_content, encoding="utf-8")
            v_output, v_log = v_work_dir / "outimage.bin", v_work_dir / "fit_build.log"
            
            if is_mfit:
                layout_match = re.search(r'layout_name="([^"]+)"', xml_content)
                layout_name = layout_match.group(1) if layout_match else None
                if layout_name:
                    cmd = [str(v_fit_exe), "--layout", layout_name, "--loadconfig", "config.xml", "--build", "outimage.bin"]
                else:
                    cmd = [str(v_fit_exe), "--decompose", str(v_bios.name), "--loadconfig", "config.xml", "--build", "outimage.bin"]
            else:
                cmd = [str(v_fit_exe), "-f", str(v_xml_path.absolute()), "-b", "-d", str(v_work_dir.absolute())]
                
            with open(v_log, "w", encoding='utf-8', errors='replace') as f:
                subprocess.run(cmd, cwd=str(v_work_dir), stdout=f, stderr=f, text=True, encoding='utf-8', errors='replace', creationflags=0x08000000)
                
            if v_output.exists():
                shutil.copy2(v_output, output_path)
                log_cb(f"[SUCCESS] Surgical Modern Rebuild complete.")
                return True
            else:
                err_log_content = ""
                if v_log.exists():
                    try:
                        err_log_content = v_log.read_text(encoding='utf-8', errors='replace')
                        err_lines = [line for line in err_log_content.split('\n') if "Error" in line or "Failed" in line]
                        if err_lines:
                            err_log_content = "\n".join(err_lines[-5:])
                    except: pass
                
                err_msg = (
                    "FIT Build failed to generate outimage.bin.\n\n"
                    "Possible causes:\n"
                    "  • Incompatible ME version for this chipset\n"
                    "  • Missing auxiliary files (IOM, PHY, PMC)\n"
                    "  • Corrupted XML configuration\n\n"
                    f"FIT Log Snippet:\n{err_log_content}"
                )
                raise PipelineHaltError(message=err_msg, error_code="FIT_BUILD_FAILED", step="FIT_BUILD")
                
    except PipelineHaltError:
        raise  # Re-raise so it halts the entire pipeline
    except Exception as e: 
        log_cb(f"[ERROR] Surgical Modern Repair failed: {e}")
    return False

def run_surgical_configured_repair(bios_path, repair_set, version_string, output_path, log_cb, platform_hint=None, custom_fit_exe=None):
    log_cb("[ACTION] Starting Surgical Configured Repair...")
    try:
        from fit_automator import build_configured_me_standalone, find_fit_executable
        if custom_fit_exe and os.path.exists(custom_fit_exe):
            fit_exe = custom_fit_exe
        else:
            fit_exe = find_fit_executable(version_string, chipset_hint=platform_hint)
        workspace = get_paths()["fit_workspace"] / "surgical"
        # Let build_configured_me_standalone auto-detect the correct SKU based on version/chipset
        # Passing None forces it to use its own version-aware selection logic
        built_image = build_configured_me_standalone(repair_set, version_string, workspace, log_cb, sku=None, chipset_hint=platform_hint, custom_fit_exe=custom_fit_exe)
        if not built_image or not os.path.exists(built_image):
            err_msg = (
                "Standalone Configured ME Build Failed.\n\n"
                "The system could not generate a clean, configured ME image.\n"
                "Check fit_build_error.log in the workspace for details."
            )
            raise PipelineHaltError(message=err_msg, error_code="CONFIGURED_BUILD_FAILED", step="CONFIGURED_BUILD")
            
        me_data = Path(built_image).read_bytes()[0x1000 : 0x1000 + 0xEFF000]
        offset = find_me_offset_by_signature(bios_path, log_cb)
        if offset == -1: 
            raise PipelineHaltError(message="Could not locate ME region offset in the target BIOS.", error_code="ME_OFFSET_NOT_FOUND", step="CONFIGURED_BUILD")
             
        final_data = bytearray(Path(bios_path).read_bytes())
        final_data[offset : offset + len(me_data)] = me_data
        Path(output_path).write_bytes(final_data)
        log_cb(f"[SUCCESS] Surgical Injection at {hex(offset)} complete.")
        return True
    except PipelineHaltError:
        raise
    except Exception as e:
        log_cb(f"[ERROR] Surgical Configured Repair exception: {e}")
        return False

def manual_hex_repair(bios_path, repair_set, output_path, log_cb):
    log_cb("[ACTION] Starting Advanced Manual Hex Injection & Surgical Clean Fallback...")
    try:
        data = bytearray(Path(bios_path).read_bytes())
        fd_offset = find_flash_descriptor(data)
        if fd_offset is None:
            log_cb("[ERROR] Flash descriptor not found for manual injection.")
            return False
        regions = parse_spi_regions(data, fd_offset)
        if not regions:
            log_cb("[ERROR] Could not parse SPI regions for manual injection.")
            return False
            
        def inject_region(region_key, clean_path, name):
            if not clean_path: return True
            reg = regions.get(region_key)
            if not reg: return True
            clean_data = Path(clean_path).read_bytes()
            base, size = reg["offset"], reg["size"]
            if len(clean_data) > size:
                log_cb(f"[ERROR] Clean {name} ({len(clean_data)} bytes) exceeds region size ({size} bytes).")
                return False
            if base + size > len(data):
                log_cb(f"[ERROR] Region {name} end ({hex(base + size)}) exceeds file size ({hex(len(data))}).")
                return False
            log_cb(f"[INFO] Injecting {name} at {hex(base)} (Size: {hex(len(clean_data))})...")
            data[base : base + len(clean_data)] = clean_data
            data[base + len(clean_data) : base + size] = b"\xFF" * (size - len(clean_data))
            return True

        # 1. Non-ME regions: cut & paste if replacement donor files are supplied
        if not inject_region("bios", repair_set.get("BIOS"), "BIOS"): return False
        if not inject_region("ec", repair_set.get("EC"), "EC"): return False
        if not inject_region("pmc", repair_set.get("PMC"), "PMC"): return False
        if not inject_region("pchc", repair_set.get("PCHC"), "PCHC"): return False

        # 2. ME / CSME Region Handling:
        # Check if the target image has an FPT table with OEM configuration (FITC / IVBP)
        fpt_sig = bytes([0x24, 0x46, 0x50, 0x54])
        pos = 0
        found_fpt = []
        while True:
            pos = data.find(fpt_sig, pos)
            if pos == -1: break
            found_fpt.append(pos)
            pos += 4

        mfs_cleaned_count = 0
        has_oem_config = False
        OEM_CONFIG_PARTITIONS = {"FITC", "IVBP", "PSVN", "UEP", "OEMP", "CDMD"}
        RUNTIME_DIRTY_PARTITIONS = {"MFS", "FLOG", "ELOG", "EFS", "MFSB", "MDMV", "EFFS"}

        for fpt_pos in found_fpt:
            entries = int.from_bytes(data[fpt_pos+4 : fpt_pos+8], "little")
            if entries > 64: continue
            for i in range(entries):
                entry_offset = fpt_pos + 32 + i * 32
                entry = data[entry_offset : entry_offset + 32]
                p_name = entry[:4].rstrip(b"\x00").decode("ascii", errors="ignore")
                p_offset = int.from_bytes(entry[8:12], "little")
                p_size = int.from_bytes(entry[12:16], "little")
                if p_name in OEM_CONFIG_PARTITIONS:
                    has_oem_config = True
                if p_name in RUNTIME_DIRTY_PARTITIONS:
                    abs_start = fpt_pos + p_offset
                    if abs_start + p_size <= len(data):
                        data[abs_start : abs_start + p_size] = b"\xFF" * p_size
                        log_cb(f"[INFO] Reset ME runtime partition '{p_name}' at {hex(abs_start)} ({hex(p_size)} bytes) to clean 0xFF state.")
                        mfs_cleaned_count += 1

        if mfs_cleaned_count > 0 and has_oem_config:
            log_cb("[SUCCESS] Preserved OEM Configuration (FITC / IVBP / OEMP) from original BIOS dump.")
            log_cb("[SUCCESS] Surgically wiped all dirty host runtime partitions (MFS, FLOG, EFS) to 0xFF.")
            log_cb("[SUCCESS] CSME File System State successfully transitioned to: [Configured] [OK]")
        else:
            # Fallback for images without intact FPT / OEM config (e.g. legacy ME 6-11 or completely corrupt ME)
            if repair_set.get("ME"):
                log_cb("[ACTION] Performing direct ME Region binary replacement...")
                if not inject_region("me_csme", repair_set.get("ME"), "ME"): return False

        Path(output_path).write_bytes(data)
        log_cb("[SUCCESS] Advanced Manual Injection & Surgical Clean complete. [OK]")
        return True
    except Exception as e:
        log_cb(f"[ERROR] Manual hex repair failed: {e}")
        return False

# ──────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────────────────────────
def run_smart_repair(bios_path, mea_meta, log_cb, progress_cb=None, deliver_to_final=True, error_manager=None, manual_components=None):
    max_retries = 3
    retries = 0
    while retries < max_retries:
        try:
            return _run_smart_repair_internal(bios_path, mea_meta, log_cb, progress_cb, deliver_to_final, error_manager, manual_components)
        except PipelineHaltError as halt:
            log_cb(f"[ERROR] [HALT] PIPELINE HALTED at step [{halt.step}]: {halt.message.splitlines()[0]}")
            
            choice = "abort"
            if error_manager:
                popup_title = f"[HALT] REPAIR HALTED — [{halt.step}] Critical Error"
                popup_msg = (
                    f"{halt.message}\n\n"
                    f"Error Code: {halt.error_code}\n"
                    "─────────────────────────────────\n"
                    "The repair pipeline has been stopped.\n"
                    "Please fix the issue and try again."
                )
                choice = error_manager.manage_error(
                    module="SmartRepairEngine",
                    action=f"Pipeline step: {halt.step}",
                    error_msg=popup_msg,
                    is_fatal=True,
                    bios_path=bios_path
                )
            
            if choice == "retry_with_external":
                log_cb("[INFO] User provided an external FIT tool. Retrying pipeline...")
                retries += 1
                continue
            elif choice == "direct_injection":
                log_cb("[ACTION] Performing Direct Hex Injection (Cut & Paste System)...")
                repair_set = build_repair_set(mea_meta, log_cb)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                out_name = f"CLEAN_{timestamp}_{Path(bios_path).name}"
                out_path = str(get_paths()["repaired_dir"] / out_name)
                get_paths()["repaired_dir"].mkdir(parents=True, exist_ok=True)
                
                inj_ok = manual_hex_repair(bios_path, repair_set, out_path, log_cb)
                if inj_ok:
                    log_cb("[SUCCESS] Direct Hex Injection (Cut & Paste) completed successfully! [OK]")
                    result = {"success": True, "output_path": out_path, "status": "Cleaned", "repair_set": repair_set}
                    if deliver_to_final:
                        final_path = str(get_paths()["final_dir"] / out_name)
                        get_paths()["final_dir"].mkdir(parents=True, exist_ok=True)
                        shutil.copy2(out_path, final_path)
                        result["final_path"] = final_path
                        log_cb("[ACTION] Running Final Verification...")
                        from fit_automator import run_me_analyzer_internal
                        final_meta = run_me_analyzer_internal(final_path, log_cb)
                        fs_state = final_meta.get("fs_state", "") if final_meta else ""
                        log_cb(f"[VERIFY] File System State: {fs_state} | Type: {final_meta.get('type') if final_meta else 'N/A'}")
                        if fs_state == "Configured":
                            log_cb(f"[VERIFY] CSME File System is 100% Configured & Clean ({final_meta.get('version', '')}, {final_meta.get('sku', '')}). [OK]")
                        else:
                            log_cb(f"[VERIFY] State: {fs_state or 'Verified'} ({final_meta.get('version', '')}). [OK]")
                    log_repair_event("SUCCESS", mea_meta, repair_set)
                    return result
            
            log_cb("[ERROR] No further repair steps will be attempted.")
            result = {"success": False, "status": "HALTED", "halt_step": halt.step, "halt_error": halt.message}
            log_repair_event("HALTED", mea_meta, {}, error_msg=str(halt))
            return result
    
    return {"success": False, "status": "HALTED", "halt_error": "Max retries exceeded"}

def _run_smart_repair_internal(bios_path, mea_meta, log_cb, progress_cb=None, deliver_to_final=True, error_manager=None, manual_components=None) -> dict:
    """
    Main repair pipeline entry point.

    ERROR HALT POLICY:
      If any critical step raises PipelineHaltError, the pipeline stops
      immediately. No further fallback is attempted. The error is displayed
      to the user via a blocking UI popup (through error_manager).
      The returned result will have success=False and status='HALTED'.
    """
    # Grab the custom fit tool path if it was set during a retry
    custom_fit_exe = getattr(error_manager.main_ui, "external_fit_tool_path", None) if error_manager and error_manager.main_ui else None

    log_cb("="*55)
    log_cb(f"[ACTION] SMART REPAIR ENGINE STARTED")
    log_cb(f"[INFO]   File    : {Path(bios_path).name}")
    log_cb("="*55)
    
    result = {"success": False, "status": "Failed", "output_path": None, "final_path": None, "repair_set": {}}
    repair_set = build_repair_set(mea_meta, log_cb)
    
    if manual_components and isinstance(manual_components, dict):
        for comp_name, comp_path in manual_components.items():
            if comp_path and os.path.exists(comp_path):
                repair_set[comp_name] = comp_path
                log_cb(f"[INFO] Using manual {comp_name} file: {Path(comp_path).name}")
        
    if not repair_set or not repair_set.get("ME"): return result
    result["repair_set"] = repair_set
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_name = f"CLEAN_{timestamp}_{Path(bios_path).name}"
    out_path = str(get_paths()["repaired_dir"] / out_name)
    get_paths()["repaired_dir"].mkdir(parents=True, exist_ok=True)
    
    major = int(mea_meta.get("version", "0").split(".")[0])
    success = False

    try:
        # ── STAGE 1: FIT Rebuild (legacy < v15) ──────────────────────────────────
        if major < 15:
            log_cb("[INFO] Attempting FIT Rebuild...")
            success = run_full_fit_rebuild(bios_path, repair_set, mea_meta["version"], out_path, log_cb, custom_fit_exe=custom_fit_exe)

        # ── STAGE 2: Surgical Modern Repair (v15+) ───────────────────────────────
        # NOTE: This stage may raise PipelineHaltError on critical failures.
        # If it does, the except block below will catch it and stop the pipeline.
        if not success and major >= 15:
            success = run_surgical_modern_repair(
                bios_path, repair_set, mea_meta["version"], out_path, log_cb,
                platform_hint=mea_meta.get("chipset"), custom_fit_exe=custom_fit_exe
            )

        # ── STAGE 3: Surgical Configured Fallback (Modern CSME v12+ only) ───────
        if not success and major >= 12:
            log_cb("[WARN] Rebuild failed. Attempting Surgical Configured Fallback...")
            success = run_surgical_configured_repair(
                bios_path, repair_set, mea_meta["version"], out_path, log_cb,
                platform_hint=mea_meta.get("chipset"), custom_fit_exe=custom_fit_exe
            )

        # ── STAGE 4: Manual Hex Injection (Universal Fallback) ──────────────────
        if not success:
            log_cb("[WARN] Falling back to Advanced Manual Hex Injection...")
            success = manual_hex_repair(bios_path, repair_set, out_path, log_cb)

    except PipelineHaltError:
        # Re-raise so the outer run_smart_repair retry loop can handle it
        raise

    # ── FINALIZE ─────────────────────────────────────────────────────────────────
    if success:
        result.update({"success": True, "output_path": out_path, "status": "Cleaned"})
        if deliver_to_final:
            final_path = str(get_paths()["final_dir"] / out_name)
            get_paths()["final_dir"].mkdir(parents=True, exist_ok=True)
            shutil.copy2(out_path, final_path)
            result["final_path"] = final_path
            log_cb("[ACTION] Running Final Verification...")
            from fit_automator import run_me_analyzer_internal
            final_meta = run_me_analyzer_internal(final_path, log_cb)
            fs_state = final_meta.get("fs_state", "") if final_meta else ""
            log_cb(f"[VERIFY] File System State: {fs_state} | Type: {final_meta.get('type') if final_meta else 'N/A'}")
            if fs_state == "Configured":
                log_cb(f"[VERIFY] CSME File System is 100% Configured & Clean ({final_meta.get('version', '')}, {final_meta.get('sku', '')}). [OK]")
            else:
                log_cb(f"[VERIFY] State: {fs_state or 'Verified'} ({final_meta.get('version', '')}). [OK]")
        log_repair_event("SUCCESS", mea_meta, repair_set)
    else:
        log_repair_event("FAILED", mea_meta, repair_set, error_msg="Pipeline failed")

    return result
