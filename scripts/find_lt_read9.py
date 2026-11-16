with open(r'D:\SDD DATA\all bios\Bios\HP\6050A3059101-MB-A01 (A1)\New folder\read 9-6-22.bin', 'rb') as f:
    data = f.read()

# Search for CSE Layout Table
for sig in (b'\x01\x62\x4F\x72', b'\xAA\x55\x78\x87', b'\x87\x78\x55\xAA'):
    pos = 0
    while True:
        pos = data.find(sig, pos)
        if pos == -1: break
        print(f"Found {sig.hex()} at {hex(pos)}")
        pos += 4
