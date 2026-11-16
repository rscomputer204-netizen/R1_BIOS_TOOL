with open(r'D:\SDD DATA\all bios\Bios\HP\01015fy00-388-g\dump_main.bin', 'rb') as f:
    d = f.read()

print("File size:", hex(len(d)))
print("First 16 bytes:", d[:16])
print("Offset 0x10:", d[0x10:0x20])
fd_sig = d[0x10:0x14]
print("FD sig at 0x10:", fd_sig.hex())
has_fpt = b'$FPT' in d
print("Has $FPT anywhere:", has_fpt)
