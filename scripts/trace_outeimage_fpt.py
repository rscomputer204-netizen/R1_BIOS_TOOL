with open(r"D:\SDD DATA\all bios\Bios\LENOVO\GE4B0-GE5B0nm-d011.rev 1.0\GE4B0 GE5B0 NM-D011\outeimage bin.rom", "rb") as f:
    d = f.read()

import struct

# Where is $FPT in outeimage bin.rom?
pos = 0
sig_fpt = b"$FPT"
while True:
    p = d.find(sig_fpt, pos)
    if p == -1: break
    print("Found $FPT at:", hex(p))
    num = struct.unpack('<I', d[p+4:p+8])[0]
    print(f"  num={num}")
    if num < 64:
        for i in range(num):
            off = p + 32 + i*32
            pname = d[off:off+4].decode('ascii', errors='ignore')
            poff = struct.unpack('<I', d[off+8:off+12])[0]
            psz = struct.unpack('<I', d[off+12:off+16])[0]
            print(f"    {pname}: offset={hex(poff)}, size={hex(psz)}, end={hex(poff+psz)}")
    pos = p + 4
