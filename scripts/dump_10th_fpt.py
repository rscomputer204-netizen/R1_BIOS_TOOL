import struct

with open(r'D:\SDD DATA\all bios\Bios\HP\10th gen_DA0X8LMB8D0 REV D\clean test ok under side ram.bin', 'rb') as f:
    data = f.read()

fpt_off = 0x2000
num_entries = struct.unpack('<I', data[fpt_off+4:fpt_off+8])[0]
print("Num entries:", num_entries)
max_end = 0
for i in range(num_entries):
    e = data[fpt_off+32+i*32 : fpt_off+32+(i+1)*32]
    name = e[:4].rstrip(b'\x00').decode('latin1')
    poff, sz = struct.unpack('<II', e[8:16])
    print(f"  {name:4s}: off=0x{poff:x} sz=0x{sz:x} end=0x{poff+sz:x}")
    if poff != 0xffffffff and sz != 0xffffffff:
        max_end = max(max_end, poff + sz)

print("max_end from FPT:", hex(max_end))
print("max_end + 0x2000:", hex(max_end + 0x2000))
