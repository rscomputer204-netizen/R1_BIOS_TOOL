import os
import sys
import subprocess
import shutil
import contextlib
from pathlib import Path
import time
import re
import json
from mea_parser import parse_mea_output
from path_utils import get_app_root

def print_terminal_log(callback, message, level="INFO"):
    if level and not any(message.startswith(tag) for tag in ["[SUCCESS]", "[ERROR]", "[WARNING]", "[WARN]", "[INFO]", "[DEBUG]", "[ACTION]"]):
        full_msg = f"[{level}] {message}"
    else:
        full_msg = message
    if callback:
        try:
            callback(full_msg)
        except Exception:
            pass
    else:
        print(full_msg)

def find_fit_candidates(version_str, external_dir="external", chipset_hint=None):
    """
    Advanced scanner and matcher for 117+ Flash Image Tools.
    Uses metadata-driven architecture (fit_registry.json & fit_info.json) to rank tools
    by version accuracy, build freshness, and chipset compatibility.
    """
    import json
    
    base_dir = Path(get_app_root()) / external_dir / "FLASH System Tools"
    if not base_dir.exists():
        alt_dir = Path(get_app_root()) / "ALL_FIT_TOOLS_UNZIPPED"
        if alt_dir.exists():
            base_dir = alt_dir
        else:
            return []

    # 1. Try loading pre-built registry first for 0ms ultra-fast response
    tools_list = []
    reg_candidates = [
        base_dir / "fit_registry.json",
        Path(get_app_root()) / "fit_registry.json"
    ]
    reg_loaded = False
    for reg_path in reg_candidates:
        if reg_path.exists():
            try:
                with open(reg_path, "r", encoding="utf-8") as f:
                    tools_list = json.load(f)
                    reg_loaded = True
                    break
            except Exception:
                pass

    if not reg_loaded:
        # Dynamic scan from fit_info.json in each folder
        for item in base_dir.iterdir():
            if not item.is_dir():
                continue
            info_file = item / "fit_info.json"
            if info_file.exists():
                try:
                    with open(info_file, "r", encoding="utf-8") as inf_f:
                        info_data = json.load(inf_f)
                        info_data["rel_dir"] = item.name
                        info_data["rel_exe"] = os.path.join(item.name, info_data.get("executable", "fit.exe"))
                        tools_list.append(info_data)
                except:
                    pass

    # 2. Parse query version: e.g. 16.1.42.2872
    m_ver = re.search(r'(\d+(?:\.\d+)*)', version_str)
    q_parts = [int(x) for x in m_ver.group(1).split('.')] if m_ver else []
    q_major = q_parts[0] if len(q_parts) > 0 else 0
    q_minor = q_parts[1] if len(q_parts) > 1 else 0
    q_patch = q_parts[2] if len(q_parts) > 2 else 0
    q_build = q_parts[3] if len(q_parts) > 3 else 0

    # Determine if target is TXE / CSTXE
    is_txe_target = False
    if chipset_hint and any(k in chipset_hint.lower() for k in ["txe", "cstxe", "gemini", "apollo", "braswell", "bay trail"]):
        is_txe_target = True
    elif "txe" in version_str.lower() or "cstxe" in version_str.lower():
        is_txe_target = True

    candidates = []
    for t in tools_list:
        t_major = t.get("major", 0)
        t_minor = t.get("minor", 0)
        t_patch = t.get("patch", 0)
        t_build = t.get("build", 0)
        t_rev = t.get("revision", 0)
        t_is_txe = t.get("is_txe", False)
        t_rel_exe = t.get("rel_exe", "")

        # Resolve absolute exe path
        exe_path = base_dir / t_rel_exe
        if not exe_path.exists():
            folder_path = base_dir / t.get("folder", "")
            if folder_path.exists():
                for cand_exe in ["mfit.exe", "fit.exe", "fitc.exe", "ftoolc.exe"]:
                    check_p = folder_path / cand_exe
                    if check_p.exists():
                        exe_path = check_p
                        break
        if not exe_path.exists():
            continue

        # Filter TXE vs non-TXE
        if is_txe_target != t_is_txe:
            continue

        # Major version match is mandatory for CSME/ME architecture compatibility
        if t_major != q_major:
            continue

        score = 1000000

        # Exact Minor match
        if t_minor == q_minor:
            score += 500000
            
            # RULE: 3-Part Match (Major.Minor.Patch e.g. 11.8.50, 11.0.0, 12.0.49)
            # When first 3 parts match, this tool wins with absolute top priority!
            # 4th part (Build number) is ignored as per user requirement.
            if len(q_parts) >= 3 and t_patch == q_patch:
                score += 5000000
                if t_build > 0:
                    score += 500000 + t_build  # Real tool with specific build wins over generic packages
                else:
                    score += t_build
            else:
                # Fallback only when the exact 3-part patch is not available in database
                diff_patch = abs(t_patch - q_patch)
                score -= min(400000, diff_patch * 10000)
                score += t_build
        else:
            diff = abs(t_minor - q_minor)
            score -= min(300000, diff * 15000)

        # Revision bonus for fresher tool
        score += t_rev * 1000

        # Chipset preference bonus
        if chipset_hint:
            t_gen = t.get("generation", "").lower()
            t_title = t.get("title", "").lower()
            hint_words = [w for w in re.split(r'[\s,\-_]+', chipset_hint.lower()) if len(w) > 2]
            if any(w in t_gen or w in t_title for w in hint_words):
                score += 250000

        candidates.append((score, str(exe_path)))

    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates

def find_fit_executable(version_str, external_dir="external", chipset_hint=None):
    candidates = find_fit_candidates(version_str, external_dir, chipset_hint=chipset_hint)
    return candidates[0][1] if candidates else None

def find_partition_files(decomp_dir, region_keyword):
    """
    Finds all files in the decompile folder that match a specific region type.
    Includes robust aliases for FITC, FIT, and MFIT across ME/CSME generations.
    Ignores temporary, backup, and log files.
    """
    keyword_map = {
        "ME": [
            'me region.bin', 'me_region.bin', 'meregion.bin', 'me.bin',
            'cse_me.bin', 'csme.bin', 'cse region.bin', 'cse_region.bin', 'cseregion.bin',
            'me sub partition.bin', 'me_sub_partition.bin', 'mesubpartition.bin'
        ],
        "PMC": ['pmc region.bin', 'pmc_region.bin', 'pmcregion.bin', 'pmc.bin'],
        "PCHC": ['pchc region.bin', 'pchc_region.bin', 'pchcregion.bin', 'pchc.bin'],
        "PHY": ['phy region.bin', 'phy_region.bin', 'phyregion.bin', 'phy.bin'],
        "BIOS": ['bios region.bin', 'bios_region.bin', 'biosregion.bin', 'bios.bin'],
        "DESC": ['flash descriptor.bin', 'desc.bin', 'descriptor.bin', 'fd.bin']
    }
    
    targets = keyword_map.get(region_keyword, [])
    found = []
    if not os.path.exists(decomp_dir):
        return found
        
    for root, _, files in os.walk(decomp_dir):
        for f in files:
            f_lower = f.lower()
            if f_lower.endswith(('.bak', '.old', '.tmp', '.map', '.log', '.orig')):
                continue
            f_norm = f_lower.replace("_", " ").replace("-", " ")
            if f_lower in targets or any(k in f_lower or k in f_norm for k in targets):
                found.append(os.path.join(root, f))
    return found

def validate_decompiled_structure(decomp_dir, terminal_callback=None):
    """
    Performs deep validation of the decompiled directory.
    Checks for essential binaries and their sizes.
    Must have at least an ME/CSE region file and non-zero size.
    """
    if not decomp_dir or not os.path.exists(decomp_dir):
        print_terminal_log(terminal_callback, "[WARNING] Decompile folder does not exist.", "WARNING")
        return False

    essential_regions = ["ME"]  # Minimum requirement: ME or CSE region must exist
    for region in essential_regions:
        files = find_partition_files(decomp_dir, region)
        if not files:
            print_terminal_log(terminal_callback, f"[WARNING] Essential region {region} (ME/CSE) missing in decomposition directory.", "WARNING")
            return False
        
        # Check for valid non-zero byte files
        valid_file_found = False
        for f in files:
            if os.path.getsize(f) > 0:
                valid_file_found = True
                break
        if not valid_file_found:
            print_terminal_log(terminal_callback, f"[WARNING] Essential region {region} files are all empty (0-byte).", "WARNING")
            return False
                
    return True

def run_me_analyzer_internal(bios_path, terminal_callback=None):
    """
    Runs ME analysis on the given BIOS image and returns structured metadata.
    
    PRIMARY ENGINE: Native R1 CSME Analyzer (in-process, 100% reliable).
    SECONDARY FALLBACK: External MEA.py scripts across known repository paths.
    
    GUARANTEE: NEVER returns None. Always returns a dict with standard keys,
    preventing any 'NoneType' object has no attribute 'get' exceptions across the codebase.
    """
    safe_default = {
        "version":  "",
        "family":   "",
        "sku":      "",
        "chipset":  "",
        "stepping": "",
        "release":  "",
        "type":     "N/A",
        "fs_state": "",
        "fs_stage": "",
        "is_valid_me": False
    }

    if not bios_path or not os.path.exists(bios_path):
        return safe_default

    # 1. PRIMARY: Try native R1 CSME Analyzer
    try:
        from path_utils import get_app_root
        root = get_app_root()
        r1_dir = os.path.join(root, "R1_CSME_Analyzer")
        if r1_dir not in sys.path:
            sys.path.insert(0, r1_dir)
        from r1_csme_parser import R1CSMEAnalyzer
        
        analyzer = R1CSMEAnalyzer(bios_path)
        r1_res = analyzer.parse()
        if r1_res and (r1_res.get("is_valid_me") or r1_res.get("version") not in ("", "Unknown", None)):
            fs_val = r1_res.get("fs_stage") or r1_res.get("fs_state") or ""
            return {
                "version":     r1_res.get("version", ""),
                "family":      r1_res.get("family", ""),
                "sku":         r1_res.get("sku", ""),
                "chipset":     r1_res.get("chipset", ""),
                "stepping":    r1_res.get("stepping", ""),
                "release":     r1_res.get("release", "Production"),
                "type":        r1_res.get("type", "Extracted"),
                "fs_state":    fs_val,
                "fs_stage":    fs_val,
                "oem_config":  r1_res.get("oem_config", ""),
                "fitc_ver":    r1_res.get("fitc_ver", ""),
                "full_tag":    r1_res.get("full_tag", ""),
                "is_valid_me": r1_res.get("is_valid_me", True),
                "pmc_version": r1_res.get("pmc_version", ""),
                "pchc_version": r1_res.get("pchc_version", ""),
                "phy_version": r1_res.get("phy_version", ""),
            }
    except Exception as e:
        if terminal_callback:
            try:
                terminal_callback(f"[DEBUG] Native R1 Analyzer pass: {e}")
            except Exception:
                pass

    # 2. SECONDARY: Fallback to external MEA.py if present
    try:
        from path_utils import get_app_root, get_python_cmd
        root = get_app_root()
        possible_mea = [
            os.path.join(root, "external", "MEAnalyzer", "MEA.py"),
            os.path.join(root, "ME Analyzer", "MEA.py"),
            os.path.join(root, "ME_Analyzer_LATEST", "MEA.py"),
            os.path.join(root, "external", "MEA_Compare r374", "MEA.py"),
        ]
        mea_script = next((p for p in possible_mea if os.path.exists(p)), None)
        if mea_script:
            python_exe = get_python_cmd()
            cmd = [python_exe, mea_script, bios_path, "-exit", "-skip"]
            creationflags = 0x08000000 if os.name == 'nt' else 0
            res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', creationflags=creationflags)
            from mea_parser import parse_mea_output
            parsed = parse_mea_output(res.stdout)
            if parsed and isinstance(parsed, dict):
                safe_default.update(parsed)
                return safe_default
    except Exception:
        pass

    return safe_default

def force_manufacturing_mode(xml_path, state="Yes"):
    if not os.path.exists(xml_path):
        return
    with open(xml_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    opp_state = "No" if state == "Yes" else "Yes"
    opp_state_full = "Disabled" if state == "Yes" or state == "Enabled" else "Enabled"
    state_full = "Enabled" if state == "Yes" else "Disabled"
    
    modifications = [
        # Manufacturing Mode Settings
        (r'(<MeInManufacturingMode value=")([^"]*)(")', rf'\1{state}\3'),
        (r'(<IntelMeManufacturingMode value=")([^"]*)(")', rf'\1{state}\3'),
        (r'(<ManufacturingMode value=")([^"]*)(")', rf'\1{state_full}\3'),
        (r'(<CloseManufacturingMode value=")([^"]*)(")', rf'\1{opp_state}\3'),
        (r'(<FpfHwBindingEn value=")([^"]*)(")', rf'\1{opp_state_full}\3'),
        (r'(<NvarPostManUnLckd value=")([^"]*)(")', rf'\1{state}\3'),
        (r'(<HmrfpoEnable value=")([^"]*)(")', rf'\1{state}\3'),
        (r'(<FlexibleEomSettings value=")([^"]*)(")', r'\1Lock Descriptor and OEM Configs\3'),
        
        # Intel AMT / Manageability Settings (Commonly disabled for clean ME)
        (r'(<AmtSupported value=")([^"]*)(")', rf'\1{state}\3'),
        (r'(<IntelAmtSupported value=")([^"]*)(")', rf'\1{state}\3'),
        (r'(<MngAppSupported value=")([^"]*)(")', rf'\1{state}\3'),
        (r'(<NetServicesSupported value=")([^"]*)(")', rf'\1{state}\3'),
        (r'(<MngHwStatus value=")([^"]*)(")', rf'\1{state_full}\3'),
        (r'(<ManageabilityMode value=")([^"]*)(")', rf'\1{state_full}\3'),
        (r'(<MngAppPowerUpState value=")([^"]*)(")', rf'\1{state_full}\3'),
        
        # Intel Sensor Hub (ISH) / Thunderbolt
        (r'(<IshSupported value=")([^"]*)(")', rf'\1{state}\3'),
        (r'(<IshPowerUpState value=")([^"]*)(")', rf'\1{state_full}\3'),
        (r'(<TboltEnable value=")([^"]*)(")', rf'\1{state}\3'),
    ]
    modified = content
    for pattern, replacement in modifications:
        modified = re.sub(pattern, replacement, modified)
    
    # Inject if missing in specific kernels
    if "<IntelMeKernel" in modified:
        inject_tags = [
            f'<MeInManufacturingMode value="{state}" />',
            f'<NvarPostManUnLckd value="{state}" />',
            f'<IntelMeManufacturingMode value="{state}" />',
            f'<ManufacturingMode value="{state_full}" />',
            f'<CloseManufacturingMode value="{opp_state}" />',
            f'<AmtSupported value="{state}" />',
            f'<MngAppSupported value="{state}" />',
            f'<IshSupported value="{state}" />'
        ]
        for tag in inject_tags:
            # Match exact tag name to avoid substring match (e.g. ManufacturingMode vs MeInManufacturingMode)
            tag_name = tag.split(' ')[0][1:]
            tag_pattern = rf'<{tag_name}\s'
            if not re.search(tag_pattern, modified):
                # Add before kernel end
                modified = modified.replace("</IntelMeKernel>", f"    {tag}\n        </IntelMeKernel>")
    
    # Also handle IntelAmt section specifically if it exists
    if "<IntelAmt" in modified:
        amt_injects = [
            f'<AmtSupported value="{state}" />',
            f'<MngAppSupported value="{state}" />',
            f'<MngAppPowerUpState value="{state_full}" />',
            f'<NetServicesSupported value="{state}" />'
        ]
        for tag in amt_injects:
            tag_name = tag.split(' ')[0][1:]
            tag_pattern = rf'<{tag_name}\s'
            if not re.search(tag_pattern, modified):
                modified = modified.replace("</IntelAmt>", f"    {tag}\n        </IntelAmt>")

    with open(xml_path, 'w', encoding='utf-8') as f:
        f.write(modified)

def verify_image_integrity(file_path, terminal_callback=None):
    """
    Verifies the integrity of the generated BIOS image.
    Checks for common signatures like $FPT (ME/CSME header).
    """
    if not os.path.exists(file_path):
        return False
        
    try:
        with open(file_path, 'rb') as f:
            data = f.read(0x20000) # Read first 128KB to find headers
            
        # Check for Flash Descriptor signature
        if b"\x5A\xA5\xF0\x0F" not in data:
            print_terminal_log(terminal_callback, "[WARNING] Flash Descriptor signature missing.", "WARNING")
            return False
            
        # Check for ME/CSME header ($FPT)
        if b"$FPT" not in data:
            # For some modern versions it might be further down (e.g. after 1MB)
            with open(file_path, 'rb') as f:
                # Read up to 8MB to cover most BIOS layouts
                data_large = f.read(8 * 1024 * 1024)
                if b"$FPT" not in data_large:
                    print_terminal_log(terminal_callback, "[WARNING] ME/CSME Header ($FPT) not found.", "WARNING")
                    return False
        
        return True
    except:
        return False

def get_short_path(path):
    """
    Returns the 8.3 short path version of a Windows path to avoid issues with spaces.
    """
    if os.name != 'nt': return path
    try:
        import subprocess
        # Use cmd to get the short path
        cmd = f'cmd /c for %i in ("{path}") do @echo %~si'
        res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', shell=True)
        short = res.stdout.strip()
        return short if short else path
    except:
        return path

@contextlib.contextmanager
def mapped_drive_context(target_path):
    """
    Maps a path to a virtual drive letter using SUBST to avoid space-in-path issues.
    Yields the root path of the mapped drive.
    """
    target_path = str(Path(target_path).absolute())
    
    # Find an available drive letter
    import string
    import os
    used_drives = [d.split(":")[0].upper() for d in subprocess.check_output("wmic logicaldisk get name", shell=True, text=True, stderr=subprocess.DEVNULL).split() if ":" in d]
    available_drives = [l for l in string.ascii_uppercase[2:] if l not in used_drives] # Start from C:
    
    if not available_drives:
        yield Path(target_path)
        return
        
    drive = available_drives[-1] + ":" # Pick from end (Z:, Y:...)
    
    try:
        subprocess.run(["subst", drive, target_path], check=True, creationflags=0x08000000)
        success = True
    except:
        success = False
        
    if success:
        try:
            yield Path(drive + "\\")
        finally:
            subprocess.run(["subst", drive, "/d"], creationflags=0x08000000, stderr=subprocess.DEVNULL)
    else:
        yield Path(target_path)

def execute_fit_decompile(bios_path, version_string, workspace_dir, terminal_callback=None, external_dir="external", custom_fit_exe=None):
    # Step 1: Pre-analysis with ME Analyzer
    print_terminal_log(terminal_callback, "[INFO] Running Pre-analysis with ME Analyzer...")
    mea_data = run_me_analyzer_internal(bios_path, terminal_callback)
    chipset_hint = mea_data.get('chipset') if mea_data else None
    if chipset_hint:
        print_terminal_log(terminal_callback, f"[INFO] Detected Chipset: {chipset_hint}")
    
    # If a custom external FIT tool is provided, use it directly
    if custom_fit_exe and os.path.exists(custom_fit_exe):
        print_terminal_log(terminal_callback, f"[INFO] Using external FIT tool: {Path(custom_fit_exe).name}")
        candidates = [(9999999, custom_fit_exe)]
    else:
        # Step 2: Get ranked candidates using FITC tool version (Major.Minor.Patch)
        target_ver = version_string
        fitc_ver = mea_data.get('fitc_ver') if mea_data else None
        if fitc_ver and fitc_ver not in ("N/A", "Unknown", None, ""):
            target_ver = fitc_ver
            print_terminal_log(terminal_callback, f"[INFO] Matching FIT Tool by FITC Version: {target_ver}")
        candidates = find_fit_candidates(target_ver, external_dir, chipset_hint)
        if not candidates:
            print_terminal_log(terminal_callback, f"[ERROR] No Intel FIT found for version {target_ver}.", "ERROR")
            return None

    # Step 3: Retry Loop
    for attempt, (score, fit_exe) in enumerate(candidates, 1):
        tool_folder_name = Path(fit_exe).parent.name
        print_terminal_log(terminal_callback, f"[INFO] Attempt {attempt} of {len(candidates)}: Trying {tool_folder_name} (Score: {score})...")
        
        workspace = Path(workspace_dir)
        workspace.mkdir(exist_ok=True, parents=True)
        unique_dir = workspace / "FIT_Decompiled"
        if unique_dir.exists():
            try: shutil.rmtree(unique_dir, ignore_errors=True)
            except: pass
        unique_dir.mkdir(exist_ok=True)
        
        abs_fit_exe = get_short_path(os.path.abspath(fit_exe))
        abs_bios_path = get_short_path(os.path.abspath(bios_path))
        temp_bios = unique_dir / "image.bin"
        abs_temp_bios = get_short_path(os.path.abspath(temp_bios))
        
        try:
            shutil.copy2(os.path.abspath(bios_path), os.path.abspath(temp_bios))
        except Exception as e:
            print_terminal_log(terminal_callback, f"[ERROR] Copy failed: {str(e)}", "ERROR")
            continue

        xml_path = unique_dir / "config.xml"
        abs_xml_path = get_short_path(os.path.abspath(xml_path))
        is_mfit_tool = abs_fit_exe.lower().endswith("mfit.exe")
        fit_dir = get_short_path(os.path.dirname(os.path.abspath(fit_exe)))

        if is_mfit_tool:
            cmd = [abs_fit_exe, "--decompose", abs_temp_bios, "--saveconfig", abs_xml_path]
        else:
            cmd = [abs_fit_exe, "-f", abs_temp_bios, "-save", abs_xml_path, "-i", "disable"]

        try:
            sub_res = subprocess.run(cmd, cwd=fit_dir, capture_output=True, text=True, encoding='utf-8', errors='replace', creationflags=0x08000000)
            
            # Fallback search for XML
            if not xml_path.exists():
                for base in [unique_dir, Path(fit_dir)]:
                    for possible in [base / "image.xml", base / "config.xml"]:
                        if possible.exists():
                            shutil.copy2(possible, xml_path)
                            break
                    if xml_path.exists(): break

            if xml_path.exists():
                decomp_target = unique_dir / "image"
                moved_from = None
                if not decomp_target.exists():
                    fit_decomp = Path(fit_dir) / "image"
                    if not fit_decomp.exists():
                        short_stem = Path(abs_temp_bios).stem
                        for cand_name in ["image", short_stem, Path(temp_bios).stem, Path(bios_path).stem]:
                            cand_p = Path(fit_dir) / cand_name
                            if cand_p.exists() and cand_p.is_dir():
                                fit_decomp = cand_p
                                break
                    if not fit_decomp.exists() and Path(fit_dir).exists():
                        try:
                            from clean_fit_tools import GENUINE_SUBDIRS
                        except Exception:
                            GENUINE_SUBDIRS = set()
                        for sub in Path(fit_dir).iterdir():
                            if sub.is_dir() and sub.name.lower() not in GENUINE_SUBDIRS:
                                if (sub / "Decomp").exists() or list(sub.glob("*.bin")):
                                    fit_decomp = sub
                                    break
                    if fit_decomp.exists():
                        moved_from = str(fit_decomp.absolute())
                        shutil.move(str(fit_decomp), str(decomp_target))
                    else:
                        subdirs = [d for d in unique_dir.iterdir() if d.is_dir() and d.name != "image"]
                        decomp_target = subdirs[0] if subdirs else unique_dir
                        
                if moved_from and xml_path.exists():
                    try:
                        x_txt = xml_path.read_text(encoding='utf-8')
                        x_txt = x_txt.replace(moved_from, str(decomp_target.absolute()))
                        x_txt = x_txt.replace(moved_from.replace('\\', '/'), str(decomp_target.absolute()).replace('\\', '/'))
                        xml_path.write_text(x_txt, encoding='utf-8')
                    except Exception as ex:
                        print_terminal_log(terminal_callback, f"[WARN] Failed to rewrite xml paths: {ex}", "WARN")
                
                # Deep Validation
                if validate_decompiled_structure(decomp_target, terminal_callback):
                    print_terminal_log(terminal_callback, f"[SUCCESS] [OK] FIT Decompile Complete via {tool_folder_name}")
                    print_terminal_log(terminal_callback, f"[INFO] Decompiled Files Location: {os.path.abspath(decomp_target)}")
                    print_terminal_log(terminal_callback, f"[INFO] Decompiled layout verified: config.xml and partition binaries ready.")
                    
                    # Clean any residual junk in tool folder
                    try:
                        import clean_fit_tools
                        clean_fit_tools.clean_specific_tool_dir(fit_dir)
                    except Exception:
                        pass
                        
                    return str(decomp_target)
                else:
                    print_terminal_log(terminal_callback, f"[WARNING] Attempt {attempt} validation failed with {tool_folder_name}. Trying next tool in queue...", "WARNING")
            else:
                print_terminal_log(terminal_callback, f"[WARNING] Attempt {attempt} failed to generate config with {tool_folder_name}. Trying next tool in queue...", "WARNING")
            
        except Exception as e:
            print_terminal_log(terminal_callback, f"[ERROR] Execution failed for {tool_folder_name}: {str(e)}", "ERROR")
            continue

    print_terminal_log(terminal_callback, "[ERROR] Intel FIT decompilation failed across all candidate tools. Safety lock engaged.", "ERROR")
    print_terminal_log(terminal_callback, "[NOTICE] Direct Hex Injection Mode is permanently removed to protect motherboard from No-Display bricking.", "ERROR")
    return None

def execute_fit_rebuild(corrupt_bios_path, clean_paths_dict, version_string, output_path, terminal_callback=None, external_dir="external", custom_fit_exe=None):
    # Pre-analysis for ranking
    mea_data = run_me_analyzer_internal(corrupt_bios_path, terminal_callback)
    chipset_hint = mea_data.get('chipset') if mea_data else None
    
    # If a custom external FIT tool is provided, use it directly
    if custom_fit_exe and os.path.exists(custom_fit_exe):
        print_terminal_log(terminal_callback, f"[INFO] Using external FIT tool: {Path(custom_fit_exe).name}")
        candidates = [(9999999, custom_fit_exe)]
    else:
        target_ver = version_string
        fitc_ver = mea_data.get('fitc_ver') if mea_data else None
        if fitc_ver and fitc_ver not in ("N/A", "Unknown", None, ""):
            target_ver = fitc_ver
            print_terminal_log(terminal_callback, f"[INFO] Matching FIT Rebuild Tool by FITC Version: {target_ver}")
        candidates = find_fit_candidates(target_ver, external_dir, chipset_hint)
        if not candidates:
            print_terminal_log(terminal_callback, f"[ERROR] No Intel FIT found for version {target_ver}.", "ERROR")
            return False

    for attempt, (score, fit_exe) in enumerate(candidates, 1):
        tool_name = Path(fit_exe).parent.name
        print_terminal_log(terminal_callback, f"[INFO] Rebuild Attempt {attempt} of {len(candidates)}: Trying {tool_name} (Score: {score})...")
        
        # Use short path for the executable to avoid issues with spaces and special characters
        fit_exe_safe = get_short_path(os.path.abspath(fit_exe))
        fit_dir = get_short_path(os.path.dirname(os.path.abspath(fit_exe)))
        
        fit_workspace = Path(get_app_root()) / "FIT_WORKSPACE"
        if fit_workspace.exists():
            shutil.rmtree(fit_workspace, ignore_errors=True)
        fit_workspace.mkdir(exist_ok=True)
        
        temp_corrupt = fit_workspace / "corrupt.bin"
        shutil.copy2(corrupt_bios_path, temp_corrupt)
        xml_path = fit_workspace / "config.xml"
        is_mfit_tool = fit_exe.lower().endswith("mfit.exe")
        is_legacy_fitc = "fitc.exe" in str(fit_exe_safe).lower()
        
        # ── 1. RUN DECOMPILE TO GET CONFIG & EXTRACTED PARTITIONS ─────────────
        print_terminal_log(terminal_callback, f"[INFO] Running Intel FIT Decompile via {tool_name}...")
        if is_mfit_tool:
            cmd = [fit_exe_safe, "--decompose", temp_corrupt.name, "--saveconfig", xml_path.name.replace(" ", "_")]
        elif is_legacy_fitc:
            cmd = [fit_exe_safe, "/b", "/w", str(fit_workspace), "/s", str(fit_workspace), "/d", str(fit_workspace), "/save", xml_path.name.replace(" ", "_"), temp_corrupt.name]
        else:
            cmd = [fit_exe_safe, "-f", temp_corrupt.name, "-save", xml_path.name.replace(" ", "_"), "-i", "disable"]
        
        subprocess.run(cmd, cwd=str(fit_workspace), capture_output=True, text=True, encoding='utf-8', errors='replace', creationflags=0x08000000)
        
        if not xml_path.exists():
            for possible in [fit_workspace / "corrupt.xml", fit_workspace / "image.xml", Path(fit_dir) / "config.xml", Path(fit_dir) / "corrupt.xml"]:
                if possible.exists():
                    shutil.copy2(possible, xml_path)
                    break
        
        # Locate decompiled directory
        decomp_target = fit_workspace / "corrupt"
        if not decomp_target.exists():
            for cand_name in ["corrupt", Path(temp_corrupt).stem, Path(corrupt_bios_path).stem, "image", "Decomp"]:
                cand_p = Path(fit_dir) / cand_name
                if cand_p.exists() and cand_p.is_dir():
                    try:
                        shutil.move(str(cand_p), str(decomp_target))
                        break
                    except:
                        pass
        
        if not decomp_target.exists():
            if is_mfit_tool:
                subprocess.run([fit_exe_safe, "--decompose", temp_corrupt.name], cwd=str(fit_workspace), capture_output=True, creationflags=0x08000000)
            elif not is_legacy_fitc and xml_path.exists():
                subprocess.run([fit_exe_safe, "-f", xml_path.name, "-b", "-o", "dummy_out.bin"],
                               cwd=str(fit_workspace), capture_output=True, creationflags=0x08000000)
        
        if not decomp_target.exists():
            subdirs = [d for d in fit_workspace.iterdir() if d.is_dir() and d.name != "corrupt"]
            if subdirs:
                decomp_target = subdirs[0]
            else:
                for cand_name in ["corrupt", Path(temp_corrupt).stem, Path(corrupt_bios_path).stem, "image", "Decomp"]:
                    cand_p = Path(fit_dir) / cand_name
                    if cand_p.exists() and cand_p.is_dir():
                        try:
                            shutil.move(str(cand_p), str(decomp_target))
                            break
                        except:
                            pass

        # ── 2. STRICT DECOMPILE VALIDATION GATE ───────────────────────────────
        # "ডি কম্পাইল ছাড়া কোন কাজ হবে না এরকম লজিক তৈরি করতে হবে"
        decompile_ok = False
        if xml_path.exists() and decomp_target and decomp_target.exists():
            if validate_decompiled_structure(decomp_target, terminal_callback):
                decompile_ok = True
                print_terminal_log(terminal_callback, f"[SUCCESS] [OK] FIT Decompile Complete via {tool_name}")
                print_terminal_log(terminal_callback, f"[INFO] Decompiled Files Location: {os.path.abspath(decomp_target)}")
                print_terminal_log(terminal_callback, f"[INFO] Decompiled layout verified: {xml_path.name} and partition binaries ready.")
            else:
                print_terminal_log(terminal_callback, f"[WARNING] Attempt {attempt}: Decompiled structure incomplete or missing partitions with {tool_name}. Trying next tool in queue...", "WARNING")
        else:
            print_terminal_log(terminal_callback, f"[WARNING] Attempt {attempt}: FIT Decompile failed to produce config or partitions with {tool_name}. Trying next tool in queue...", "WARNING")

        if not decompile_ok:
            continue  # STRICT GATE: NO CLEANING OR COMPILING PERMITTED WITHOUT SUCCESSFUL DECOMPILE!

        # ── 3. REPLACE / CLEAN ME REGION IN DECOMPILED WORKSPACE ─────────────
        clean_me_file = clean_paths_dict.get("ME")
        if clean_me_file and os.path.exists(clean_me_file):
            print_terminal_log(terminal_callback, f"[INFO] Replacing ME Region using matched clean binary: {Path(clean_me_file).name}")
            me_targets = find_partition_files(decomp_target, "ME")
            replaced = False
            for t in me_targets:
                try:
                    if os.path.exists(t): os.chmod(t, 0o666)
                    shutil.copy2(clean_me_file, t)
                    replaced = True
                except Exception as ex:
                    print_terminal_log(terminal_callback, f"[WARNING] Failed to replace ME partition: {ex}", "WARNING")
            
            if replaced:
                print_terminal_log(terminal_callback, f"[SUCCESS] [OK] ME Region Replacement Complete ({Path(clean_me_file).name})")
            else:
                print_terminal_log(terminal_callback, f"[WARNING] Attempt {attempt}: No ME partition file found in {decomp_target.name}. Trying next tool...", "WARNING")
                continue
        else:
            print_terminal_log(terminal_callback, f"[WARNING] Attempt {attempt}: Clean ME binary not provided or missing. Trying next tool...", "WARNING")
            continue

        # Patch XML for OEM State (Manufacturing Mode = No)
        force_manufacturing_mode(xml_path, state="No")
        print_terminal_log(terminal_callback, "[INFO] Manufacturing Mode set to Closed (No Late Display).")

        # ── 4. REBUILD / COMPILE ─────────────────────────────────────────────
        print_terminal_log(terminal_callback, f"[INFO] Compiling / Rebuilding BIOS firmware image via {tool_name}...")
        final_out = fit_workspace / "outimage.bin"
        if is_mfit_tool:
            cmd = [fit_exe_safe, "--decompose", temp_corrupt.name, "--loadconfig", xml_path.name, "--build", final_out.name]
        elif is_legacy_fitc:
            cmd = [fit_exe_safe, "/b", "/w", str(fit_workspace), "/s", str(fit_workspace), "/d", str(fit_workspace)]
            if clean_paths_dict.get("ME"):
                cmd.extend(["/me", str(clean_paths_dict["ME"])])
            cmd.append(xml_path.name)
        else:
            cmd = [fit_exe_safe, "-f", xml_path.name, "-b", "-o", final_out.name, "-i", "disable"]
            
        res = subprocess.run(cmd, cwd=str(fit_workspace), capture_output=True, text=True, encoding='utf-8', errors='replace', creationflags=0x08000000)

        # Check alternative output filenames that FIT might generate
        if not final_out.exists() or final_out.stat().st_size == 0:
            for alt_out in [fit_workspace / "image.bin", fit_workspace / "dummy_out.bin", Path(fit_dir) / "outimage.bin"]:
                if alt_out.exists() and alt_out.stat().st_size > 0:
                    shutil.copy2(alt_out, final_out)
                    break

        # Capture and log FIT error details if compile failed
        if not final_out.exists() or final_out.stat().st_size == 0:
            fit_err_lines = []
            if res.stdout:
                for line in res.stdout.splitlines():
                    if any(w in line.lower() for w in ["error", "failed", "exception"]):
                        fit_err_lines.append(line.strip())
            if res.stderr:
                for line in res.stderr.splitlines():
                    if any(w in line.lower() for w in ["error", "failed", "exception"]):
                        fit_err_lines.append(line.strip())
            fit_log_p = Path(fit_workspace) / "fit.log"
            if not fit_err_lines and fit_log_p.exists():
                try:
                    with open(str(fit_log_p), "r", encoding="utf-8", errors="replace") as fl:
                        for line in fl.readlines()[-20:]:
                            if any(w in line.lower() for w in ["error", "failed", "exception"]):
                                fit_err_lines.append(line.strip())
                except Exception:
                    pass
            for el in fit_err_lines[:5]:
                print_terminal_log(terminal_callback, f"[FIT ERROR] {el}", "ERROR")

        if final_out.exists() and final_out.stat().st_size > 0:
            # Final Integrity Check
            if verify_image_integrity(final_out, terminal_callback):
                print_terminal_log(terminal_callback, f"[SUCCESS] [OK] FIT Compile / Rebuild Complete via {tool_name}")
                shutil.copy2(final_out, output_path)
                print_terminal_log(terminal_callback, "[SUCCESS] Full CSME Rebuild Completed!")
                try:
                    import clean_fit_tools
                    clean_fit_tools.clean_specific_tool_dir(fit_dir)
                except Exception:
                    pass
                return True
            else:
                print_terminal_log(terminal_callback, f"[WARNING] Attempt {attempt}: Integrity check failed for build via {tool_name}. Trying next tool...", "WARNING")
        else:
            print_terminal_log(terminal_callback, f"[WARNING] Attempt {attempt}: Compile failed to produce binary with {tool_name}. Trying next tool...", "WARNING")

    print_terminal_log(terminal_callback, "[ERROR] All build attempts failed.", "ERROR")
    return False

def build_configured_me_standalone(repair_set, version_string, workspace_dir, log_cb=None, sku=None, chipset_hint=None, custom_fit_exe=None):
    """
    Builds a 'Configured' ME image from scratch using clean components and a dummy BIOS.
    Used when the original BIOS is too corrupted to decompose.
    """
    if custom_fit_exe and os.path.exists(custom_fit_exe):
        fit_exe = custom_fit_exe
        print_terminal_log(log_cb, f"[INFO] Using external FIT tool: {Path(custom_fit_exe).name}")
    else:
        fit_exe = find_fit_executable(version_string, chipset_hint=chipset_hint)
    if not fit_exe:
        print_terminal_log(log_cb, f"FIT tool for {version_string} not found", "ERROR")
        return None
        
    workspace = Path(workspace_dir)
    workspace.mkdir(exist_ok=True, parents=True)
    
    # 1. Create Dummy BIOS
    dummy_bios = workspace / "dummy_bios.bin"
    dummy_bios.write_bytes(b"\xFF" * 1024 * 1024) # 1MB dummy
    
    # 2. Determine SKU (Simple heuristic for modern platforms)
    is_lp = "LP" in repair_set.get("SKU_HINT", "") or "LP" in repair_set.get("CHIPSET", "")
    is_corporate = "COR" in repair_set.get("SKU_HINT", "") or "Corporate" in repair_set.get("SKU_HINT", "")
    if not sku:
        if "16." in version_string:
            sku = "ADP-P-B0 Corporate" if is_corporate else "ADP-P-B0 Consumer"
        elif "15." in version_string:
            # Determine TGP stepping from chipset_hint (e.g., "TGP-LP B" vs "TGP-LP C")
            is_c_step = chipset_hint and "-LP C" in chipset_hint
            tgp_step = "C0" if is_c_step else "B0"
            sku = f"TGP-LP-{tgp_step} Premium U" if is_lp else f"TGP-H-{tgp_step} No Emulation"
        elif "14." in version_string:
            sku = "CMP-LP No Emulation" if is_lp else "CMP-H No Emulation"
        elif "12." in version_string:
            sku = "CNP-LP Premium U"
        elif "11." in version_string:
            sku = "SKL/KBP/HAP L/LP/U/Y Premium"
        else:
            sku = "CNP-LP Premium U"

    # 3. Create XML
    xml_path = workspace / "config_scratch.xml"
    me_file = get_short_path(str(Path(repair_set['ME']).absolute())).replace("\\", "/")
    pmc_file = get_short_path(str(Path(repair_set['PMC']).absolute())).replace("\\", "/") if repair_set.get('PMC') else ""
    pchc_file = get_short_path(str(Path(repair_set['PCHC']).absolute())).replace("\\", "/") if repair_set.get('PCHC') else ""
    dummy_bios_str = get_short_path(str(dummy_bios.absolute())).replace("\\", "/")

    # For v15+ (TGP), IOM is required in XML but we don't have standalone IOM binaries.
    # Disable it explicitly to prevent Error 237.
    iom_section = ""
    if "15." in version_string or "16." in version_string:
        iom_section = """
        <SubPartitions>
            <FWIomRegion>
                <Enabled value="Disabled" />
            </FWIomRegion>
        </SubPartitions>"""

    xml_content = f"""<?xml version='1.0' encoding='utf-8'?>
<FitData version="10.22" sku="{sku}">
    <BuildSettings>
        <BuildResults>
            <BuildOutputFilename value="outimage.bin" />
        </BuildResults>
    </BuildSettings>
    <FlashLayout>
        <BiosRegion>
            <InputFile value="{dummy_bios_str}" />
        </BiosRegion>
        <Ifwi_IntelMePmcRegion>
            <MeRegionFile value="{me_file}" />
            <PmcBinary value="{pmc_file}" />
        </Ifwi_IntelMePmcRegion>
        <SubPartitions>
            <PchcSubPartitionData>
                <InputFile value="{pchc_file}" />
            </PchcSubPartitionData>
        </SubPartitions>{iom_section}
    </FlashLayout>
    <FlashSettings>
        <FlashComponents>
            <NumberOfComponents value="1" />
            <FlashComponent1Size value="16MB" />
        </FlashComponents>
    </FlashSettings>
</FitData>
"""
    xml_path.write_text(xml_content)
    
    # 4. Build
    print_terminal_log(log_cb, f"[INFO] Building Standalone Configured Image for {version_string}...")
    cmd = [fit_exe, "-f", str(xml_path), "-b", "-i", "disable", "-d", str(workspace)]
    res = subprocess.run(cmd, cwd=str(workspace), capture_output=True, text=True, encoding='utf-8', errors='replace')
    
    out_file = workspace / "outimage.bin"
    if out_file.exists():
        print_terminal_log(log_cb, "[SUCCESS] Standalone Configured Build complete.")
        return str(out_file)
    
    # Debug: log full FIT output if failed
    with open(workspace / "fit_build_error.log", "w") as f:
        f.write(res.stdout + "\n" + res.stderr)
    
    print_terminal_log(log_cb, f"[ERROR] Build failed. Check fit_build_error.log", "ERROR")
    return None
