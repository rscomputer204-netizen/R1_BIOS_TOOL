import os
import sys
import shutil
import json
import time
import subprocess
import logging
import ctypes
from datetime import datetime

# --- CONFIGURATION ---
LOG_FILE = "updater.log"
UPDATE_CACHE_DIR = "update_cache"
BACKUP_DIR_BASE = "backup"
MANIFEST_FILE = "manifest.json"
PAYLOAD_DIR = "payload"
VERSION_FILE = "version.txt"
EXE_CANDIDATES = ["R1_BIOS_TOOL.exe", "main.exe", "R1_BIOS_EDITOR.exe"]

# Configure Logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def log(msg, level="info"):
    print(msg)
    if level == "info":
        logging.info(msg)
    elif level == "error":
        logging.error(msg)
    elif level == "warning":
        logging.warning(msg)

def wait_for_process_exit(pid):
    """Waits for the specified PID to exit before attempting to overwrite files."""
    if not pid:
        return
    log(f"Waiting for main process (PID: {pid}) to exit...")
    try:
        kernel32 = ctypes.windll.kernel32
        SYNCHRONIZE = 0x00100000
        process = kernel32.OpenProcess(SYNCHRONIZE, False, int(pid))
        if process:
            # Wait up to 15 seconds for process termination
            kernel32.WaitForSingleObject(process, 15000)
            kernel32.CloseHandle(process)
            log("Main process exited cleanly.")
        else:
            log("Process not found or already exited.")
    except Exception as e:
        log(f"Warning while waiting on PID {pid}: {e}", "warning")
        time.sleep(2)

def load_manifest(cache_path):
    manifest_path = os.path.join(cache_path, MANIFEST_FILE)
    if not os.path.exists(manifest_path):
        raise FileNotFoundError("Manifest file missing in update cache.")
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        raise ValueError("Invalid manifest JSON.")

def create_backup(manifest, root_dir):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(root_dir, BACKUP_DIR_BASE, timestamp)
    os.makedirs(backup_path, exist_ok=True)
    
    log(f"Creating backup at {backup_path}...")
    backup_map = []
    
    files_to_update = list(manifest.get("files", []))
    if VERSION_FILE not in files_to_update:
        files_to_update.append(VERSION_FILE)
    
    for rel_path in files_to_update:
        if ".." in rel_path or rel_path.startswith("/") or rel_path.startswith("\\"):
            continue
        src = os.path.join(root_dir, rel_path)
        dst = os.path.join(backup_path, rel_path)
        if os.path.exists(src):
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
            backup_map.append((src, dst))
            
    with open(os.path.join(backup_path, "backup_map.json"), "w", encoding='utf-8') as f:
        json.dump(backup_map, f)
        
    return timestamp

def perform_update(manifest, cache_path, root_dir):
    payload_path = os.path.join(cache_path, PAYLOAD_DIR)
    if not os.path.exists(payload_path):
        raise FileNotFoundError("Payload directory missing in update cache.")
        
    log("Applying updates to application root...")
    files = manifest.get("files", [])
    
    for rel_path in files:
        src = os.path.join(payload_path, rel_path)
        dst = os.path.join(root_dir, rel_path)
        if not os.path.exists(src):
            log(f"Warning: Source file missing in payload: {rel_path}", "warning")
            continue
        if os.path.isdir(src):
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
        log(f"Updated: {rel_path}")

    # Copy new version file
    ver_src = os.path.join(cache_path, VERSION_FILE)
    if not os.path.exists(ver_src):
        ver_src = os.path.join(payload_path, VERSION_FILE)
    ver_dst = os.path.join(root_dir, VERSION_FILE)
    if os.path.exists(ver_src):
        shutil.copy2(ver_src, ver_dst)
        log("Updated version.txt")

def rollback(root_dir, backup_timestamp):
    log(f"CRITICAL: Rolling back to backup {backup_timestamp}...")
    backup_path = os.path.join(root_dir, BACKUP_DIR_BASE, str(backup_timestamp))
    if not os.path.exists(backup_path):
        log("Rollback failed: Backup directory not found!", "error")
        return

    for root, dirs, files in os.walk(backup_path):
        for file in files:
            full_backup_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_backup_path, backup_path)
            if rel_path == "backup_map.json":
                continue
            target_path = os.path.join(root_dir, rel_path)
            try:
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                shutil.copy2(full_backup_path, target_path)
                log(f"Restored: {rel_path}")
            except Exception as e:
                log(f"Failed to restore {rel_path}: {e}", "error")

def relaunch_app(base_dir):
    """Relaunches the main application, either as standalone EXE or Python script."""
    # 1. Check for standalone EXE
    for exe_name in EXE_CANDIDATES:
        exe_path = os.path.join(base_dir, exe_name)
        if os.path.exists(exe_path):
            log(f"Relaunching executable: {exe_name}")
            subprocess.Popen([exe_path], cwd=base_dir)
            return

    # 2. Check for python main.py
    main_py = os.path.join(base_dir, "main.py")
    if os.path.exists(main_py):
        log(f"Relaunching python script: {main_py}")
        subprocess.Popen([sys.executable, main_py], cwd=base_dir)
        return

    log("CRITICAL: Neither executable nor main.py found for relaunch!", "error")

def main():
    pid = sys.argv[1] if len(sys.argv) > 1 else None
    
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Wait for the main app to close and release file locks
    wait_for_process_exit(pid)
    time.sleep(1)

    cache_path = os.path.join(base_dir, UPDATE_CACHE_DIR)
    if not os.path.exists(cache_path):
        log("Update cache not found. Nothing to do.", "error")
        relaunch_app(base_dir)
        sys.exit(1)

    backup_id = None
    try:
        manifest = load_manifest(cache_path)
        ver_str = manifest.get('version', 'unknown')
        log(f"Starting update to version {ver_str}...")

        backup_id = create_backup(manifest, base_dir)
        perform_update(manifest, cache_path, base_dir)
        log("Update applied successfully!")

        try:
            shutil.rmtree(cache_path, ignore_errors=True)
        except Exception as e:
            log(f"Warning: Could not remove cache: {e}", "warning")

    except Exception as e:
        log(f"UPDATE FAILED: {e}", "error")
        import traceback
        log(traceback.format_exc(), "error")
        if backup_id:
            rollback(base_dir, backup_id)
        try:
            ctypes.windll.user32.MessageBoxW(
                0,
                f"Update Failed!\n\nError: {e}\n\nThe application has been restored to the previous version.",
                "R1 BIOS Tool - Update Error",
                0x10
            )
        except Exception:
            pass

    # Relaunch the application
    relaunch_app(base_dir)

if __name__ == "__main__":
    main()
