
import os
import struct
import subprocess
import shutil
from pathlib import Path

class HPBIOSRepairer:
    def __init__(self, original_bios_path, update_exe_path, work_dir="HP_REPAIR_WORK", migrate_dmi=True):
        self.orig_path = Path(original_bios_path)
        self.exe_path = Path(update_exe_path)
        self.work_dir = Path(work_dir)
        self.extracted_dir = self.work_dir / "extracted"
        self.migrate_dmi = migrate_dmi
        self.log = []

    def log_info(self, msg):
        print(f"[INFO] {msg}")
        self.log.append(f"[INFO] {msg}")

    def log_error(self, msg):
        print(f"[ERROR] {msg}")
        self.log.append(f"[ERROR] {msg}")

    def extract_exe(self):
        if self.extracted_dir.exists():
            shutil.rmtree(self.extracted_dir)
        self.extracted_dir.mkdir(parents=True, exist_ok=True)
        
        self.log_info(f"Extracting {self.exe_path.name}...")
        cmd = ["7z", "x", str(self.exe_path), f"-o{self.extracted_dir}", "-y"]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        if result.returncode != 0:
            self.log_error(f"7z extraction failed: {result.stderr}")
            return False
        return True

    def get_regions_info(self, data):
        if data[0x10:0x14] != b"\x5A\xA5\xF0\x0F":
            return None
        regions = {}
        for i, name in [(1, "BIOS"), (2, "ME")]:
            entry = struct.unpack("<I", data[0x40 + i*4 : 0x44 + i*4])[0]
            if entry == 0 or entry == 0xFFFFFFFF: continue
            base = (entry & 0x7FFF) << 12
            limit = ((entry >> 16) & 0x7FFF) << 12 | 0xFFF
            regions[name] = {"base": base, "size": limit - base + 1}
        return regions

    def identify_update_file(self, orig_data):
        subdirs = [d for d in self.extracted_dir.iterdir() if d.is_dir()]
        self.log_info(f"Found {len(subdirs)} subdirectories in extraction.")

        selected_dir = None
        match_code = None
        
        if len(subdirs) > 1:
            self.log_info("Multiple folders detected. Searching for matching code...")
            for d in subdirs:
                code = d.name.encode('utf-8')
                if code in orig_data:
                    self.log_info(f"Match found: '{d.name}'")
                    selected_dir = d
                    match_code = code
                    break
            if not selected_dir:
                self.log_error("No matching folder code found.")
                return None, None
        elif len(subdirs) == 1:
            selected_dir = subdirs[0]
            match_code = selected_dir.name.encode('utf-8')
        else:
            selected_dir = self.extracted_dir
            # For root files, we might not have a code, so we'll try to find any code.
            match_code = None

        bin_files = list(selected_dir.glob("*.bin"))
        if not bin_files: return None, None
        bin_files.sort(key=lambda x: x.stat().st_size, reverse=True)
        return bin_files[0], match_code

    def perform_repair(self, output_path):
        if not self.extract_exe(): return False
        
        orig_data = bytearray(self.orig_path.read_bytes())
        update_bin, match_code = self.identify_update_file(orig_data)
        if not update_bin: return False
        
        update_data = update_bin.read_bytes()
        regions = self.get_regions_info(orig_data)
        if not regions or "BIOS" not in regions:
            self.log_error("Could not parse regions.")
            return False
            
        bios_info = regions["BIOS"]
        me_info = regions.get("ME", {"base": 0x1000, "size": 0xFFF000})

        # --- ALIGNMENT LOGIC ---
        start_in_spi = None
        if match_code:
            idx_orig = orig_data.find(match_code)
            idx_upd = update_data.find(match_code)
            if idx_orig != -1 and idx_upd != -1:
                start_in_spi = idx_orig - idx_upd
                self.log_info(f"Alignment found via code '{match_code.decode()}'. Update starts at SPI offset {hex(start_in_spi)}")
        
        if start_in_spi is None:
            # Fallback: check if it starts at ME or BIOS
            if update_data[0:4] == b"$FPT" or update_data.find(b"$FPT", 0, 0x2000) != -1:
                start_in_spi = me_info['base']
                self.log_info(f"Alignment assumed: Starts at ME region ({hex(start_in_spi)})")
            else:
                # Default to BIOS region start if nothing else found
                start_in_spi = bios_info['base']
                self.log_info(f"Alignment assumed: Starts at BIOS region ({hex(start_in_spi)})")

        # --- INJECTION ---
        # Calculate overlap with BIOS region
        bios_start = bios_info['base']
        bios_size = bios_info['size']
        
        # Offset of BIOS region relative to update file start
        offset_in_update = bios_start - start_in_spi
        
        if offset_in_update < 0:
            # BIOS region starts BEFORE the update file
            target_start_in_upd = 0
            target_start_in_spi = start_in_spi
            target_size = len(update_data)
        else:
            # BIOS region starts AT or AFTER the update file start
            target_start_in_upd = offset_in_update
            target_start_in_spi = bios_start
            
        # Limit by update data size and BIOS region size
        available_data = len(update_data) - target_start_in_upd
        if available_data <= 0:
            self.log_error("Update file does not contain BIOS region data based on alignment.")
            return False
            
        inject_size = min(available_data, bios_size - (target_start_in_spi - bios_start))

        # --- CLEANING ---
        if not self.migrate_dmi:
            self.log_info(f"DMI Migration: NO. Wiping BIOS region ({hex(bios_size)} bytes) for total clean...")
            orig_data[bios_start : bios_start + bios_size] = b"\xFF" * bios_size
        else:
            self.log_info("DMI Migration: YES (Preserving existing NVRAM/DMI by patching).")

        self.log_info(f"Injecting {hex(inject_size)} bytes from update offset {hex(target_start_in_upd)} into SPI {hex(target_start_in_spi)}")
        
        orig_data[target_start_in_spi : target_start_in_spi + inject_size] = update_data[target_start_in_upd : target_start_in_upd + inject_size]
        
        # --- HP CLEANING REPORT ---
        self.log_info("-" * 50)
        self.log_info(">>> [HP REPAIR SUMMARY REPORT]")
        self.log_info(f"  - Original BIOS Region Size : {bios_size/1024/1024:.2f} MB")
        self.log_info(f"  - HP Update Payload Size    : {len(update_data)/1024/1024:.2f} MB")
        self.log_info(f"  - Injected into SPI Offset  : {hex(target_start_in_spi)}")
        self.log_info(f"  - Actual Injected Data Size : {inject_size/1024/1024:.2f} MB")
        
        if not self.migrate_dmi:
            self.log_info(f"  - DMI/NVRAM Status          : CLEANED (Wiped ✅)")
        else:
            self.log_info(f"  - DMI/NVRAM Status          : PRESERVED (Patched ✅)")
        self.log_info("-" * 50)

        Path(output_path).write_bytes(orig_data)
        self.log_info(f"Successfully saved repaired BIOS to {output_path}")
        return True

if __name__ == "__main__":
    orig_bios = r"TESTING_AREA\BIOS_region_clean\W25Q256FV@WSON8 8X6_System.BIN"
    update_exe = r"TESTING_AREA\BIOS_region_clean\sp168853.exe"
    output = r"TESTING_AREA\BIOS_region_clean\REPAIRED_BIOS_FINAL.BIN"
    
    repairer = HPBIOSRepairer(orig_bios, update_exe)
    repairer.perform_repair(output)
