import os
from pathlib import Path

def print_terminal_log(callback, message, level="INFO"):
    """Sends a message to the terminal UI callback."""
    if callback:
        callback(f"[{level}] {message}")
    else:
        print(f"[{level}] {message}")

def decompile_bios(file_path, regions_map, output_base_dir=None, terminal_callback=None):
    """
    Reads the BIOS file and extracts each region into a separate binary file
    within a new folder named after the BIOS file.
    """
    if not file_path or not os.path.exists(file_path):
        print_terminal_log(terminal_callback, "[ERROR] Invalid BIOS file path provided for decompilation.", "ERROR")
        return False

    if not regions_map:
        print_terminal_log(terminal_callback, "[WARNING] No regions available to decompile.", "WARNING")
        return False

    try:
        # Determine paths
        bio_path = Path(file_path)
        base_name = bio_path.name
        safe_name = bio_path.stem
        
        # Use provided output_base_dir if given, otherwise use bio_path's parent
        target_base = Path(output_base_dir) if output_base_dir else bio_path.parent
        out_dir = target_base / safe_name

        # Create output directory
        os.makedirs(out_dir, exist_ok=True)
        print_terminal_log(terminal_callback, f"[INFO] Decompiling '{base_name}'...")
        print_terminal_log(terminal_callback, f"[INFO] Output Directory: {out_dir}")

        # Open the source BIOS file
        with open(file_path, "rb") as source_file:
            for region_name, region_data in regions_map.items():
                offset = region_data.get('offset', 0)
                size = region_data.get('size', 0)

                if size <= 0:
                    continue

                # Prepare the chunk output path
                # Format name: e.g. "me_region" -> "Me Region.bin"
                display_name = region_name.lower().replace("_", " ").title()
                if " Region" not in display_name:
                    chunk_display = f"{display_name} Region"
                else:
                    chunk_display = display_name
                
                chunk_filename = f"{chunk_display}.bin"
                chunk_path = out_dir / chunk_filename

                # Seek to offset and read chunk
                source_file.seek(offset)
                chunk_data = source_file.read(size)

                # Write chunk to new file
                with open(chunk_path, "wb") as chunk_file:
                    chunk_file.write(chunk_data)

                # Format size for logging
                if size < 1024 * 1024:
                    size_str = f"{size / 1024:.0f} KB"
                else:
                    size_str = f"{size / (1024 * 1024):.2f} MB"
                
                print_terminal_log(terminal_callback, f"[SUCCESS] Extracted: {chunk_filename} ({size_str})")

        print_terminal_log(terminal_callback, f"[INFO] Decompilation completed successfully! All regions saved to: {out_dir.name}")
        return True

    except Exception as e:
        print_terminal_log(terminal_callback, f"[ERROR] Decompilation failed: {str(e)}", "ERROR")
        return False

# For testing independently
if __name__ == "__main__":
    pass
