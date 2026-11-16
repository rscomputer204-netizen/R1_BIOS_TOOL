fpath = r'D:\SDD DATA\all bios\Bios\HP\6050A3059101-MB-A01 (A1)\ok 100\read raju.bin'
with open(fpath, 'rb') as f:
    reading = f.read()

for off in [0x0, 0x1000, 0x2000, 0x3000]:
    print(f"Offset {hex(off)}: {reading[off:off+32].hex()}")
