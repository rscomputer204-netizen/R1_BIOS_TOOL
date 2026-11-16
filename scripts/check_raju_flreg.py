fpath = r'D:\SDD DATA\all bios\Bios\HP\6050A3059101-MB-A01 (A1)\ok 100\read raju.bin'
with open(fpath, 'rb') as f:
    reading = f.read()

# Let's inspect 0x0 to 0x200
print("0x0..0x100:", reading[:0x100].hex())
# What was the FD?
# FD was at 0x10
# me_fd_start = 0x10 + 0x1000 = 0x1010? Or what was me_fd_start?
# Let's check FLREG
import struct
flreg1 = struct.unpack('<I', reading[0x10 + 0x44 : 0x10 + 0x48])[0]
print("FLREG1 (BIOS):", hex(flreg1))
flreg2 = struct.unpack('<I', reading[0x10 + 0x48 : 0x10 + 0x4C])[0]
print("FLREG2 (ME):", hex(flreg2))
me_base = (flreg2 & 0x1FFF) * 0x1000
me_limit = ((flreg2 >> 16) & 0x1FFF) * 0x1000
print(f"me_base={hex(me_base)}, me_limit={hex(me_limit)}")
