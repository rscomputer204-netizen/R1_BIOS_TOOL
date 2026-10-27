import struct
from pathlib import Path

def parse_descriptor():
    bios_path = Path("TESTING_AREA/MAIN BIOS/read en.bin")
    data = bios_path.read_bytes()
    
    # Descriptor signature at 0x10
    desc_sig = data[0x10:0x14]
    if desc_sig != b"\x5A\xA5\xF0\x0F":
        print("Invalid Descriptor Signature")
        return

    # Region section pointer at 0x14
    # The pointer is at [0x14:0x15], it's an offset into the descriptor
    # Wait, in Flash Descriptor v1, it's bits 15:8 of the DWORD at 0x14.
    # Actually, it's simpler:
    # 0x00: Signature
    # 0x04: Component Section
    # 0x08: Region Section
    # 0x0C: Master Section
    
    # Let's just read the Region Section directly
    # In newer descriptors, Region Section starts at 0x40
    # Region 0: Descriptor (Base: 0x0000, Limit: 0x0FFF)
    # Region 1: BIOS
    # Region 2: ME
    
    for i in range(10):
        # Each region entry is 4 bytes
        # Base: bits 11:0 * 0x1000
        # Limit: bits 27:16 * 0x1000 + 0xFFF
        entry = struct.unpack("<I", data[0x40 + i*4 : 0x44 + i*4])[0]
        base = (entry & 0x7FFF) << 12
        limit = ((entry >> 16) & 0x7FFF) << 12 | 0xFFF
        
        if entry == 0 or entry == 0xFFFFFFFF: continue
        
        names = ["Descriptor", "BIOS", "ME", "GbE", "PDR", "DevExp", "BIOS2", "Microcode"]
        name = names[i] if i < len(names) else f"Region {i}"
        
        print(f"{name:10} | Base: 0x{base:08X} | Limit: 0x{limit:08X} | Size: 0x{limit-base+1:X}")

if __name__ == "__main__":
    parse_descriptor()
