import os
import time
from datetime import datetime
from PySide6.QtWidgets import QApplication

def apply_firmware_patch(bios_file, offset, clean_firmware_path, terminal_callback, fw_name="ME"):
    """
    Generic function to patch any BIOS region with clean firmware.
    """
    try:
        if not os.path.exists(clean_firmware_path):
            terminal_callback(f"[ERROR] Clean firmware not found: {clean_firmware_path}")
            return False

        with open(clean_firmware_path, "rb") as f:
            clean_data = f.read()

        total_size = len(clean_data)
        
        with open(bios_file, "r+b") as f:
            f.seek(offset)
            
            # Apply patch with progress updates
            chunk_size = int(total_size // 4) if total_size > 0 else 0
            
            for i in range(4):
                time.sleep(0.1) # Faster simulation
                
                start = int(i * chunk_size)
                end = int(total_size) if i == 3 else int((i + 1) * chunk_size)
                
                f.write(clean_data[start:end])
                
                progress = (i + 1) * 25
                terminal_callback(f"[INFO] Patching {fw_name} region… {progress}%")
                QApplication.processEvents()
        
        # Verify
        with open(bios_file, "rb") as f:
            f.seek(offset)
            written_data = f.read(total_size)
            
        if written_data == clean_data:
            terminal_callback(f"[SUCCESS] {fw_name} region patched successfully")
            return True
        else:
            terminal_callback(f"[ERROR] {fw_name} patch verification failed")
            return False
            
    except Exception as e:
        terminal_callback(f"[ERROR] Patching {fw_name} failed: {str(e)}")
        return False
