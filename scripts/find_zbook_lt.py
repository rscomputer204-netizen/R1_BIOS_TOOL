fpath = r'D:\SDD DATA\all bios\Bios\HP\HP ZBook 15 G5 Mobile Workstation DA0XW2MBAG0 XW2A\orginal read no power.bin'
with open(fpath, "rb") as f: data = f.read()

# Let's search for CSE LT in ZBook
# Where is base in ZBook?
for base in range(0, 0x10000, 0x1000):
    if data[base+0x10:base+0x14] in [b'\x40\x00\x00\x00', b'\x48\x00\x00\x00', b'\x00\x40\x00\x00', b'\x00\xc0\x20\x00'] or (data[base:base+4] == b'\xff'*4 and data[base+0x14:base+0x18] in [b'\x00\x40\x00\x00', b'\x00\x10\x00\x00', b'\x00\xc0\x20\x00']):
        print(f"Candidate base at {hex(base)}: {data[base:base+40].hex()}")
