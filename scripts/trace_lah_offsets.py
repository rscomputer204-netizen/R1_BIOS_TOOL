with open(r"D:\SDD DATA\all bios\Bios\LENOVO\LA-H101P REV1.0\read bin.bin", "rb") as f:
    d = f.read()

# ME region in FD
me_start = 0x1000
me_end = 0x400000
# Search for $FPT or CSE LT in me region
print("len of d:", hex(len(d)))
print("bytes at 0x0..0x20:", d[:32].hex())
import re
print("All $FPT offsets:", [hex(m.start()) for m in re.finditer(rb'\$FPT', d)])
print("All $CPD offsets:", [hex(m.start()) for m in re.finditer(rb'\$CPD', d)])
print("All $MN2 offsets:", [hex(m.start()) for m in re.finditer(rb'\$MN2', d)])
