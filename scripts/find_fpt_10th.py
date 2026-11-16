with open(r'D:\SDD DATA\all bios\Bios\HP\10th gen_DA0X8LMB8D0 REV D\clean test ok under side ram.bin', 'rb') as f:
    data = f.read()

idx = 0
while True:
    idx = data.find(b'$FPT', idx)
    if idx == -1: break
    print(f"FPT at 0x{idx:x}")
    idx += 4

# Let's also see layout table
idx = 0
while True:
    idx = data.find(b'\xaa\x55', idx)
    if idx == -1: break
    print(f"BPDT or LT at 0x{idx:x}: {data[idx:idx+16].hex()}")
    idx += 2
