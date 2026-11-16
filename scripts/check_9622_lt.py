import struct
fpath = r'D:\SDD DATA\all bios\Bios\HP\6050A3059101-MB-A01 (A1)\New folder\read 9-6-22.bin'
with open(fpath, "rb") as f: data = f.read()

for base in [0, 0x1000, 0x2000, 0x3000, 0x4000]:
    if base + 56 <= len(data):
        sz = struct.unpack("<H", data[base + 0x10 : base + 0x12])[0]
        if sz in (0x40, 0x48):
            r0, r1, r2, r3, sz, flg, res, csum, data_off, data_sz, bp1_off, bp1_sz, bp2_off, bp2_sz, bp3_off, bp3_sz = struct.unpack("<IIIIHBBIIIIIIIII", data[base : base + 56])
            print("base:", hex(base))
            print(f"data_off={hex(data_off)}, data_sz={hex(data_sz)}")
            print(f"bp1_off={hex(bp1_off)}, bp1_sz={hex(bp1_sz)}")
            print(f"bp2_off={hex(bp2_off)}, bp2_sz={hex(bp2_sz)}")
            print(f"bp3_off={hex(bp3_off)}, bp3_sz={hex(bp3_sz)}")
