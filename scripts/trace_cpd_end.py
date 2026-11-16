with open(r"D:\SDD DATA\all bios\Bios\LENOVO\LA-H101P REV1.0\read bin.bin", "rb") as f:
    d = f.read()

import struct

# CPD at 0x174000
cpd_off = 0x174000
tag = d[cpd_off:cpd_off+4]
num = struct.unpack('<I', d[cpd_off+4:cpd_off+8])[0]
print(f"CPD at {hex(cpd_off)}: tag={tag}, num_entries={num}")
max_end = 0
for i in range(num):
    e_off = cpd_off + 16 + i * 24
    name = d[e_off:e_off+12].rstrip(b'\x00').decode('ascii', errors='ignore')
    off = struct.unpack('<I', d[e_off+12:e_off+16])[0] & 0x01FFFFFF
    sz = struct.unpack('<I', d[e_off+16:e_off+20])[0]
    print(f"  {name}: off={hex(off)}, sz={hex(sz)}, end={hex(off+sz)}, abs_end={hex(cpd_off+off+sz)}")
    max_end = max(max_end, cpd_off + off + sz)

print("Max end from CPD:", hex(max_end))
print("Max end relative to me_fd_start (0x1000):", hex(max_end - 0x1000))
