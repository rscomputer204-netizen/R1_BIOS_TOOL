"""
R1 BIOS Tool - All-in-One Build Script
=======================================
Usage: python build.py

What this script does:
1. Compiles main.py with all required modules -> dist/R1_BIOS_TOOL/
2. Compiles standalone pyrunner.exe into dist/R1_BIOS_TOOL/
3. Copies external runtime directories (Firmware_Repository, external tools, etc.)

Files INCLUDED in the compiled app:
  - All Python modules imported by main.py (auto by PyInstaller)
  - assets/ folder (logo, icons)
  - translations/ folder (language files)
  - BIOSUtilities/ folder (biosutilities Python library)
  - brands/ and rg_engine/ packages
  - password_unlock_engine and all repair engines

Files NOT included (they are external, placed alongside exe):
  - Firmware_Repository/
  - external/ (UniExtract, 7z, and other extraction tools)
  - ME Analyzer/
  - MCExtractor/
  - BGScriptTool/
  - MCS-Parser/
  - WORKSPACE/
"""

import os
import sys
import stat
import shutil
import subprocess
import time

_app_root = os.path.dirname(os.path.abspath(__file__))

# ─── RESOLVE CORRECT PYTHON + PYINSTALLER EXECUTABLE ────────────────────────
# System Python (Python 3.13) has PyInstaller + PySide6 6.11.2 cleanly installed.
# We do NOT use .venv because it has an outdated/broken PySide6 6.11.0 from another machine.

_SYSTEM_PYTHON = r"C:\Users\R1 LAB\AppData\Local\Programs\Python\Python313\python.exe"

# Prefer the known absolute path; fallback to the running interpreter
if os.path.exists(_SYSTEM_PYTHON):
    _PYTHON_EXE = _SYSTEM_PYTHON
else:
    _PYTHON_EXE = sys.executable

_PYINSTALLER_CMD = [_PYTHON_EXE, "-m", "PyInstaller"]
print(f"[BUILD] Python    : {_PYTHON_EXE}")
print(f"[BUILD] PyInstaller: {_PYTHON_EXE} -m PyInstaller")


# ─── CONFIGURATION ────────────────────────────────────────────────────────────

APP_NAME        = "R1_BIOS_TOOL"
MAIN_SCRIPT     = "main.py"
ICON_PATH       = os.path.join("assets", "icon.ico")   # Optional; skipped if missing

# Folders to bundle inside the compiled app alongside the exe
BUNDLE_DATA_DIRS = [
    ("assets", "assets"),                               # Logo, SVG icons
    ("translations", "translations"),                   # Language JSON files
    ("BIOSUtilities", "BIOSUtilities"),                 # biosutilities root (for path resolution)
    (os.path.join("BIOSUtilities", "biosutilities"),
     "biosutilities"),                                  # biosutilities Python package (critical!)
    ("brands", "brands"),                               # Brand plugins folder
    ("rg_engine", "rg_engine"),                         # BIOS RG Fix engine modules
]

# External folders NOT bundled into the exe but placed next to it in dist/
EXTERNAL_RUNTIME_DIRS = [
    "Firmware_Repository",
    "external",        # Contains UniExtract, 7z, and other extraction tools
    "ME Analyzer",
    "MCExtractor",     # Added for Microcode Audit
    "BGScriptTool",    # Added for BIOS Guard Analysis
    "MCS-Parser",      # Added for additional parsing
    "WORKSPACE",       # User workspace (created at runtime if missing)
    "config",          # Report and application user settings
]

# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _on_rm_error(func, path, exc_info):
    """Error handler for shutil.rmtree: strips read-only flag and retries."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception as e:
        print(f"  [!] Could not remove {path}: {e}")

def force_rmtree(path):
    """Remove a directory tree, clearing read-only flags on all files first.
    Uses both 'attrib -r /s /d' (Windows) and chmod to handle all edge cases."""
    if not os.path.exists(path):
        return
    # Step 1: Use Windows attrib command to strip read-only from all files/dirs
    try:
        subprocess.run(
            ["attrib", "-r", "-h", "-s", f"{path}\\*", "/s", "/d"],
            capture_output=True, timeout=30
        )
    except Exception:
        pass
    # Step 2: Also use Python chmod to handle remaining cases
    for root, dirs, files in os.walk(path):
        for f in files:
            try:
                os.chmod(os.path.join(root, f), stat.S_IWRITE | stat.S_IREAD)
            except Exception:
                pass
        for d in dirs:
            try:
                os.chmod(os.path.join(root, d), stat.S_IWRITE | stat.S_IREAD)
            except Exception:
                pass
    try:
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
    except Exception:
        pass
    # Step 3: rmtree with error handler that strips read-only and retries
    shutil.rmtree(path, onerror=_on_rm_error)
    if os.path.exists(path):
        time.sleep(1.0)
        shutil.rmtree(path, onerror=_on_rm_error)
    if os.path.exists(path):
        time.sleep(1.5)
        shutil.rmtree(path, ignore_errors=True)


def run(cmd: list, cwd=None):
    print(f"\n> Running: {' '.join(str(x) for x in cmd)}\n")
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        print(f"\n[FAIL] Command failed with exit code {result.returncode}")
        print("  If PyInstaller is missing, run:  pip install pyinstaller")
        sys.exit(1)

def find_iscc():
    """Locate Inno Setup Command-Line Compiler (ISCC.exe)."""
    candidates = [
        r"C:\Program Files\Inno Setup 7\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 7\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Users\R1 LAB\AppData\Local\Programs\Inno Setup 7\ISCC.exe",
        r"C:\Users\R1 LAB\AppData\Local\Programs\Inno Setup 6\ISCC.exe",
        shutil.which("ISCC.exe"),
        shutil.which("ISCC"),
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    return None

def banner(text: str):
    print(f"\n{'='*55}")
    print(f"  {text}")
    print(f"{'='*55}")

# ─── PRE-CLEAN: Wipe entire dist/ and build/ folders ─────────────────────────
# Ensures no old/stale files survive between builds.

DIST_DIR = "dist"
BUILD_DIR = "build"

banner("PRE-CLEAN  |  Terminating running instances & wiping old dist/ and build/")
try:
    subprocess.run(["taskkill", "/F", "/IM", f"{APP_NAME}.exe", "/T"], capture_output=True)
    subprocess.run(["taskkill", "/F", "/IM", "pyrunner.exe", "/T"], capture_output=True)
    subprocess.run(["taskkill", "/F", "/IM", "R1 Edtor installer.exe", "/T"], capture_output=True)
    subprocess.run(["taskkill", "/F", "/IM", "ISCC.exe", "/T"], capture_output=True)
    time.sleep(1.5)  # Wait for OS to fully release file locks
    # Strip read-only from the whole dist folder before wipe
    subprocess.run(["attrib", "-r", "-h", "-s", "dist\\*", "/s", "/d"],
                   capture_output=True, cwd=_app_root)
    time.sleep(0.5)
except Exception:
    pass

for clean_dir in [DIST_DIR, BUILD_DIR]:
    if os.path.exists(clean_dir):
        force_rmtree(clean_dir)
        print(f"  [DELETED]  {clean_dir}/")
os.makedirs(DIST_DIR, exist_ok=True)
os.makedirs(BUILD_DIR, exist_ok=True)
print("  [OK] Clean workspace ready. Starting fresh build...")

# ─── STEP 1: COMPILE MAIN APP ─────────────────────────────────────────────────

banner("Step 1/4  |  Compiling Main Application")

main_cmd = _PYINSTALLER_CMD + [
    "--noconfirm",
    "--onedir",
    "--noconsole",
    "--name", APP_NAME,
    # Add biosutilities source + project root to the analysis path
    "--paths", "BIOSUtilities",
    "--paths", _app_root,
]

# ── CRITICAL: Collect ALL of PySide6 and shiboken6 ──
# Without this, libshiboken cannot import PySide6.QtGui in the frozen exe!
main_cmd += [
    "--collect-all", "PySide6",
    "--collect-all", "shiboken6",
]

# Bundle required data directories
for src, dest in BUNDLE_DATA_DIRS:
    if os.path.exists(src):
        main_cmd += ["--add-data", f"{src};{dest}"]
    else:
        print(f"  [!] Skipping '{src}' - folder not found.")

if os.path.exists(ICON_PATH):
    main_cmd += ["--icon", ICON_PATH]

main_cmd.append(MAIN_SCRIPT)

# ── BIOSUTILITIES HIDDEN IMPORTS (critical for advanced_extractor.py) ──
BIOSUTILITIES_HIDDEN_IMPORTS = [
    "biosutilities",
    "biosutilities.common",
    "biosutilities.common.templates",
    "biosutilities.common.checksums",
    "biosutilities.common.compression",
    "biosutilities.common.paths",
    "biosutilities.common.patterns",
    "biosutilities.common.structs",
    "biosutilities.common.system",
    "biosutilities.common.texts",
    "biosutilities.ami_pfat_extract",
    "biosutilities.ami_ucp_extract",
    "biosutilities.apple_efi_id",
    "biosutilities.apple_efi_im4p",
    "biosutilities.apple_efi_pbzx",
    "biosutilities.apple_efi_pkg",
    "biosutilities.award_bios_extract",
    "biosutilities.dell_pfs_extract",
    "biosutilities.fujitsu_sfx_extract",
    "biosutilities.fujitsu_upc_extract",
    "biosutilities.insyde_ifd_extract",
    "biosutilities.panasonic_bios_extract",
    "biosutilities.phoenix_tdk_extract",
    "biosutilities.portwell_efi_extract",
    "biosutilities.toshiba_com_extract",
    "biosutilities.vaio_package_extract",
]

for bio_mod in BIOSUTILITIES_HIDDEN_IMPORTS:
    main_cmd += ["--hidden-import", bio_mod]

# ── RG ENGINE HIDDEN IMPORTS (BIOS RG Fix feature) ──
RG_ENGINE_HIDDEN_IMPORTS = [
    "rg_engine",
    "rg_engine.extractor",
    "rg_engine.replacer",
    "rg_engine.ui",
    "rg_engine.validator",
    # Hardware license guard & security system
    "programmer_guard",
    "license_manager",
    "security_gate",
]

for rg_mod in RG_ENGINE_HIDDEN_IMPORTS:
    main_cmd += ["--hidden-import", rg_mod]

for dmi_mod in ["hp_dmi_extractor", "dell_dmi_extractor", "lenovo_dmi_extractor", "acer_dmi_extractor", "dmi_extractor", "dmi_injector"]:
    main_cmd += ["--hidden-import", dmi_mod]

# ── PASSWORD UNLOCK ENGINE (new modules) ──
for unlock_mod in ["password_unlock_engine", "password_remover_dialog"]:
    main_cmd += ["--hidden-import", unlock_mod]

# ── DYNAMICALLY INCLUDE ALL NEW FEATURES ──
# Recursively find all Python files in the workspace (excluding specific folders and files)
def get_all_modules(root_dir='.'):
    modules = []
    exclude_dirs = {
        'dist', 'build', '__pycache__', 'venv', 'env', '.git', '.vscode',
        'assets', 'translations', 'BIOSUtilities', 'external',
        'Firmware_Repository', 'ME Analyzer', 'ME Analyzer_OLD',
        'ME_Analyzer_LATEST', 'WORKSPACE', 'REPAIRED_BIOS', 'DIAG_WORKSPACE',
        'TESTING_AREA', 'scratch',
    }
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Exclude directories
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs and not d.startswith('.')]
        
        for f in filenames:
            if f.endswith('.py') and f not in ('build.py', 'main.py'):
                if f.startswith('test_') or f.startswith('debug_') or f.endswith('_backup.py'):
                    continue
                if f in ('server_start.py', 'server_fastapi.py'):
                    continue
                
                # Create module notation (e.g., folder.subfolder.module)
                rel_path = os.path.relpath(os.path.join(dirpath, f), root_dir)
                mod_name = rel_path[:-3].replace(os.sep, '.')
                modules.append(mod_name)
    return modules

# Add all dynamically found modules as hidden imports
for mod_name in get_all_modules():
    main_cmd += ["--hidden-import", mod_name]

run(main_cmd)

dist_app_dir = os.path.join("dist", APP_NAME)
if not os.path.exists(dist_app_dir):
    print("[FAIL] Main app was not compiled successfully. Aborting.")
    sys.exit(1)

# --- STEP 2: COMPILE STANDALONE PYTHON RUNNER ---
banner("Step 2/4  |  Compiling Standalone Python Runner (pyrunner.exe)")
pyrunner_cmd = _PYINSTALLER_CMD + [
    "--noconfirm",
    "--onefile",
    "--distpath", dist_app_dir,
    "pyrunner.py",
]
run(pyrunner_cmd)
print(f"  [OK] pyrunner.exe compiled into {dist_app_dir}")

# --- STEP 3: COPY EXTERNAL RUNTIME DIRS ---

banner("Step 3/4  |  Copying External Runtime Directories")

for ext_dir in EXTERNAL_RUNTIME_DIRS:
    src_path = os.path.join(os.getcwd(), ext_dir)
    dest_path = os.path.join(dist_app_dir, ext_dir)
    if os.path.exists(src_path):
        if os.path.isdir(src_path):
            if os.path.exists(dest_path):
                force_rmtree(dest_path)
            # Ignore unnecessary files/folders during copy to reduce bundle size
            ignore_func = shutil.ignore_patterns('__CHECK__', '__pycache__', '.git', '*.pyc', '.vscode')
            shutil.copytree(src_path, dest_path, ignore=ignore_func)
            print(f"  [OK] Copied {ext_dir}/ to {dest_path}/ (Ignored junk files)")
        else:
            shutil.copy2(src_path, dest_path)
            print(f"  [OK] Copied file {ext_dir} to {dest_path}")
    else:
        print(f"  [!] Skipping {ext_dir} - not found locally.")

# Copy essential XML templates to TESTING_AREA in dist
dist_testing_area = os.path.join(dist_app_dir, "TESTING_AREA")
os.makedirs(dist_testing_area, exist_ok=True)
for tmpl in ["adp_template.xml", "tgp_template.xml"]:
    src_tmpl = os.path.join("TESTING_AREA", tmpl)
    if os.path.exists(src_tmpl):
        shutil.copy2(src_tmpl, os.path.join(dist_testing_area, tmpl))
        print(f"  [OK] Copied essential template {tmpl} -> {dist_testing_area}")

# ─── STEP 4: PACKAGE WITH INNO SETUP ──────────────────────────────────────────

banner("Step 4/4  |  Packaging Installer with Inno Setup")

ISS_SCRIPT      = os.path.join(_app_root, "R1 Edtor installer.iss")
INSTALLER_NAME  = "R1 Edtor installer"
INSTALLER_OUT   = os.path.join(_app_root, DIST_DIR, f"{INSTALLER_NAME}.exe")

iscc_path = find_iscc()

if not iscc_path:
    print("  [!] WARNING: Inno Setup (ISCC.exe) not found on this machine.")
    print("      Installer packaging skipped. Install Inno Setup 7 from https://jrsoftware.org/isdl.php")
elif not os.path.isfile(ISS_SCRIPT):
    print(f"  [!] WARNING: Installer script not found: {ISS_SCRIPT}")
    print("      Installer packaging skipped.")
else:
    print(f"  [ISCC] Found : {iscc_path}")
    print(f"  [ISCC] Script: {ISS_SCRIPT}")
    print(f"  [ISCC] Output: {INSTALLER_OUT}")
    print()

    iss_cmd = [
        iscc_path,
        f"--output-dir={os.path.join(_app_root, DIST_DIR)}",
        f"--output-filename={INSTALLER_NAME}",
        "--quiet-progress",
        ISS_SCRIPT,
    ]

    iss_result = subprocess.run(iss_cmd, cwd=_app_root)

    if iss_result.returncode == 0:
        size_mb = 0
        if os.path.isfile(INSTALLER_OUT):
            size_mb = os.path.getsize(INSTALLER_OUT) / (1024 * 1024)
        print(f"\n  [OK] Installer created successfully!")
        print(f"  [OK] Location : dist\\{INSTALLER_NAME}.exe  ({size_mb:.1f} MB)")
    else:
        print(f"\n  [FAIL] Inno Setup packaging failed with exit code {iss_result.returncode}.")
        print("         Check the .iss script or re-run 'py build.py' after fixing the issue.")

# ─── DONE ─────────────────────────────────────────────────────────────────────

banner("ALL DONE!")
print(f"""
  Step 1/4  ✅  Main Application compiled
  Step 2/4  ✅  pyrunner.exe compiled
  Step 3/4  ✅  External runtime directories copied
  Step 4/4  {'✅  Installer created → dist\\' + INSTALLER_NAME + '.exe' if iscc_path else '⚠️  Inno Setup not found — installer skipped'}

  > Compiled app  : dist/{APP_NAME}/
  > EXE installer : dist/{INSTALLER_NAME}.exe
  > Run the app   : dist/{APP_NAME}/{APP_NAME}.exe
""")
