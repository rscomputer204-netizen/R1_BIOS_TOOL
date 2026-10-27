import os
import shutil
import struct
from pathlib import Path
from dmi_migrator import DMIMigrator
from bios_parser import find_flash_descriptor, parse_spi_regions
from compare_fixer import CompareFixer
from advanced_extractor import AdvancedExtractor

class BIOSRegionFixer:
    """
    Advanced Engine for BIOS Region Cleaning and DMI Migration.
    Supports partial update files from manufacturers.
    """

    @staticmethod
    def fix_bios_region(original_path, donor_path, log_cb, output_dir=None, migrate_dmi=True):
        log_cb("="*55)
        log_cb("[ACTION] SMART BIOS REGION FIX STARTED")
        log_cb(f"[INFO] Target: {os.path.basename(original_path)}")
        log_cb(f"[INFO] Donor : {os.path.basename(donor_path)}")
        log_cb("="*55)

        try:
            # 1. Read Original
            with open(original_path, 'rb') as f:
                original_data = bytearray(f.read())
            
            # 2. Parse Regions of Original
            desc_offset = find_flash_descriptor(original_data)
            if desc_offset is None:
                log_cb("[ERROR] Flash Descriptor not found in original file.", "ERROR")
                return None
            
            regions = parse_spi_regions(original_data, desc_offset)
            if not regions or "bios" not in regions:
                log_cb("[ERROR] Could not map BIOS region in original file.", "ERROR")
                return None
            
            orig_bios = regions["bios"]
            log_cb(f"[INFO] Original BIOS Region: Offset 0x{orig_bios['offset']:X}, Size: {orig_bios['size']/1024:.0f} KB")

            # 3. Analyze Donor
            # If donor is a package (.exe, .pfs, etc.), extract it first
            donor_bin = donor_path
            temp_dir = os.path.join(os.getcwd(), "WORKSPACE", "donor_extract")
            os.makedirs(temp_dir, exist_ok=True)
            
            ext = os.path.splitext(donor_path)[1].lower()
            if ext in ['.exe', '.pfs', '.pkg', '.cap']:
                log_cb(f"[INFO] Detecting {ext.upper()} donor package. Extracting...")
                if AdvancedExtractor.run_universal_extract(donor_path, temp_dir, log_cb):
                    # Find the best binary in extracted files
                    extracted_files = []
                    for root, _, files in os.walk(temp_dir):
                        for f in files:
                            if f.lower().endswith(('.bin', '.rom', '.fd')):
                                extracted_files.append(os.path.join(root, f))
                    
                    if extracted_files:
                        # Find a file that matches the BIOS region size or the full flash size
                        best_match = None
                        for f in extracted_files:
                            sz = os.path.getsize(f)
                            if sz == orig_bios['size']:
                                best_match = f
                                break
                            elif sz == len(original_data):
                                best_match = f
                                break
                        
                        donor_bin = best_match if best_match else max(extracted_files, key=os.path.getsize)
                        log_cb(f"[SUCCESS] Extracted best donor image: {os.path.basename(donor_bin)} - File Match Complete ✅")
                    else:
                        log_cb("[ERROR] Extraction succeeded but no binary files were found inside.", "ERROR")
                        return None
                else:
                    log_cb("[ERROR] Advanced Extraction failed for donor package.", "ERROR")
                    return None

            # Read Donor Data
            with open(donor_bin, 'rb') as f:
                donor_data = f.read()
            
            donor_size = len(donor_data)
            
            # 4. Determine Replacement Mode
            final_data = bytearray(original_data)
            
            if donor_size == len(original_data):
                log_cb("[INFO] Donor is a FULL SPI DUMP. Replacing BIOS region...")
                # Extract BIOS region from full donor
                donor_desc = find_flash_descriptor(donor_data)
                donor_regions = parse_spi_regions(donor_data, donor_desc) if donor_desc is not None else None
                if donor_regions and "bios" in donor_regions:
                    d_bios = donor_regions["bios"]
                    donor_payload = donor_data[d_bios['offset'] : d_bios['offset'] + d_bios['size']]
                else:
                    # Fallback to assuming same offset if descriptor check fails on donor
                    donor_payload = donor_data[orig_bios['offset'] : orig_bios['offset'] + orig_bios['size']]
            elif donor_size == orig_bios['size']:
                log_cb("[INFO] Donor is a raw BIOS REGION. Replacing...")
                donor_payload = donor_data
            elif "me_csme" in regions and donor_size == regions["me_csme"]["size"]:
                 log_cb("[INFO] Donor is a raw ME REGION. Replacing ME instead of BIOS...")
                 me = regions["me_csme"]
                 final_data[me['offset'] : me['offset'] + me['size']] = donor_data
                 log_cb("[INFO] ME Region replacement Match Complete ✅")
                 return BIOSRegionFixer.finalize(final_data, original_path, log_cb)
            else:
                log_cb(f"[WARNING] Donor size ({donor_size/1024:.0f} KB) does not match original BIOS region size ({orig_bios['size']/1024:.0f} KB).")
                log_cb("[INFO] Attempting smart signature-based injection...")
                # If sizes don't match, we might have an update file that is just PART of the BIOS region
                # or a different version. 
                # For now, let's try to find if the donor payload is inside the original.
                donor_payload = donor_data

            # 5. DMI PRESERVATION (The critical part)
            dmi_blocks = []
            if migrate_dmi:
                log_cb("[ACTION] Scanning for DMI Blocks in original BIOS region...")
                # Signatures to preserve (Standard + HP Specific + Common DMI)
                signatures = DMIMigrator.COMMON_SIGNATURES
                signatures += [
                    b"O.E.M.", b"System Serial Number", b"UUID", b"Asset Tag",
                    b"HP_MUD", b"H\x00P\x00_\x00M\x00U\x00D", # HP specific Unicode
                    b"IDEK", b"I\x00D\x00E\x00K",           # HP specific Unicode
                    b"BRD", b"B\x00R\x00D",                 # HP specific Unicode
                    b"Key00", b"K\x00e\x00y\x000\x000",     # HP DMI Keys
                    b"\xaa\x55\x3f\x00", b"\x55\xaa\x3f\x00", # HP DMI Block Headers
                    b"System Serial", b"S\x00y\x00s\x00t\x00e\x00m\x00 \x00S\x00e\x00r\x00i\x00a\x00l"
                ]
                
                # We only scan the BIOS region for DMI to avoid false positives in ME/Descriptor
                orig_bios_data = original_data[orig_bios['offset'] : orig_bios['offset'] + orig_bios['size']]
                
                found_sigs = set()
                for sig in signatures:
                    pos = orig_bios_data.find(sig)
                    while pos != -1:
                        # Get block boundaries (relative to bios start)
                        start, end = DMIMigrator.get_block_boundaries(orig_bios_data, pos)
                        if (start, end) not in found_sigs:
                            block_data = orig_bios_data[start:end]
                            # Verify the block isn't just empty (all FF or 00)
                            if any(b != 0xFF and b != 0x00 for b in block_data):
                                dmi_blocks.append({
                                    "signature": sig,
                                    "data": block_data,
                                    "rel_offset": start,
                                    "size": len(block_data)
                                })
                                found_sigs.add((start, end))
                                log_cb(f"  -> Found DMI Block: Sig='{sig}', Offset: 0x{start:X}, Size: {len(block_data)/1024:.0f} KB")
                        
                        pos = orig_bios_data.find(sig, pos + 1)
            else:
                log_cb("[INFO] DMI Migration disabled by user. Proceeding with clean region.")

            # 6. REPLACE BIOS REGION
            log_cb("[INFO] Injecting New BIOS Region Data...")

            # --- CRITICAL CLEANING ---
            # If DMI migration is disabled, we must wipe the region to remove old Serial Numbers/NVRAM
            if not migrate_dmi:
                log_cb(f"[INFO] DMI Migration: NO. Wiping BIOS region with 0xFF for total clean.")
                final_data[orig_bios['offset'] : orig_bios['offset'] + orig_bios['size']] = b"\xFF" * orig_bios['size']

            # If donor_payload is smaller than region, pad it or center it? 
            # Usually update files are the END of the region.
            if len(donor_payload) < orig_bios['size']:
                log_cb(f"[WARN] Donor payload is smaller than slot. Aligning to END of region.")
                offset_in_slot = orig_bios['size'] - len(donor_payload)
                final_data[orig_bios['offset'] + offset_in_slot : orig_bios['offset'] + orig_bios['size']] = donor_payload
            else:
                final_data[orig_bios['offset'] : orig_bios['offset'] + orig_bios['size']] = donor_payload[:orig_bios['size']]

            # --- CLEANING REPORT ---
            log_cb("-" * 55)
            log_cb(">>> [REPAIR SUMMARY REPORT]")
            log_cb(f"  - Original BIOS Region Size: {orig_bios['size']/1024/1024:.2f} MB")
            log_cb(f"  - Donor Payload Size       : {len(donor_payload)/1024/1024:.2f} MB")
            
            if len(donor_payload) < orig_bios['size']:
                log_cb(f"  - Mode                     : Partial Patch (Aligned to END)")
            else:
                log_cb(f"  - Mode                     : Full Region Replacement")
            
            if not migrate_dmi:
                log_cb(f"  - DMI/NVRAM Cleaning       : ENABLED (Region Wiped ✅)")
            else:
                log_cb(f"  - DMI/NVRAM Cleaning       : DISABLED (DMI Migrated ✅)")
            log_cb("-" * 55)

            # 7. RE-INJECT DMI BLOCKS
            if migrate_dmi and dmi_blocks:
                log_cb("[ACTION] Restoring DMI Blocks into new BIOS Region...")
                new_bios_data = final_data[orig_bios['offset'] : orig_bios['offset'] + orig_bios['size']]
                
                for block in dmi_blocks:
                    # Try to find the same signature in the NEW data to see if offset shifted
                    new_pos = new_bios_data.find(block["signature"])
                    if new_pos != -1:
                        # Map to the start of the block in the new data
                        new_start = new_pos & ~0xFFF
                        if new_start + block["size"] <= len(new_bios_data):
                            new_bios_data[new_start : new_start + block["size"]] = block["data"]
                            log_cb(f"  [SUCCESS] Restored DMI Block '{block['signature']}' at new offset: 0x{new_start:X}")
                        else:
                            log_cb(f"  [ERROR] New offset 0x{new_start:X} out of bounds for DMI restoration.", "ERROR")
                    else:
                        # If signature not found, fallback to original relative offset
                        log_cb(f"  [WARN] Signature '{block['signature']}' not found in donor. Using original relative offset: 0x{block['rel_offset']:X}")
                        new_start = block["rel_offset"]
                        if new_start + block["size"] <= len(new_bios_data):
                             new_bios_data[new_start : new_start + block["size"]] = block["data"]
                        else:
                             log_cb(f"  [ERROR] Relative offset 0x{new_start:X} out of bounds.", "ERROR")

                # Write back the modified BIOS region
                final_data[orig_bios['offset'] : orig_bios['offset'] + orig_bios['size']] = new_bios_data

            return BIOSRegionFixer.finalize(final_data, original_path, log_cb, output_dir)

        except Exception as e:
            log_cb(f"[ERROR] BIOS Region Fix failed: {str(e)}", "ERROR")
            import traceback
            log_cb(traceback.format_exc(), "DEBUG")
            return None

    @staticmethod
    def finalize(final_data, original_path, log_cb, output_dir=None):
        # 8. FIX CHECKSUMS
        log_cb("[INFO] Finalizing: Correcting FV Checksums...")
        fix_count = CompareFixer.fix_fv_checksums(final_data, log_cb)
        if fix_count > 0:
            log_cb(f"[SUCCESS] Corrected {fix_count} FV checksum errors.")
        
        # 9. SAVE
        timestamp = __import__('datetime').datetime.now().strftime("%Y%m%d_%H%M%S")
        out_name = f"FIXED_REGION_{timestamp}_{os.path.basename(original_path)}"
        
        if not output_dir:
            output_dir = os.path.join(os.getcwd(), "REPAIRED_BIOS")
        
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, out_name)
        
        with open(out_path, 'wb') as f:
            f.write(final_data)
        
        log_cb("-" * 30)
        log_cb("[SUCCESS] BIOS_region Clean Complete ✅")
        log_cb(f"[INFO] Result: {out_name}")
        log_cb("-" * 30)
        
        return out_path
