import re, struct

fpath = r'D:\SDD DATA\all bios\Bios\HP\01015fy00-388-g\dump_main.bin'
with open(fpath, 'rb') as f:
    reading = f.read()

# Let's inspect the FPT at 0xf10
fpt_hdr = reading[0xf10:0xf10+0x20]
print("FPT header:", fpt_hdr.hex())
# In FPT v1 (length 0x20):
# 0x00: $FPT
# 0x04: num_entries
# 0x08: header_version
# 0x0c: entry_size
num_entries = struct.unpack('<I', fpt_hdr[4:8])[0]
hdr_ver = struct.unpack('<I', fpt_hdr[8:12])[0]
print("num_entries:", num_entries, "hdr_ver:", hex(hdr_ver))
for i in range(min(num_entries, 10)):
    entry = reading[0xf30 + i*0x20 : 0xf30 + (i+1)*0x20]
    name = entry[:4].decode('latin1', errors='replace')
    off = struct.unpack('<I', entry[8:12])[0]
    sz = struct.unpack('<I', entry[12:16])[0]
    print(f"Part {i}: {name} off={hex(off)} sz={hex(sz)}")
