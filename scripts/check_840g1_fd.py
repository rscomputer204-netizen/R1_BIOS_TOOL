with open(r'D:\SDD DATA\all bios\Bios\HP\840 g1\25Q128_Clear me.bin', 'rb') as f:
    reading = f.read()

flreg1 = int.from_bytes(reading[0x44:0x48], 'little')
base = (flreg1 & 0x1FFF) << 12
limit = (((flreg1 >> 16) & 0x1FFF) << 12) | 0xFFF
size = limit - base + 1
print("FD ME base:", hex(base), "limit:", hex(limit), "size:", hex(size))
