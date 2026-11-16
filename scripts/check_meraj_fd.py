with open(r'D:\SDD DATA\all bios\Bios\HP\6050a2930901-mb-a01(a1)\EC16MB\read meraj.bin', 'rb') as f:
    reading = f.read()

# Let's check FD in read meraj.bin:
flreg1 = int.from_bytes(reading[0x44:0x48], 'little')
base = (flreg1 & 0x1FFF) << 12
limit = (((flreg1 >> 16) & 0x1FFF) << 12) | 0xFFF
print("FD base:", hex(base), "limit:", hex(limit))
# Where is FPT relative to base?
# If base is 0x3000, then base + 0x10 is 0x3010
fpt_at_base = reading.find(b'$FPT', base)
print("FPT at base:", hex(fpt_at_base) if fpt_at_base != -1 else "None")
