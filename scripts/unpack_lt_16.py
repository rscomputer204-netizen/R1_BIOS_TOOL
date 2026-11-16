import struct

fpath = r'D:\SDD DATA\all bios\Bios\HP\6050A3059101-MB-A01 (A1)\ok 100\read raju.bin'
with open(fpath, "rb") as f: data = f.read()

base = 0x1000
romb0, romb1, romb2, romb3, d_off, d_sz, b1_off, b1_sz, b2_off, b2_sz, b3_off, b3_sz, b4_off, b4_sz, b5_off, b5_sz = struct.unpack('<IIIIIIIIIIIIIIII', data[base:base+0x40])
print(f"Data: off={hex(d_off)} sz={hex(d_sz)}")
print(f"BP1 : off={hex(b1_off)} sz={hex(b1_sz)}")
print(f"BP2 : off={hex(b2_off)} sz={hex(b2_sz)}")
print(f"BP3 : off={hex(b3_off)} sz={hex(b3_sz)}")
print(f"BP4 : off={hex(b4_off)} sz={hex(b4_sz)}")
print(f"BP5 : off={hex(b5_off)} sz={hex(b5_sz)}")

total = 0x1000 + d_sz + b1_sz + b2_sz
print("Total size:", hex(total))
