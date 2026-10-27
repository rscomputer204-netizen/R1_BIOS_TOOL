import os
from pathlib import Path

def print_terminal_log(callback, message, level="INFO"):
    """Sends a message to the terminal UI callback."""
    if callback:
        callback(f"[{level}] {message}")
    else:
        print(f"[{level}] {message}")

def recompile_bios(original_bios_path, workspace_dir, regions_map, output_path, terminal_callback=None):
    """
    Rebuilds the BIOS by taking the original file as a template and overlaying
    all modified region files from the WORKSPACE onto their precise offsets.
    """
    if not os.path.exists(original_bios_path):
        print_terminal_log(terminal_callback, "[ERROR] Original BIOS file missing for template.", "ERROR")
        return False
        
    try:
        # Load the original BIOS as the base template
        with open(original_bios_path, "rb") as f:
            template_data = bytearray(f.read())
            
        workspace = Path(workspace_dir)
        bios_name = Path(original_bios_path).stem
        target_dir = workspace / bios_name
        
        if not target_dir.exists():
            # Fallback if standard extraction didn't nest into bios_name
            target_dir = workspace

        print_terminal_log(terminal_callback, f"[INFO] Preparing to recompile BIOS...")
        
        # Overlay each region found in the workspace
        overlay_count = 0
        for region_name, region_data in regions_map.items():
            offset = region_data.get('offset', 0)
            size = region_data.get('size', 0)
            if size <= 0: continue
                
            display_name = region_name.lower().replace("_", " ").title()
            if " Region" not in display_name:
                chunk_display = f"{display_name} Region"
            else:
                chunk_display = display_name
                
            chunk_filename = f"{chunk_display}.bin"
            chunk_path = target_dir / chunk_filename
            
            if chunk_path.exists():
                with open(chunk_path, "rb") as f:
                    chunk_data = f.read()
                    
                # Ensure the chunk data does not exceed the Flash Descriptor limit
                if len(chunk_data) > size:
                    print_terminal_log(terminal_callback, f"[WARNING] {chunk_filename} is larger than allocated ({size} bytes). Truncating...", "WARNING")
                    chunk_data = chunk_data[:size]
                    
                # Write chunk into template
                template_data[offset:offset + len(chunk_data)] = chunk_data
                
                # If chunk is smaller, pad the rest of the region with 0xFF
                if len(chunk_data) < size:
                    padding_len = size - len(chunk_data)
                    template_data[offset + len(chunk_data):offset + size] = b'\xFF' * padding_len
                    print_terminal_log(terminal_callback, f"[INFO] Padded {chunk_filename} with {padding_len} bytes (0xFF).")
                    
                overlay_count += 1
                
        # Write final reconstructed file
        with open(output_path, "wb") as out_f:
            out_f.write(template_data)
            
        print_terminal_log(terminal_callback, f"[SUCCESS] Recompiled BIOS successfully (Overlaid {overlay_count} regions).")
        return True
        
    except Exception as e:
        print_terminal_log(terminal_callback, f"[ERROR] Recompilation failed: {str(e)}", "ERROR")
        return False
