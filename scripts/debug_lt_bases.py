import os, sys, struct

fpath = r'D:\SDD DATA\all bios\Bios\HP\6050A3059101-MB-A01 (A1)\ok 100\read raju.bin'
with open(fpath, "rb") as f: data = f.read()

for base in [0, 0x1000, 0x2000, 0x3000, 0x4000]:
    sz = struct.unpack("<H", data[base + 0x10 : base + 0x12])[0]
    print(f"base={hex(base)}, sz={hex(sz)}")
