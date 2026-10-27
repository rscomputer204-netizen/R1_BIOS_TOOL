import os
import shutil
import time

def replace_bios_region(original_bios_path, validated_data, region_offset, target_size, log_callback=print):
    if not os.path.exists(original_bios_path):
        raise FileNotFoundError("Original BIOS file not found.")

    log_callback("Creating Backup...")
    backup_path = original_bios_path + f"_{int(time.time())}_backup.bin"
    shutil.copy2(original_bios_path, backup_path)
    log_callback(f"Backup created: {os.path.basename(backup_path)}")

    log_callback("Replacing BIOS Region...")
    with open(original_bios_path, "r+b") as f:
        f.seek(region_offset)
        f.write(validated_data)

    log_callback("Saving...")
    log_callback("Operation Completed Successfully.")
    
    return {
        "status": "Success",
        "backup_path": backup_path
    }
