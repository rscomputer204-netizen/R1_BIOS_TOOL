fpath = r'D:\SDD DATA\all bios\Bios\HP\01015fy00-388-g\dump_main.bin'
with open(fpath, 'rb') as f:
    reading = f.read()

# FD starts at 0x10
# fd_rgn_base = end_fd_match + 0x2C
# In MEA:
# start_fd_match = 0x10
# end_fd_match = 0x10 + 0x14 = 0x24 (or 0x10 + 4 = 0x14)
# Let's inspect bytes around 0x10 + 0x20..0x60
import struct
# Let's check FLMAP0, FLMAP1, FLREG
flreg_offset = 0x10 + 0x40 # usually 0x40 or 0x60
for offset in range(0x10, 0x100, 4):
    val = struct.unpack('<I', reading[offset:offset+4])[0]
    base = (val & 0x1FFF) * 0x1000
    limit = ((val >> 16) & 0x1FFF) * 0x1000
    if limit > 0:
        print(f"Offset {hex(offset)}: raw={hex(val)} base={hex(base)} limit={hex(limit)}")
