fpath = r'D:\SDD DATA\all bios\Bios\HP\6050A3059101-MB-A01 (A1)\ok 100\read raju.bin'
with open(fpath, 'rb') as f:
    reading = f.read()

print("Bytes around 0x27A000:")
print("0x279fe0..0x27a000:", reading[0x279fe0:0x27a000].hex())
print("0x27a000..0x27a020:", reading[0x27a000:0x27a020].hex())

# Let's search all CPD partitions in read raju.bin
import re
cpd_matches = [m.start() for m in re.finditer(b'\\$CPD', reading)]
print("CPD matches:", [hex(m) for m in cpd_matches])
