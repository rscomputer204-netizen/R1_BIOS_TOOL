import struct

fpath = r'D:\SDD DATA\all bios\Bios\HP\6050A3059101-MB-A01 (A1)\ok 100\read raju.bin'
with open(fpath, 'rb') as f:
    reading = f.read()

# Inspect CPD at 0x104000
cpd_hdr = reading[0x104000:0x104014]
num_entries = struct.unpack('<I', cpd_hdr[4:8])[0]
print("NFTP CPD num_entries:", num_entries)
max_end = 0
for i in range(num_entries):
    e = reading[0x104014 + i*0x18 : 0x104014 + (i+1)*0x18]
    name = e[:12].decode('latin1', errors='replace').strip('\x00')
    off = struct.unpack('<I', e[0x0c:0x10])[0] & 0x01FFFFFF
    sz = struct.unpack('<I', e[0x10:0x14])[0]
    end = 0x104000 + off + sz
    if end > max_end:
        max_end = end
    print(f"  {name}: off={hex(off)} sz={hex(sz)} end={hex(end)}")

print(f"Max end in NFTP: {hex(max_end)}")
print(f"Max end aligned to 4KB: {hex((max_end + 0xFFF) & ~0xFFF)}")
