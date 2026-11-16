import struct

fpath = r'D:\SDD DATA\all bios\Bios\HP\6050A3059101-MB-A01 (A1)\ok 100\read raju.bin'
with open(fpath, 'rb') as f:
    reading = f.read()

# Let's search for 0x27A000 (bytes: 00 a0 27 00)
target = struct.pack('<I', 0x27A000)
pos = 0
while True:
    pos = reading.find(target, pos)
    if pos == -1: break
    print("Found 0x27A000 at:", hex(pos))
    pos += 4

# Also 0x279000
target2 = struct.pack('<I', 0x279000)
pos = 0
while True:
    pos = reading.find(target2, pos)
    if pos == -1: break
    print("Found 0x279000 at:", hex(pos))
    pos += 4
