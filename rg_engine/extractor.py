import os
import subprocess
import shutil
import time

# Only BIOS firmware-related file formats will be shown to the user.
# All other formats (txt, exe, dll, ini, log, etc.) are ignored.
BIOS_EXTENSIONS = {
    ".bin", ".fd", ".rom", ".cap", ".img",
    ".bio", ".wph", ".efi", ".hdr", ".fv",
    ".bios", ".bkp", ".flash"
}

def extract_bios_package(exe_path, log_callback=print):
    if not os.path.exists(exe_path):
        raise FileNotFoundError(f"Source file not found: {exe_path}")

    base_dir = os.path.dirname(exe_path)
    base_name = os.path.splitext(os.path.basename(exe_path))[0]
    dest_dir = os.path.join(base_dir, f"{base_name}_Extracted")

    if os.path.exists(dest_dir):
        try:
            shutil.rmtree(dest_dir)
        except Exception:
            dest_dir = f"{dest_dir}_{int(time.time())}"

    os.makedirs(dest_dir, exist_ok=True)

    from path_utils import get_app_root
    ue_path = os.path.join(get_app_root(), "external", "UniExtract", "UniExtract.exe")

    if not os.path.exists(ue_path):
        raise FileNotFoundError("Universal Extractor not bundled in external/UniExtract/")

    log_callback(f"Extracting Package to: {dest_dir}")
    
    try:
        subprocess.run([ue_path, exe_path, dest_dir], check=False)
        log_callback("Extraction Complete.")
    except Exception as e:
        log_callback(f"[ERROR] Extraction failed: {e}")
        raise

    return dest_dir

def list_extracted_files(dest_dir, log_callback=print):
    """
    Recursively scans dest_dir and returns ONLY files with BIOS-relevant extensions.
    Filters out garbage files (txt, exe, dll, ini, log, xml, etc.).
    """
    all_files = []
    for root, dirs, files in os.walk(dest_dir):
        for f in files:
            full_path = os.path.join(root, f)
            ext = os.path.splitext(f)[1].lower()
            if ext in BIOS_EXTENSIONS:
                all_files.append(full_path)
    
    if not all_files:
        log_callback("[WARNING] No BIOS firmware files found in extracted package.")
        log_callback(f"[INFO] Expected extensions: {', '.join(sorted(BIOS_EXTENSIONS))}")
    else:
        log_callback(f"[INFO] Found {len(all_files)} BIOS candidate file(s).")
    
    return all_files
