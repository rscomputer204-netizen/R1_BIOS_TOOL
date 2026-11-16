fpath = r'D:\SDD DATA\all bios\Bios\HP\01015fy00-388-g\dump_main.bin'
with open(fpath, 'rb') as f:
    reading = f.read()

print("len:", hex(len(reading)))
fd_idx = reading.find(b'\x5a\xa5\xf0\x0f')
print("FD at:", hex(fd_idx) if fd_idx != -1 else "None")
fpt_idx = reading.find(b'$FPT')
print("FPT at:", hex(fpt_idx) if fpt_idx != -1 else "None")
print("First 16 bytes:", reading[:16].hex())
