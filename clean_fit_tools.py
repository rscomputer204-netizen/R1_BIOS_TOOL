import os
import sys
import shutil
from pathlib import Path

# Genuine subdirectories present in original Intel System Tools
GENUINE_SUBDIRS = {
    'fixed address programming tool',
    'flash programming tool',
    'fwupdate',
    'iamtnvm',
    'meinfo',
    'memanuf',
    'menvm',
    'itpmdiag',
    'fstdos',
    'flexible sku update tool',
    'configwizard',
    'clock commander tool',
    'iusmanuftool',
    'updparam',
    'usbfile',
    'manifest extension utility',
    'txeinfo',
    'txemanuf',
    'nandutil',
    'desktop & notebook',
    'linux64',
    'build'
}

# Genuine XML templates distributed with Intel FIT / FITC tools
GENUINE_XMLS = {
    'newfiletmpl.xml',
    'ftooltmplc.xml',
    'fitctmpl.xml',
    'pch_4m_newfiletmpl.xml',
    'default.xml',
    'bxt_emmc_8mb_bxtp.xml',
    'bxt_spi_8mb_bxtp.xml'
}

def resolve_tools_dir(base_dir=None):
    """
    Finds the valid FLASH System Tools directory across runtime and dev environments.
    """
    if base_dir and os.path.isdir(base_dir):
        return Path(base_dir)

    candidates = [
        Path(r"d:\BIOS_-TOOL\external\FLASH System Tools"),
        Path(r"C:\Program Files\R1 BIOS TOOL\external\FLASH System Tools"),
        Path(__file__).resolve().parent / "external" / "FLASH System Tools",
        Path(__file__).resolve().parent.parent / "external" / "FLASH System Tools"
    ]
    for cand in candidates:
        if cand.is_dir():
            return cand
    return None

def clean_specific_tool_dir(tool_dir_path):
    """
    Cleans junk folders, temporary bins, logs, maps, and decompiled XMLs
    from a specific Intel FIT tool directory.
    """
    tool_dir = Path(tool_dir_path)
    if not tool_dir.is_dir():
        return {"deleted_files": 0, "deleted_dirs": 0, "freed_bytes": 0}

    deleted_files = 0
    deleted_dirs = 0
    freed_bytes = 0

    try:
        for item in list(tool_dir.iterdir()):
            name_lower = item.name.lower()
            if item.is_dir():
                if name_lower == 'build':
                    for b_item in list(item.iterdir()):
                        try:
                            if b_item.is_file() or b_item.is_symlink():
                                freed_bytes += b_item.stat().st_size
                                b_item.unlink(missing_ok=True)
                                deleted_files += 1
                            elif b_item.is_dir():
                                shutil.rmtree(b_item, ignore_errors=True)
                                deleted_dirs += 1
                        except Exception:
                            pass
                elif name_lower not in GENUINE_SUBDIRS:
                    # Residual decompile directory
                    try:
                        shutil.rmtree(item, ignore_errors=True)
                        deleted_dirs += 1
                    except Exception:
                        pass
            elif item.is_file():
                is_junk = False
                if name_lower.endswith('.log') and not name_lower.endswith('changelog.txt'):
                    is_junk = True
                elif name_lower.endswith('.map'):
                    is_junk = True
                elif name_lower.endswith('.xml') and name_lower not in GENUINE_XMLS:
                    is_junk = True
                elif name_lower.endswith('.bin') and name_lower != 'vsccommn.bin':
                    is_junk = True
                elif name_lower.endswith(('.bak', '.old', '.tmp')):
                    is_junk = True

                if is_junk:
                    try:
                        freed_bytes += item.stat().st_size
                        item.unlink(missing_ok=True)
                        deleted_files += 1
                    except Exception:
                        pass
    except Exception:
        pass

    return {
        "deleted_files": deleted_files,
        "deleted_dirs": deleted_dirs,
        "freed_bytes": freed_bytes
    }

def clean_all_fit_tools(tools_dir=None):
    """
    Scans all FIT tool directories and purges all decompile leftovers,
    junk XMLs, temporary bins, and logs across all packages in milliseconds.
    """
    target_dir = resolve_tools_dir(tools_dir)
    if not target_dir or not target_dir.is_dir():
        return {"deleted_files": 0, "deleted_dirs": 0, "freed_bytes": 0}

    total_files = 0
    total_dirs = 0
    total_bytes = 0

    try:
        for tool_folder in target_dir.iterdir():
            if tool_folder.is_dir():
                res = clean_specific_tool_dir(tool_folder)
                total_files += res["deleted_files"]
                total_dirs += res["deleted_dirs"]
                total_bytes += res["freed_bytes"]
    except Exception:
        pass

    return {
        "deleted_files": total_files,
        "deleted_dirs": total_dirs,
        "freed_bytes": total_bytes
    }

if __name__ == "__main__":
    print("[INFO] Scanning and cleaning FLASH System Tools repository...")
    report = clean_all_fit_tools()
    mb = report['freed_bytes'] / (1024 * 1024)
    print(f"[SUCCESS] Cleanup Finished: {report['deleted_files']} files removed, {report['deleted_dirs']} junk folders purged, {mb:.2f} MB freed.")
