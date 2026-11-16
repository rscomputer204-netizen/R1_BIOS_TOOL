import struct

fpath = r'D:\SDD DATA\all bios\Bios\HP\HP ZBook 15 G5 Mobile Workstation DA0XW2MBAG0 XW2A\orginal read no power.bin'
with open(fpath, "rb") as f: data = f.read()

for base in [0, 0x1000, 0x2000, 0x3000, 0x4000]:
    sz = struct.unpack("<H", data[base + 0x10 : base + 0x12])[0]
    print(f"base={hex(base)}, sz={hex(sz)}")

# Check Flash Descriptor ME region:
# Where is FD in ZBook?
fd_pos = data.find(b'\x5A\xA5\xF0\x0F')
print("FD at:", hex(fd_pos))
flreg2 = struct.unpack('<I', data[fd_pos+0x48:fd_pos+0x4C])[0]
me_start = (flreg2 & 0x1FFF) * 0x1000
me_end = (((flreg2 >> 16) & 0x1FFF) + 1) * 0x1000
print(f"ME region: {hex(me_start)} - {hex(me_end)}")
