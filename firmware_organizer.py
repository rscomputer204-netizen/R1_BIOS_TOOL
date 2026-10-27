import os
import shutil
from pathlib import Path

def print_terminal_log(callback, message, level="INFO"):
    if callback:
        callback(f"[{level}] {message}")
    else:
        print(f"[{level}] {message}")

def get_unique_path(target_path):
    """Generates a unique path by adding numeric suffixes."""
    if not target_path.exists():
        return target_path
    
    stem = target_path.stem
    suffix = target_path.suffix
    directory = target_path.parent
    counter = 1
    
    while True:
        new_path = directory / f"{stem}_{counter}{suffix}"
        if not new_path.exists():
            return new_path
        counter += 1

def classify_firmware(file_path):
    """
    Classifies firmware based on signatures or name.
    Returns: 'intel_me', 'csme', or 'other'
    """
    try:
        with open(file_path, "rb") as f:
            # Check first 1MB for signatures
            data = f.read(1024 * 1024)
            
            # Simple ME signature check
            if b"$FPT" in data:
                # Basic distinction: Check for newer CSME markers if possible or just group
                if b"ME11" in data or b"ME12" in data or b"ME14" in data:
                    return "csme"
                return "intel_me"
    except:
        pass
        
    # Default based on name if signature fails
    name = file_path.name.lower()
    if "me" in name and "csme" not in name:
        return "intel_me"
    elif "csme" in name:
        return "csme"
    
    return "other"

def detect_and_organize_local_firmware(base_dir, terminal_callback=None):
    """
    Scans the directory for BIOS/Firmware files and organizes them.
    """
    base_path = Path(base_dir)
    db_path = base_path / "firmware_database"
    
    # Setup folders
    subfolders = ["intel_me", "csme", "other"]
    for sub in subfolders:
        (db_path / sub).mkdir(parents=True, exist_ok=True)
        
    extensions = [".bin", ".rom", ".fd", ".cap"]
    found_files = []
    
    # List files in current directory
    for item in base_path.iterdir():
        if item.is_file() and item.suffix.lower() in extensions:
            if "main.py" not in item.name and "test_parser.py" not in item.name:
                found_files.append(item)
                
    if not found_files:
        print_terminal_log(terminal_callback, "No firmware files detected in working directory.", "WARNING")
        return
        
    for file_path in found_files:
        category = classify_firmware(file_path)
        target_dir = db_path / category
        target_path = target_dir / file_path.name
        
        # Handle duplicates
        final_path = get_unique_path(target_path)
        
        try:
            shutil.move(str(file_path), str(final_path))
            print_terminal_log(terminal_callback, f"File \"{file_path.name}\" moved to \"firmware_database/{category}/\"")
        except Exception as e:
            print_terminal_log(terminal_callback, f"ERROR: Failed to move {file_path.name}: {str(e)}", "ERROR")

def setup_firmware_database(base_dir):
    """Initial check and folder creation."""
    db_path = Path(base_dir) / "firmware_database"
    for sub in ["intel_me", "csme", "other"]:
        (db_path / sub).mkdir(parents=True, exist_ok=True)
