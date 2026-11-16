with open(r'D:\SDD DATA\all bios\Bios\HP\6050a2930901-mb-a01(a1)\EC16MB\read meraj.bin', 'rb') as f:
    reading = f.read()

hdr_bytes = reading[0x635000:0x635020]
print("Offset 0x635000:")
for i in range(0, 32, 2):
    val = int.from_bytes(hdr_bytes[i:i+2], 'little')
    print(f"  +{hex(i)}: {hex(val)} ({val})")
