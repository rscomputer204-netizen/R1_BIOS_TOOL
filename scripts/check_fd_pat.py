import re

fpath = r'D:\SDD DATA\all bios\Bios\HP\01015fy00-388-g\dump_main.bin'
with open(fpath, 'rb') as f:
    reading = f.read()

fd_pat = re.compile(br'\x5A\xA5\xF0\x0F[\x01-\x10].{171}\xFF{16}', re.DOTALL)
m = list(fd_pat.finditer(reading))
print("MEA fd_pat match:", m)

# If fd_pat did NOT match, why?
idx = reading.find(b'\x5A\xA5\xF0\x0F')
print("5AA5F00F at:", hex(idx))
print("Bytes after 5AA5F00F:", reading[idx:idx+32].hex())
