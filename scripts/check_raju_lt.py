fpath = r'D:\SDD DATA\all bios\Bios\HP\6050A3059101-MB-A01 (A1)\ok 100\read raju.bin'
with open(fpath, 'rb') as f:
    reading = f.read()

# Let's inspect reading[0x1000:0x1040]
# Earlier we saw:
# Offset 0x1000: ffffffffffffffffffffffffffffffff 00c02000 00e00600 00100000 00101000
# Wait! Offset 0x1000 had 16 0xFF bytes, then:
# 00c02000 00e00600 ...
# In MEA, cse_lt_off:
# Let's see what cse_lt_pos_17 matches in reading[:0x1000] or reading[0x1000:0x2000]!
import re, struct
cse_lt_pos_17 = re.compile(br'\x40\x00[\x00\x01]\x00.{4}(.{3}\x00){14}', re.DOTALL).search(reading[:0x2000])
if cse_lt_pos_17:
    print("Matched cse_lt_17 at:", hex(cse_lt_pos_17.start()))
    off = cse_lt_pos_17.start() - 0x10
    print("cse_lt_off:", hex(off))
    # Unpack CSE Layout Table 1.7:
    # 0x00: RomBypass
    # 0x04: Size
    # 0x08: Flags
    # 0x0C: RomBypassInstr3
    # 0x10: Partitions...
    # BP1Offset is at offset 0x10?
    for j in range(0, 0x40, 4):
        val = struct.unpack('<I', reading[off+j:off+j+4])[0]
        print(f"+{hex(j)}: {hex(val)}")
