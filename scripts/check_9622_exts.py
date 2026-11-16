import sys
sys.path.insert(0, r"d:\BIOS_-TOOL\external\MEAnalyzer")

fpath = r'D:\SDD DATA\all bios\Bios\HP\6050A3059101-MB-A01 (A1)\New folder\read 9-6-22.bin'
with open(fpath, 'rb') as f:
    reading = f.read()

# Let's inspect FTPR manifest in read 9-6-22.bin
import re
mn2_matches = [m.start() for m in re.finditer(b'\\$MN2', reading)]
print("MN2 matches:", [hex(m) for m in mn2_matches])
for m in mn2_matches:
    hdr_start = m - 0x1C
    hdr_len = int.from_bytes(reading[hdr_start+4:hdr_start+8], 'little') * 4
    # Scan extensions
    curr = hdr_start + hdr_len
    exts = []
    for _ in range(20):
        if curr + 8 > len(reading): break
        ext_type = int.from_bytes(reading[curr:curr+4], 'little')
        ext_len = int.from_bytes(reading[curr+4:curr+8], 'little')
        exts.append((hex(ext_type), hex(ext_len)))
        if ext_len == 0: break
        curr += ext_len
    print(f"MN2 at {hex(m)} has exts:", exts[:8])
