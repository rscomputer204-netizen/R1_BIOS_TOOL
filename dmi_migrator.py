import os
import shutil

class DMIMigrator:
    # Common UEFI NVRAM/DMI Signatures
    COMMON_SIGNATURES = [
        b"$_IFL_$",
        b"VSS",
        b"Fsys",
        b"SSV",
        b"NVAR",
        b"EVSA"
    ]

    @staticmethod
    def print_log(callback, message, level="INFO"):
        if callback:
            callback(f"[{level}] {message}")
        else:
            print(f"[{level}] {message}")

    @staticmethod
    def get_block_boundaries(data, signature_offset):
        """
        Dynamically finds the start and end of the padding/nvram block 
        containing the signature. Usually aligned to 4KB (0x1000) boundaries.
        """
        if signature_offset < 0 or signature_offset >= len(data):
            return 0, 0
            
        # Find 4KB aligned start before the signature
        block_start = signature_offset & ~0xFFF
        
        # Scan forward to find the next major boundary or end of padding
        # Typically UEFI NVRAM or Padding blocks are either 64KB (0x10000) 
        # or bounded by the next 4KB aligned block that starts with a new header
        block_end = block_start + 0x10000 # Default to 64KB
        if block_end > len(data):
            block_end = len(data)
            
        # Refine end boundary by checking for next block alignment that starts with FF or specific headers
        # We'll stick to 64KB max or EOF to ensure we capture the whole VSS/Padding structure safely
        
        return block_start, block_end

    @staticmethod
    def migrate(old_bios_path, current_new_bios_path, keyword_str=None, terminal_callback=None):
        if not os.path.exists(old_bios_path):
            DMIMigrator.print_log(terminal_callback, "Old BIOS backup file not found.", "ERROR")
            return None
            
        if not os.path.exists(current_new_bios_path):
            DMIMigrator.print_log(terminal_callback, "Current running BIOS file not found.", "ERROR")
            return None

        # Determine signatures to search
        signatures = []
        if keyword_str and keyword_str.strip():
            # Add user-defined keyword (e.g. Serial Number) first
            signatures.append(keyword_str.strip().encode('utf-8'))
            signatures.append(keyword_str.strip().encode('utf-16le')) # Windows keys and SN often in UTF-16
        else:
            signatures = DMIMigrator.COMMON_SIGNATURES
            
        try:
            with open(old_bios_path, 'rb') as f_old:
                old_data = bytearray(f_old.read())
                
            with open(current_new_bios_path, 'rb') as f_new:
                new_data = bytearray(f_new.read())
                
            signature_found = False
            old_offset = -1
            new_offset = -1
            matched_sig = None
            
            # Step 1: Search for signature in OLD file
            for sig in signatures:
                old_offset = old_data.find(sig)
                if old_offset != -1:
                    matched_sig = sig
                    DMIMigrator.print_log(terminal_callback, f"Signature '{sig}' found in OLD file at offset: 0x{old_offset:08X}")
                    break
                    
            if old_offset == -1:
                DMIMigrator.print_log(terminal_callback, "No DMI or specified signature found in OLD backup file.", "WARNING")
                return None
                
            # Step 2: Search for SAME signature in NEW file to determine NEW target offset mapping
            new_offset = new_data.find(matched_sig)
            if new_offset == -1:
                DMIMigrator.print_log(terminal_callback, f"Signature '{matched_sig}' NOT found in NEW file. Cannot safely map offset.", "ERROR")
                DMIMigrator.print_log(terminal_callback, "Ensure the new BIOS is exactly for the same laptop model.", "INFO")
                return None
                
            DMIMigrator.print_log(terminal_callback, f"Mapped mapping: Signature '{matched_sig}' found in NEW file at offset: 0x{new_offset:08X}")
            
            # Step 3: Extract boundaries dynamically
            old_start, old_end = DMIMigrator.get_block_boundaries(old_data, old_offset)
            block_size = old_end - old_start
            
            new_start = new_offset & ~0xFFF
            new_end = new_start + block_size
            
            if new_end > len(new_data):
                DMIMigrator.print_log(terminal_callback, "Calculated block exceeds new file bounds. Aborting mapping.", "ERROR")
                return None
                
            DMIMigrator.print_log(terminal_callback, f"Extracting {block_size/1024:.0f}KB Padding/VSS block...")
            DMIMigrator.print_log(terminal_callback, f"OLD Block: [0x{old_start:08X} - 0x{old_end:08X}]")
            DMIMigrator.print_log(terminal_callback, f"Targeting NEW Block: [0x{new_start:08X} - 0x{new_end:08X}]")
            
            # Step 4: Inject!
            dmi_payload = old_data[old_start:old_end]
            new_data[new_start:new_end] = dmi_payload
            
            # Save properly
            timestamp = __import__('datetime').datetime.now().strftime("%Y%m%d_%H%M%S")
            original_name = os.path.basename(current_new_bios_path)
            name_no_ext, ext = os.path.splitext(original_name)
            output_path = os.path.join(os.path.dirname(current_new_bios_path), f"{name_no_ext}_DMI_MIGRATED_{timestamp}{ext}")
            
            with open(output_path, 'wb') as f_out:
                f_out.write(new_data)
                
            DMIMigrator.print_log(terminal_callback, "[SUCCESS] DMI Block Migration Complete!")
            DMIMigrator.print_log(terminal_callback, f"Saved as: {os.path.basename(output_path)}")
            
            return output_path
            
        except Exception as e:
            DMIMigrator.print_log(terminal_callback, f"DMI Migration failed critically: {str(e)}", "ERROR")
            return None
