with open(r"D:\SDD DATA\all bios\Bios\LENOVO\LA-H101P REV1.0\read bin.bin", "rb") as f:
    d = f.read()

import struct
pos = 0
sig_fpt = b"$FPT"
while True:
    p = d.find(sig_fpt, pos)
    if p == -1: break
    print("Found $FPT at:", hex(p))
    num = struct.unpack('<I', d[p+4:p+8])[0]
    print(f"  num={num}")
    if num < 64:
        max_end = 0
        for i in range(num):
            off = p + 32 + i*32
            pname = d[off:off+4].decode('ascii', errors='ignore')
            poff = struct.unpack('<I', d[off+8:off+12])[0]
            psz = struct.unpack('<I', d[off+12:off+16])[0]
            max_end = max(max_end, poff + psz)
            print(f"    {pname}: offset={hex(poff)}, size={hex(psz)}, end={hex(poff+psz)}")
        print(f"  -> max_end: {hex(max_end)}")
    pos = p + 4
