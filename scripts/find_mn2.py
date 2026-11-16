with open(r'D:\SDD DATA\all bios\Bios\HP\01015fy00-388-g\dump_main.bin', 'rb') as f:
    d = f.read()

idx = 0
while True:
    idx = d.find(b'$MN2', idx)
    if idx == -1: break
    print("$MN2 at:", hex(idx))
    idx += 4
