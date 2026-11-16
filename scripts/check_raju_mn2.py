fpath = r'D:\SDD DATA\all bios\Bios\HP\6050A3059101-MB-A01 (A1)\ok 100\read raju.bin'
with open(fpath, 'rb') as f:
    reading = f.read()

# Search for $MN2 or $CPD
pos = 0
while True:
    pos = reading.find(b'$MN2', pos)
    if pos == -1: break
    print("Found $MN2 at:", hex(pos))
    pos += 4

pos = 0
while True:
    pos = reading.find(b'$CPD', pos)
    if pos == -1: break
    print("Found $CPD at:", hex(pos))
    pos += 4
