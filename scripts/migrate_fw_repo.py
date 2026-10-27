import os
import sys
import shutil
import json
from pathlib import Path

def parse_filename_to_metadata(filename: str) -> dict:
    """Extracts metadata from standard ME firmware filenames."""
    name = filename.upper().replace('.BIN', '')
    parts = name.split('_')
    
    version = parts[0]
    v_parts = version.split('.')
    major = int(v_parts[0]) if v_parts[0].isdigit() else 0
    minor = int(v_parts[1]) if len(v_parts) > 1 and v_parts[1].isdigit() else 0
    
    sku = "UNKNOWN"
    if "COR" in parts: sku = "CORPORATE"
    elif "CON" in parts: sku = "CONSUMER"
    elif "SLM" in parts: sku = "SLIM"
    elif "LIT" in parts: sku = "LITE"
    elif "SVR" in parts: sku = "SERVER"
    elif "CHR" in parts: sku = "CHROME"
    elif "1.5MB" in parts: sku = "1.5MB"
    elif "5MB" in parts: sku = "5MB"
    
    # Check LP (Low Power) vs H (High performance) vs N vs V
    power = "UNKNOWN"
    if "LP" in parts: power = "LP"
    elif "H" in parts: power = "H"
    elif "N" in parts: power = "N"
    elif "V" in parts: power = "V"
    
    status = "UNKNOWN"
    if "PRD" in parts: status = "PRODUCTION"
    elif "PRE" in parts: status = "PRE-PRODUCTION"
    
    origin = "UNKNOWN"
    if "EXTR" in name or "EXTR-Y" in name: origin = "EXTRACTED"
    elif "RGN" in name: origin = "REGION"
    elif "UPD" in name: origin = "UPDATE"
    
    return {
        "version": version,
        "major": major,
        "minor": minor,
        "sku": sku,
        "power": power,
        "status": status,
        "origin": origin,
        "original_filename": filename
    }

def migrate_repo(target_dir: str):
    base_path = Path(target_dir)
    if not base_path.exists():
        print(f"Directory not found: {base_path}")
        return
        
    print(f"Migrating: {base_path}")
    count = 0
    
    for file_path in list(base_path.glob("*.bin")):
        if not file_path.is_file():
            continue
            
        filename = file_path.name
        meta = parse_filename_to_metadata(filename)
        
        major = str(meta["major"])
        dir_name = filename.replace('.bin', '').replace('.BIN', '')
        
        # Target directory: Firmware_Repository/ME_Region/<Major>/<Filename>/
        new_dir = base_path / major / dir_name
        new_dir.mkdir(parents=True, exist_ok=True)
        
        new_file_path = new_dir / filename
        meta_file_path = new_dir / "metadata.json"
        
        # Move file
        print(f"Moving: {filename} -> {major}/{dir_name}/")
        shutil.move(str(file_path), str(new_file_path))
        
        # Create metadata
        with open(meta_file_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=4)
            
        count += 1
        
    print(f"Successfully migrated {count} ME firmware files.")

if __name__ == "__main__":
    target = r"Firmware_Repository\ME_Region"
    if len(sys.argv) > 1:
        target = sys.argv[1]
    migrate_repo(target)
