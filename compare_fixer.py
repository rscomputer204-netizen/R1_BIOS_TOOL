import os
import struct
import shutil
from pathlib import Path

class CompareFixer:
    """
    Handles Structural Comparison between BIOS dumps and automatic FV Checksum Fixes.
    """
    
    @staticmethod
    def print_log(callback, message, level="INFO"):
        if callback:
            callback(f"[{level}] {message}")
        else:
            print(f"[{level}] {message}")

    @staticmethod
    def fix_fv_checksums(data_bytearray, terminal_callback=None):
        """
        Scans for '_FVH' signatures and recalculates the 16-bit Checksum of the UEFI Firmware Volume Header.
        """
        count = 0
        offs = -1
        while True:
            offs = data_bytearray.find(b"_FVH", offs + 1)
            if offs == -1:
                break
            
            base = offs - 0x28
            if base < 0 or base + 0x34 > len(data_bytearray):
                continue
                
            header_len = struct.unpack_from("<H", data_bytearray, base + 0x30)[0]
            if header_len < 0x30 or base + header_len > len(data_bytearray) or header_len % 2 != 0:
                continue
                
            # Read current checksum at offset 0x32
            old_chk = struct.unpack_from("<H", data_bytearray, base + 0x32)[0]
            
            # Calculate new: zero out the checksum field logically during sum
            total_sum = 0
            for i in range(0, header_len, 2):
                val = struct.unpack_from("<H", data_bytearray, base + i)[0]
                if i == 0x32:
                    val = 0 # Handle checksum field as zero
                total_sum = (total_sum + val) & 0xFFFF
                
            new_chk = (0x10000 - total_sum) & 0xFFFF
            
            if new_chk != old_chk:
                struct.pack_into("<H", data_bytearray, base + 0x32, new_chk)
                count += 1
                CompareFixer.print_log(terminal_callback, f"Fixed FV Header Checksum at 0x{base:X}: 0x{old_chk:04X} -> 0x{new_chk:04X}")
                
        return count

    @staticmethod
    def run_compare_and_fix(old_bios_path, current_bios_path, terminal_callback=None):
        """
        Compares data structures between the original backup and the current modified BIOS,
        then automatically fixes any FV Header Checksum mismatches in the current BIOS,
        saving the fixed version as _CHECKED.bin.
        """
        from bios_parser import get_bios_metadata # Delay import to avoid circular dependency
        
        CompareFixer.print_log(terminal_callback, "="*50)
        CompareFixer.print_log(terminal_callback, ">>> RUNNING COMPARE & FIX ANALYZER")
        CompareFixer.print_log(terminal_callback, "="*50)
        
        if not os.path.exists(old_bios_path):
            CompareFixer.print_log(terminal_callback, "[ERROR] Old Backup file missing.", "ERROR")
            return None
        if not os.path.exists(current_bios_path):
            CompareFixer.print_log(terminal_callback, "[ERROR] Cleaned/Modified file missing.", "ERROR")
            return None

        CompareFixer.print_log(terminal_callback, "[INFO] Extracting mappings for structural comparison...")
        
        # Suppress massive terminal logs from bios parser by passing None temporarily
        old_meta = get_bios_metadata(old_bios_path, terminal_callback=None, mea_handler=None)
        new_meta = get_bios_metadata(current_bios_path, terminal_callback=None, mea_handler=None)
        
        if not old_meta or not new_meta:
            CompareFixer.print_log(terminal_callback, "[ERROR] Failed to map Flash Descriptor Regions for comparison.", "ERROR")
            return None
            
        mismatch_found = False
        
        # 1. Compare Sizes
        old_sz = old_meta.get("file_size", 0)
        new_sz = new_meta.get("file_size", 0)
        if old_sz == new_sz:
            CompareFixer.print_log(terminal_callback, f"[OK] File Size Match: {old_sz // (1024*1024)} MB")
        else:
            CompareFixer.print_log(terminal_callback, f"[FAIL] File Size Mismatch! OLD: {old_sz} bytes | NEW: {new_sz} bytes", "WARNING")
            mismatch_found = True
            
        # 2. Compare Descriptor Offset
        if old_meta.get("descriptor_offset") != new_meta.get("descriptor_offset"):
            CompareFixer.print_log(terminal_callback, f"[FAIL] Flash Descriptor Signature shifted! This may cause a brick.", "WARNING")
            mismatch_found = True
        else:
            CompareFixer.print_log(terminal_callback, "[OK] Flash Descriptor anchored securely.")

        # 3. Compare Critical Regions
        old_regions = old_meta.get("regions", {})
        new_regions = new_meta.get("regions", {})
        
        for r_name in ["bios", "me_csme", "gbe", "descriptor"]:
            o_reg = old_regions.get(r_name)
            n_reg = new_regions.get(r_name)
            
            if o_reg and n_reg:
                if o_reg["offset"] != n_reg["offset"] or o_reg["size"] != n_reg["size"]:
                    CompareFixer.print_log(terminal_callback, f"[FAIL] Region '{r_name.upper()}' structural mismatch! (OLD Offset: 0x{o_reg['offset']:X}, NEW Offset: 0x{n_reg['offset']:X})", "WARNING")
                    mismatch_found = True
                else:
                    CompareFixer.print_log(terminal_callback, f"[OK] Region '{r_name.upper()}' perfectly aligned.")
            elif o_reg and not n_reg:
                CompareFixer.print_log(terminal_callback, f"[FAIL] Region '{r_name.upper()}' is missing in the NEW file!", "WARNING")
                mismatch_found = True

        if mismatch_found:
            CompareFixer.print_log(terminal_callback, "-"*50)
            CompareFixer.print_log(terminal_callback, "[WARNING] STRUCTURAL MISMATCH CAUGHT BEFORE FLASHING!", "WARNING")
            CompareFixer.print_log(terminal_callback, "[WARNING] Extreme caution advised. This firmware structure is risky to flash.", "WARNING")
            CompareFixer.print_log(terminal_callback, "-"*50)
        else:
            CompareFixer.print_log(terminal_callback, "[SUCCESS] Structural Validation Passed! 100% Region match.")
            
        # 4. FIX FV CHECKSUMS!
        CompareFixer.print_log(terminal_callback, "\n[INFO] Starting Embedded UEFI Firmware Volume (FV) Checksum scan...")
        
        # We need to read the current modified file into a mutable bytearray
        try:
            with open(current_bios_path, "rb") as f:
                data = bytearray(f.read())
                
            fixes_applied = CompareFixer.fix_fv_checksums(data, terminal_callback)
            
            # Save the fixed file with safety net
            original_name = os.path.basename(current_bios_path)
            name_no_ext, ext = os.path.splitext(original_name)
            safe_output_path = os.path.join(os.path.dirname(current_bios_path), f"{name_no_ext}_CHECKED{ext}")
            
            with open(safe_output_path, "wb") as f_out:
                f_out.write(data)
                
            if fixes_applied > 0:
                CompareFixer.print_log(terminal_callback, f"[SUCCESS] Total FV Checksums Auto-Repaired: {fixes_applied}")
            else:
                CompareFixer.print_log(terminal_callback, "[INFO] All FV Checksums are already correct.")
                
            CompareFixer.print_log(terminal_callback, f"[INFO] Checked file securely saved: {os.path.basename(safe_output_path)}")
            
            return safe_output_path
            
        except Exception as e:
            CompareFixer.print_log(terminal_callback, f"[ERROR] FV Checksum Fixer crashed: {str(e)}", "ERROR")
            return None
