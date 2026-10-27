import os
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
    if callback:
        callback(f"[{level}] {message}")
    else:
        print(f"[{level}] {message}")

def find_fit_candidates(version_str, external_dir="external", chipset_hint=None):
    """
    Advanced scanner for Flash Image Tools. 
    Identifies major, minor, and revision (rX) numbers to rank tools by freshness
    and chipset compatibility.
    """
    parts = version_str.split('.')
    major_v = parts[0]
    minor_v = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    
    base_dir = Path(get_app_root()) / external_dir / "FLASH System Tools"
    if not base_dir.exists():
        return []
        
    adp_pref = ["v16.0 r2", "v16.0 r8", "v16.0", "v16.1"] if minor_v == 0 else (["v16.50", "v16.1"] if minor_v >= 50 else ["v16.1", "v16.0 r2", "v16.0 r8"])

    REVISION_PREFERENCES = {
        "Tiger": ["v15.0"],
        "TGL": ["v15.0"],
        "TGP": ["v15.0"],
        "ADP": adp_pref,
        "Alder": adp_pref,
        "Raptor": ["v16.50", "v16.1"],
        "Comet": ["v14.0.20", "v14.0.11"],
        "Ice": ["v13.30", "v13.0"],
        "Coffee": ["v12"],
        "Kaby": ["v11"]
    }
    
    candidates = []
    for item in base_dir.iterdir():
        if not item.is_dir():
            continue
            
        name_lower = item.name.lower()
        
        # Match Major Version (e.g. v16)
        if re.search(rf'[^\d]v{major_v}([^\d]|$)', " " + name_lower):
            # Base score
            score = 10
            
            # 1. Extract Version & Revision for ranking (e.g. v14.0.20 r15 -> (14, 0, 20, 15))
            ver_match = re.search(r'v(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:[^\d]*r(\d+))?', name_lower)
            if ver_match:
                try:
                    v_maj = int(ver_match.group(1))
                    v_min = int(ver_match.group(2)) if ver_match.group(2) else 0
                    v_pat = int(ver_match.group(3)) if ver_match.group(3) else 0
                    v_rev = int(ver_match.group(4)) if ver_match.group(4) else 0
                    
                    # Boost score based on version freshness
                    # Formula: Major*10000 + Minor*1000 + Patch*100 + Revision
                    score += (v_maj * 10000) + (v_min * 1000) + (v_pat * 100) + v_rev
                    # Exact minor version match gets high priority
                    if v_min == minor_v:
                        score += 300000
                except: pass

            # 2. Chipset Preference Match (High Priority)
            if chipset_hint:
                for hint_key, pref_list in REVISION_PREFERENCES.items():
                    if hint_key.lower() in chipset_hint.lower():
                        print(f"DEBUG: Chipset Hint Match! {hint_key} in {chipset_hint}")
                        for idx, pref in enumerate(pref_list):
                            if pref.lower() in name_lower:
                                print(f"DEBUG: Preference Match! {pref} in {name_lower}")
                                score += (2000000 - (idx * 200000)) # Increased gap to override version freshness
                                break

            # 3. Handle TXE/CSTXE special case
            if "txe" in name_lower or "cstxe" in name_lower:
                score += 50
                
            # 4. Find the executable
            found_exe = None
            for root, _, files in os.walk(item):
                for file in files:
                    if file.lower() in ['fit.exe', 'fitc.exe', 'mfit.exe']:
                        if any(k in root.lower() for k in ['win32', 'windows', 'win']):
                            found_exe = os.path.join(root, file)
                            break
                if found_exe: break
            
            if found_exe:
                candidates.append((score, found_exe))
    
    # Sort candidates by score descending
    candidates.sort(key=lambda x: x[0], reverse=True)
    
    # Debug log the ranked list
    for s, p in candidates: print(f"DEBUG: Ranked {p} with score {s}")
    
    return candidates

def find_fit_executable(version_str, external_dir="external", chipset_hint=None):
    candidates = find_fit_candidates(version_str, external_dir, chipset_hint=chipset_hint)
    return candidates[0][1] if candidates else None

def find_partition_files(decomp_dir, region_keyword):
    """
    Finds all files in the decompile folder that match a specific region type.
    """
    keyword_map = {
        "ME": ['me region.bin', 'me.bin', 'cse_me.bin', 'cse region.bin', 'me sub partition.bin'],
        "PMC": ['pmc region.bin', 'pmc.bin', 'pmc_region.bin'],
        "PCHC": ['pchc region.bin', 'pchc.bin', 'pchc_region.bin'],
        "PHY": ['phy region.bin', 'phy.bin', 'phy_region.bin']
    }
    
    targets = keyword_map.get(region_keyword, [])
    found = []
    if not os.path.exists(decomp_dir):
        return found
        
    for root, _, files in os.walk(decomp_dir):
        for f in files:
            if f.lower() in targets or any(k in f.lower() for k in targets):
                found.append(os.path.join(root, f))
    return found

def validate_decompiled_structure(decomp_dir, terminal_callback=None):
    """
    Performs deep validation of the decompiled directory.
    Checks for essential binaries and their sizes.
    """
    essential_regions = ["ME"] # Minimum requirement
    for region in essential_regions:
        files = find_partition_files(decomp_dir, region)
        if not files:
            print_terminal_log(terminal_callback, f"[WARNING] Essential region {region} missing in decomposition.", "WARNING")
            return False
        
        # Check for 0-byte files
        for f in files:
            if os.path.getsize(f) == 0:
                print_terminal_log(terminal_callback, f"[WARNING] Region file {os.path.basename(f)} is empty (0-byte).", "WARNING")
                return False
                
    return True

def run_me_analyzer_internal(bios_path, terminal_callback=None):
    """
    Runs ME Analyzer internally and returns metadata.
    """
    from path_utils import get_app_root, get_python_cmd
    mea_script = os.path.join(get_app_root(), "ME Analyzer", "MEA.py")
    if not os.path.exists(mea_script):
        return None
        
    python_exe = get_python_cmd()
    cmd = [python_exe, mea_script, bios_path, "-exit", "-skip"]
    try:
        creationflags = 0x08000000 if os.name == 'nt' else 0
        res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', creationflags=creationflags)
        return parse_mea_output(res.stdout)
    except:
        return None

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
        # Step 2: Get ranked candidates
        candidates = find_fit_candidates(version_string, external_dir, chipset_hint)
        if not candidates:
            print_terminal_log(terminal_callback, f"[ERROR] No Intel FIT found for version {version_string}.", "ERROR")
            return None

    # Step 3: Retry Loop
    for attempt, (score, fit_exe) in enumerate(candidates, 1):
        print_terminal_log(terminal_callback, f"[INFO] Attempt {attempt}: Trying {Path(fit_exe).parent.parent.name} (Score: {score})...")
        
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
                        for cand_name in ["image", Path(temp_bios).stem, Path(bios_path).stem]:
                            cand_p = Path(fit_dir) / cand_name
                            if cand_p.exists() and cand_p.is_dir():
                                fit_decomp = cand_p
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
                
                # Point 2 & 5: Deep Validation
                if validate_decompiled_structure(decomp_target, terminal_callback):
                    print_terminal_log(terminal_callback, f"[SUCCESS] FIT Decompile successful via {Path(fit_exe).name}")
                    return str(decomp_target)
                else:
                    print_terminal_log(terminal_callback, "[WARNING] Validation failed for this tool. Trying next...", "WARNING")
            
        except Exception as e:
            print_terminal_log(terminal_callback, f"[ERROR] Execution failed: {str(e)}", "ERROR")
            continue

    print_terminal_log(terminal_callback, "[ERROR] All available FIT tools failed to decompile this image.", "ERROR")
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
        candidates = find_fit_candidates(version_string, external_dir, chipset_hint)
        if not candidates:
            print_terminal_log(terminal_callback, f"[ERROR] No Intel FIT found for version {version_string}.", "ERROR")
            return False

    for attempt, (score, fit_exe) in enumerate(candidates, 1):
        tool_name = Path(fit_exe).parents[2].name
        print_terminal_log(terminal_callback, f"[INFO] Rebuild Attempt {attempt}: Trying {tool_name} (Score: {score})...")
        
        # Use short path for the executable to avoid issues with spaces and special characters
        fit_exe_safe = get_short_path(os.path.abspath(fit_exe))
        
        fit_workspace = Path(get_app_root()) / "FIT_WORKSPACE"
        if fit_workspace.exists():
            shutil.rmtree(fit_workspace, ignore_errors=True)
        fit_workspace.mkdir(exist_ok=True)
        
        temp_corrupt = fit_workspace / "corrupt.bin"
        shutil.copy2(corrupt_bios_path, temp_corrupt)
        xml_path = fit_workspace / "config.xml"
        is_mfit_tool = fit_exe.lower().endswith("mfit.exe")
        
        # Decompile to get config
        if is_mfit_tool:
            cmd = [fit_exe_safe, "--decompose", temp_corrupt.name, "--saveconfig", xml_path.name.replace(" ", "_")]
        else:
            cmd = [fit_exe_safe, "-f", temp_corrupt.name, "-save", xml_path.name.replace(" ", "_")]
        
        subprocess.run(cmd, cwd=str(fit_workspace), capture_output=True, text=True, encoding='utf-8', errors='replace', creationflags=0x08000000)
        
        if not xml_path.exists():
            for possible in [fit_workspace / "corrupt.xml", fit_workspace / "image.xml"]:
                if possible.exists():
                    shutil.copy2(possible, xml_path)
                    break
        
        if not xml_path.exists():
            continue
            
        decomp_target = fit_workspace / "corrupt"
        if not decomp_target.exists():
            if is_mfit_tool:
                subprocess.run([fit_exe, "--decompose", temp_corrupt.name], cwd=str(fit_workspace), capture_output=True, creationflags=0x08000000)
            else:
                subprocess.run([fit_exe, "-f", xml_path.name, "-b", "-o", "dummy_out.bin"],
                               cwd=str(fit_workspace), capture_output=True, creationflags=0x08000000)
        
        if not decomp_target.exists():
            subdirs = [d for d in fit_workspace.iterdir() if d.is_dir()]
            if subdirs: decomp_target = subdirs[0]
            else: continue

        # Inject clean regions
        for r_type, clean_f in clean_paths_dict.items():
            if not clean_f: continue
            targets = find_partition_files(decomp_target, r_type)
            for t in targets:
                try:
                    if os.path.exists(t): os.chmod(t, 0o666)
                    shutil.copy2(clean_f, t)
                except: pass

        # Patch XML for OEM State
        force_manufacturing_mode(xml_path, state="No")
        
        # Rebuild
        final_out = fit_workspace / "outimage.bin"
        if is_mfit_tool:
            cmd = [fit_exe_safe, "--decompose", temp_corrupt.name, "--loadconfig", xml_path.name, "--build", final_out.name]
        else:
            cmd = [fit_exe_safe, "-f", xml_path.name, "-b", "-o", final_out.name]
            
        res = subprocess.run(cmd, cwd=str(fit_workspace), capture_output=True, text=True, encoding='utf-8', errors='replace', creationflags=0x08000000)
        
        if final_out.exists():
            # Final Integrity Check
            if verify_image_integrity(final_out, terminal_callback):
                # Point 3: DMI Persistence Safety
                try:
                    from dmi_migrator import DMIMigrator
                    print_terminal_log(terminal_callback, "[INFO] Ensuring DMI Persistence...")
                    migrated_path = DMIMigrator.migrate(corrupt_bios_path, str(final_out), terminal_callback=terminal_callback)
                    if migrated_path and os.path.exists(migrated_path):
                        shutil.copy2(migrated_path, output_path)
                    else:
                        shutil.copy2(final_out, output_path)
                except:
                    shutil.copy2(final_out, output_path)
                    
                print_terminal_log(terminal_callback, "[SUCCESS] Full CSME Rebuild Completed!")
                return True
            else:
                print_terminal_log(terminal_callback, "[WARNING] Integrity check failed for this build. Trying next tool...", "WARNING")

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
