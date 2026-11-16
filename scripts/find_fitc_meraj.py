with open(r'D:\SDD DATA\all bios\Bios\HP\6050a2930901-mb-a01(a1)\EC16MB\read meraj.bin', 'rb') as f:
    d = f.read()

# 12.0.49.1536 in bytes: 12=0x000c, 0=0x0000, 49=0x0031, 1536=0x0600
pat = b'\x0c\x00\x00\x00\x31\x00\x00\x06'
print("pat in d:", d.find(pat))
# Or struct pack <HHHH: 12, 0, 49, 1536
import struct
b1 = struct.pack('<HHHH', 12, 0, 49, 1536)
print("b1 in d:", hex(d.find(b1)) if b1 in d else "not found")
b2 = struct.pack('>HHHH', 12, 0, 49, 1536)
print("b2 in d:", hex(d.find(b2)) if b2 in d else "not found")
