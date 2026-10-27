import os
import sys
import json
from pathlib import Path
sys_path = Path(r'c:\Users\R1 LAB\Desktop\BIOS_-TOOL')
sys.path.insert(0, str(sys_path / 'scripts'))
import migrate_fw_repo

target = sys_path / r'Firmware_Repository\ME_Region'
count = 0
for meta_file in target.rglob('metadata.json'):
    bin_file = meta_file.parent / (meta_file.parent.name + '.bin')
    if bin_file.exists():
        meta = migrate_fw_repo.parse_filename_to_metadata(bin_file.name)
        with open(meta_file, 'w') as f: 
            json.dump(meta, f, indent=4)
        count += 1
print(f'Updated {count} metadata files.')
