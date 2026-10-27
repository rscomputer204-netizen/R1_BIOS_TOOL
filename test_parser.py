from bios_parser import get_bios_metadata, INTEL_FD_SIGNATURE
import os
import struct

def create_dummy_intel_bios(path, size_mb=16):
    """Creates a dummy BIOS file with Intel Flash Descriptor."""
    size = size_mb * 1024 * 1024
    # Create block of 0xFF
    data = bytearray([0xFF] * size)
    
    # Place Intel signature at offset 0x10
    fd_base = 0x10
    struct.pack_into(f"{len(INTEL_FD_SIGNATURE)}s", data, fd_base, INTEL_FD_SIGNATURE)
    
    # FLMAP0 at fd_base + 0x14
    # Set FRBA (bits 23:16) to 0x04. Region section will be at fd_base + 0x40
    flmap0 = 0x00040000 
    struct.pack_into("<I", data, fd_base + 0x14, flmap0)
    
    # Region Section (FRBA = 4 -> 0x40 offset from FD base)
    frba_offset = fd_base + 0x40
    
    # Region 0: Descriptor (0x0000 - 0x0FFF) -> Base 0, Limit 0
    # reg = (limit << 16) | base
    struct.pack_into("<I", data, frba_offset + 0, 0x00000000)
    
    # Region 1: BIOS (0x100000 - 0xFFFFFF) -> Base 0x100, Limit 0xFFF
    struct.pack_into("<I", data, frba_offset + 4, 0x0FFF0100)
    
    # Region 2: ME (0x1000 - 0xFFFFF) -> Base 0x001, Limit 0x0FF
    struct.pack_into("<I", data, frba_offset + 8, 0x00FF0001)
    
    with open(path, "wb") as f:
        f.write(data)
    print(f"Created dummy BIOS with Regions: {path} ({size_mb} MB)")

def test_parser():
    dummy_path = "dummy_bios.bin"
    create_dummy_intel_bios(dummy_path, 16)
    
    print("\n--- TEST: Valid Intel BIOS ---")
    metadata = get_bios_metadata(dummy_path)
    print(f"Resulting Metadata: {metadata}")
    
    # Test Invalid Size
    small_path = "small.bin"
    with open(small_path, "wb") as f:
        f.write(b"Too small")
    
    print("\n--- TEST: Small File ---")
    metadata = get_bios_metadata(small_path)
    
    # Cleanup
    os.remove(dummy_path)
    os.remove(small_path)

if __name__ == "__main__":
    test_parser()
