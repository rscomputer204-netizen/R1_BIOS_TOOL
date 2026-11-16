fpath = r'D:\SDD DATA\all bios\Bios\HP\6050A3059101-MB-A01 (A1)\ok 100\read raju.bin'
with open(fpath, 'rb') as f:
    reading = f.read()

import struct
lt_data = reading[0x1000:0x1040]
print("0x1000..0x1040:", lt_data.hex())
# Structure of CSE Layout Table 1.7:
# 0x00: RomBypass (16 bytes) -> all 0xFF!
# 0x10: Size (uint16)
# 0x12: Flags (uint8)
# 0x13: Reserved (uint8)
# 0x14: DataOffset (uint32)
# 0x18: DataSize (uint32)
# 0x1C: BP1Offset (uint32)
# 0x20: BP1Size (uint32)
# 0x24: BP2Offset (uint32)
# 0x28: BP2Size (uint32)
# 0x2C: BP3Offset (uint32)
# 0x30: BP3Size (uint32)
sz, flags, res = struct.unpack('<HBB', lt_data[0x10:0x14])
d_off, d_sz = struct.unpack('<II', lt_data[0x14:0x1c])
b1_off, b1_sz = struct.unpack('<II', lt_data[0x1c:0x24])
b2_off, b2_sz = struct.unpack('<II', lt_data[0x24:0x2c])
b3_off, b3_sz = struct.unpack('<II', lt_data[0x2c:0x34])
print(f"CSE LT: Size={hex(sz)}, Flags={hex(flags)}")
print(f"Data: off={hex(d_off)}, sz={hex(d_sz)}")
print(f"BP1 : off={hex(b1_off)}, sz={hex(b1_sz)}")
print(f"BP2 : off={hex(b2_off)}, sz={hex(b2_sz)}")
print(f"BP3 : off={hex(b3_off)}, sz={hex(b3_sz)}")
