with open(r'D:\SDD DATA\all bios\Bios\LENOVO\NM-B891 BIOS T490S\pass.bin', 'rb') as f:
    d = f.read()

import struct

bpdt_sig = b"\x00\x00\xaa\x55" # or BPDT
print("BPDT text:", d.find(b"__BPDT__"), d.find(b"BPDT"))

# Search for $CPD
pos = 0
cpds = []
while True:
    p = d.find(b"$CPD", pos)
    if p == -1: break
    cpds.append(p)
    pos = p + 4

print("Found $CPD at:", [hex(p) for p in cpds])

# Check what MEA found for size 0x77D000:
# Where is 0x77D000 relative to me_fd_start (0x3000)?
# 0x3000 + 0x77D000 = 0x780000!
print("At 0x780000:", d[0x780000-16:0x780000+16])
print("Non-FF before 0x780000:")
chunk = d[0x3000:0xa00000]
print("len of chunk:", hex(len(chunk)))
print("rstripped chunk len:", hex(len(chunk.rstrip(b'\xff'))))
