with open(r'D:\SDD DATA\all bios\Bios\HP\6050a2930901-mb-a01(a1)\EC16MB\read meraj.bin', 'rb') as f:
    d = f.read()

pos = 0
while True:
    pos = d.find(b'$FPT', pos)
    if pos == -1:
        break
    print(f"Found $FPT at {hex(pos)}: {d[pos:pos+32].hex()}")
    pos += 4
