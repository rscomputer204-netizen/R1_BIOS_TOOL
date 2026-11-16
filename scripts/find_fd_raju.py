fpath = r'D:\SDD DATA\all bios\Bios\HP\6050A3059101-MB-A01 (A1)\ok 100\read raju.bin'
with open(fpath, 'rb') as f:
    data = f.read()

pos = 0
while True:
    pos = data.find(b'\x5a\xa5\xf0\x0f', pos)
    if pos == -1: break
    print("Found FD sig at:", hex(pos))
    pos += 4
