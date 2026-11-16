with open(r'D:\SDD DATA\all bios\Bios\HP\6050A3059101-MB-A01 (A1)\New folder\read 9-6-22.bin', 'rb') as f:
    reading = f.read()

# Is there another FPT or CPD?
idx = 0x148000
while idx < len(reading):
    sig = reading[idx:idx+4]
    if sig in (b'$FPT', b'$CPD', b'$MN2', b'FTPR', b'NFTP'):
        print(f"Found {sig} at {hex(idx)}")
    idx += 0x1000
