with open(r'D:\SDD DATA\all bios\Bios\LENOVO\NM-B891 BIOS T490S\pass.bin', 'rb') as f:
    d = f.read()

import struct
pos = 0
sig_fpt = b"$FPT"
fpts = []
while True:
    p = d.find(sig_fpt, pos)
    if p == -1: break
    fpts.append(p)
    pos = p + 4

print("Found FPTs:", len(fpts))
for p in fpts:
    num = struct.unpack('<I', d[p+4:p+8])[0]
    if num > 64:
        continue
    print(f"Valid FPT at {hex(p)} with {num} entries:")
    max_end = 0
    for i in range(num):
        off = p + 32 + i*32
        pname = d[off:off+4].decode('ascii', errors='ignore')
        poff = struct.unpack('<I', d[off+8:off+12])[0]
        psz = struct.unpack('<I', d[off+12:off+16])[0]
        if poff != 0xFFFFFFFF and psz != 0xFFFFFFFF:
            max_end = max(max_end, poff + psz)
            print(f"  {pname}: offset={hex(poff)}, size={hex(psz)}, end={hex(poff+psz)}")
    print(f"  -> max partition end: {hex(max_end)}")
