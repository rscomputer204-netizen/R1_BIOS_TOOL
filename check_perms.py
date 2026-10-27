import struct
from pathlib import Path

def check_permissions():
    bios_path = Path("TESTING_AREA/MAIN BIOS/read en.bin")
    data = bios_path.read_bytes()
    
    # Master Section at 0x60
    # Each Master entry is 3 DWORDS (Descriptor, ME, GbE)
    # CPU/BIOS Master is usually the first one
    
    print("Master Permissions (0xFF = Open):")
    for i in range(3):
        # 0x60: Master 1 (CPU/BIOS)
        # 0x6C: Master 2 (ME)
        # 0x78: Master 3 (GbE)
        m_base = 0x60 + i*12
        m_read = data[m_base + 8]
        m_write = data[m_base + 9]
        names = ["CPU/BIOS", "ME", "GbE"]
        print(f"{names[i]:10} | Read: 0x{m_read:02X} | Write: 0x{m_write:02X}")

if __name__ == "__main__":
    check_permissions()
