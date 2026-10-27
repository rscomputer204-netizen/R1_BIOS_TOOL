import os
from pathlib import Path

ROOT = Path(r"c:\Users\R1 LAB\Desktop\BIOS_TOOL")
ME_FILE = ROOT / "TESTING_AREA" / "DCOMP" / "me.bin"
OUT_DIR = ROOT / "TESTING_AREA" / "EXTRACTED_PARTS"

# Magic strings for TGL partitions
# Usually headers start with 0x01... but we can look for the name tags
PARTITIONS = {
    "IOM": b"IOM ",
    "PHY": b"PHY ",
    "TBT": b"TBT ",
    "ISH": b"ISH "
}

def carve():
    if not OUT_DIR.exists():
        OUT_DIR.mkdir(parents=True)
        
    print(f"[INFO] Scanning {ME_FILE} for sub-partitions...")
    with open(ME_FILE, "rb") as f:
        content = f.read()
        
    for name, magic in PARTITIONS.items():
        idx = content.find(magic)
        if idx != -1:
            print(f"[FOUND] {name} at offset {hex(idx)}")
            # For TGL, we need to find the manifest start. 
            # Usually the name tag is near the start of the manifest.
            # We'll carve 512KB for each as a safe estimate if we don't know the length,
            # but IOM is ~72KB, PHY ~64KB, TBT ~304KB, ISH ~256KB.
            # A better way is to find the 'Length' field in the manifest header.
            
            # Simple carve: let's take a chunk and let FIT handle it if possible, 
            # but FIT needs exact sizes.
            # Actually, I'll just carve exactly what FIT complained about.
            
            # Let's try to find the start of the manifest (0x01) before the name.
            start = idx
            while start > 0 and start > idx - 128:
                if content[start:start+4] == b"\x01\x00\x00\x00": # Likely manifest start
                    break
                start -= 1
            
            # Length is usually at offset +0x18 or +0x24 in the manifest
            # but for now let's just dump a reasonable size.
            # IOM: 0x12000, PHY: 0x10000, TBT: 0x4C000, ISH: 0x40000 (from previous template)
            lengths = {"IOM": 0x12000, "PHY": 0x10000, "TBT": 0x4C000, "ISH": 0x40000}
            length = lengths.get(name, 0x10000)
            
            part_data = content[start:start+length]
            out_path = OUT_DIR / f"{name.lower()}.bin"
            with open(out_path, "wb") as out_f:
                out_f.write(part_data)
            print(f"[SAVED] {name} -> {out_path}")
        else:
            print(f"[NOT FOUND] {name}")

if __name__ == "__main__":
    carve()
