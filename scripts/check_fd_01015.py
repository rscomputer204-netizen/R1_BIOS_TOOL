import sys
sys.path.insert(0, r"d:\BIOS_-TOOL\external\MEAnalyzer")
import MEA

fpath = r'D:\SDD DATA\all bios\Bios\HP\01015fy00-388-g\dump_main.bin'
with open(fpath, 'rb') as f:
    reading = f.read()

# Let's inspect Flash Descriptor in MEA
# How does MEA detect FD?
print("len:", hex(len(reading)))
fd_match = reading[:4] == b'\x5a\xa5\xf0\x0f'
print("FD match at 0:", fd_match)
# Does reading contain FD signature anywhere?
fd_idx = reading.find(b'\x5a\xa5\xf0\x0f')
print("FD signature anywhere:", hex(fd_idx) if fd_idx != -1 else "No")
