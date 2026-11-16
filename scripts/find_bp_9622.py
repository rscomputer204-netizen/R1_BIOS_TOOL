fpath = r'D:\SDD DATA\all bios\Bios\HP\6050A3059101-MB-A01 (A1)\New folder\read 9-6-22.bin'
with open(fpath, "rb") as f: data = f.read()

# Let's search for bp_sigs in read 9-6-22.bin
bp_sigs = (b'\xAA\x55\x00\x00', b'\xAA\x55\xAA\x00')
for s in bp_sigs:
    p = 0
    while True:
        p = data.find(s, p)
        if p == -1: break
        print(f"Found bp_sig at {hex(p)}")
        p += 4
