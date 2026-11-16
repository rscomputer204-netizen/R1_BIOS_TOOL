import struct

fpath = r'D:\SDD DATA\all bios\Bios\HP\dv6 DA0LX6MB6H1 REV.H\ok clean main.bin'
with open(fpath, 'rb') as f:
    data = f.read()

# NFTP is at 0xD2000 (or fpt_base + poff = 0x1000 + 0xD2000 = 0xD3000)
p_abs = 0x1000 + 0xD2000 # 0xD3000
print("Bytes at 0xD3000:", data[p_abs:p_abs+64].hex())
print("Sig at +0x1C:", data[p_abs+0x1c:p_abs+0x20])
hdr_len = struct.unpack("<I", data[p_abs + 0x04 : p_abs + 0x08])[0] * 4
print("hdr_len:", hex(hdr_len))
print("uint32 at 0x20:", struct.unpack("<I", data[p_abs + 0x20 : p_abs + 0x24])[0])
print("uint32 at 0x24:", struct.unpack("<I", data[p_abs + 0x24 : p_abs + 0x28])[0])

# Let's inspect MEA.py for how it calculates dynamic partition size in ME 6
# Search MEA.py for "mod_end_max" or "p_size"
with open(r'd:\BIOS_-TOOL\external\MEAnalyzer\MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

for line in text.splitlines():
    if "p_max_size" in line or "mod_end_max" in line:
        print(line[:100])
