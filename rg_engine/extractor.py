import os
import subprocess
import shutil
import time

# Only BIOS firmware-related file formats will be shown to the user.
# All other formats (txt, exe, dll, ini, log, etc.) are ignored.
BIOS_EXTENSIONS = {
    ".bin", ".fd", ".rom", ".cap", ".img",
    ".bio", ".wph", ".efi", ".hdr", ".fv",
    ".bios", ".bkp", ".flash",
    ".fl1", ".fl2", ".fl3"
}

import stat


def robust_rmtree(path):
    """Safely and thoroughly remove directory tree on Windows handling permissions and long paths."""
    if not os.path.exists(path):
        return
    p_abs = os.path.abspath(path)
    if os.name == 'nt' and not p_abs.startswith('\\\\?\\'):
        p_abs = '\\\\?\\' + p_abs

    def on_err(func, p, exc_info):
        try:
            os.chmod(p, stat.S_IWRITE)
            func(p)
        except Exception:
            pass

    try:
        shutil.rmtree(p_abs, onerror=on_err)
    except Exception:
        try:
            subprocess.run(f'cmd /c rd /s /q "{path}"', shell=True, capture_output=True)
        except Exception:
            pass


def extract_bios_package(exe_path, log_callback=print):
    if not os.path.exists(exe_path):
        raise FileNotFoundError(f"Source file not found: {exe_path}")

    base_dir = os.path.dirname(exe_path)
    base_name = os.path.splitext(os.path.basename(exe_path))[0]
    dest_dir = os.path.join(base_dir, f"{base_name}_Extracted")

    if os.path.exists(dest_dir):
        robust_rmtree(dest_dir)

    os.makedirs(dest_dir, exist_ok=True)

    log_callback(f"Extracting Package to: {dest_dir}")
    
    try:
        from R1_Universal_Extractor.r1_extractor_core import R1ExtractorCore
        result = R1ExtractorCore.extract(exe_path, dest_dir, logger=log_callback)
        if result.get("success"):
            log_callback("Extraction Complete.")
        else:
            log_callback("[WARNING] Extraction completed with warnings.")
    except Exception as e:
        log_callback(f"[ERROR] Extraction failed: {e}")
        raise

    return dest_dir

def safe_path(p: str) -> str:
    """Returns extended-length path on Windows to avoid MAX_PATH (260) limitations."""
    if not p:
        return p
    p_abs = os.path.abspath(p)
    if os.name == 'nt' and not p_abs.startswith('\\\\?\\'):
        return '\\\\?\\' + p_abs
    return p_abs


def list_extracted_files(dest_dir, log_callback=print):
    """
    Recursively scans dest_dir and returns ONLY .bin firmware files from official update.
    Filters out any non-binary files (txt, exe, dll, ini, log, xml, etc.).
    Uses safe extended-length paths on Windows.
    """
    bin_files = []
    fallback_files = []
    scan_dir = safe_path(dest_dir)

    for root, dirs, files in os.walk(scan_dir):
        for f in files:
            full_path = os.path.join(root, f)
            ext = os.path.splitext(f)[1].lower()
            if ext == ".bin":
                bin_files.append(full_path)
            elif ext in (".rom", ".fd", ".cap"):
                fallback_files.append(full_path)

    selected_files = bin_files if bin_files else fallback_files

    if not selected_files:
        log_callback("[WARNING] No .bin firmware files found in extracted package.")
    else:
        log_callback(f"[INFO] Filtered {len(selected_files)} .bin firmware file(s) from extracted package.")

    return selected_files
