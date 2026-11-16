with open(r'd:\BIOS_-TOOL\external\MEAnalyzer\MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

fpath = r'D:\SDD DATA\all bios\Bios\HP\01015fy00-388-g\dump_main.bin'
with open(fpath, 'rb') as f:
    reading = f.read()

# Let's see what fpt matches MEA finds
import re
fpt_matches_init = [m for m in re.compile(b'\$FPT').finditer(reading)]
print("fpt_matches_init:", fpt_matches_init)

# Check if MEA found an update header or something
# Let's search MEA.py for what happens before line 12535
