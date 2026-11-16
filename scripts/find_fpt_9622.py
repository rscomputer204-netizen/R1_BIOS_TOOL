fpath = r'D:\SDD DATA\all bios\Bios\HP\6050A3059101-MB-A01 (A1)\New folder\read 9-6-22.bin'
with open(fpath, "rb") as f: data = f.read()

pos = 0
while True:
    pos = data.find(b'$FPT', pos)
    if pos == -1: break
    print(f"$FPT at {hex(pos)}")
    pos += 4
