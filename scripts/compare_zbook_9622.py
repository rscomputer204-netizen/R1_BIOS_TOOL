import struct

def dump_lt(fpath):
    with open(fpath, "rb") as f: data = f.read()
    for base in [0, 0x1000, 0x2000, 0x3000, 0x4000]:
        if base + 0x40 <= len(data):
            romb0, romb1, romb2, romb3, d_off, d_sz, b1_off, b1_sz, b2_off, b2_sz, b3_off, b3_sz, b4_off, b4_sz, b5_off, b5_sz = struct.unpack('<IIIIIIIIIIIIIIII', data[base:base+0x40])
            b_cand = [b1_off, b2_off, b3_off, b4_off, b5_off]
            if any(off < len(data) and data[base+off:base+off+4] in (b'\xAA\x55\x00\x00', b'\xAA\x55\xAA\x00') for off in b_cand if off not in (0, 0xFFFFFFFF)):
                print(fpath.split(chr(92))[-1][:20])
                print(f"base={hex(base)}")
                print(f"d_off={hex(d_off)}, d_sz={hex(d_sz)}")
                print(f"b1_off={hex(b1_off)}, b1_sz={hex(b1_sz)}")
                print(f"b2_off={hex(b2_off)}, b2_sz={hex(b2_sz)}")
                print("="*40)
                break

dump_lt(r'D:\SDD DATA\all bios\Bios\HP\HP ZBook 15 G5 Mobile Workstation DA0XW2MBAG0 XW2A\orginal read no power.bin')
dump_lt(r'D:\SDD DATA\all bios\Bios\HP\6050A3059101-MB-A01 (A1)\New folder\read 9-6-22.bin')
