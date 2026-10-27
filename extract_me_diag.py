import os
from pathlib import Path

def find_me_region():
    bios_path = Path("TESTING_AREA/MAIN BIOS/read en.bin")
    if not bios_path.exists():
        print("BIOS not found.")
        return

    data = bios_path.read_bytes()
    offset = data.find(b"$FPT")
    if offset == -1:
        print("FPT Header not found.")
        return

    print(f"FPT Header found at: 0x{offset:X}")
    
    # Standard ME region usually starts slightly before FPT or at FPT
    # We'll extract 8MB starting from the first potential FPT
    # Or we can look for the Flash Descriptor
    
    descriptor_offset = data.find(b"\x5A\xA5\xF0\x0F")
    if descriptor_offset != -1:
        print(f"Flash Descriptor found at: 0x{descriptor_offset:X}")
        # Read the ME region base from the descriptor
        # Offset 0x44 in Descriptor is the Region Section
        # ME Region base/limit is at 0x48 in the Region Section
        me_reg_info = data[descriptor_offset + 0x44 + 4 : descriptor_offset + 0x44 + 8]
        # Format is [Limit High:Base High] [Limit Low:Base Low]
        # Actually it's simpler in newer descriptors.
        
    # Let's just extract the ME region based on the size we know (8MB)
    me_size = 0x7F8000
    me_data = data[offset : offset + me_size]
    
    with open("TESTING_AREA/extracted_me.bin", "wb") as f:
        f.write(me_data)
    print("Extracted ME region saved to TESTING_AREA/extracted_me.bin")

if __name__ == "__main__":
    find_me_region()
