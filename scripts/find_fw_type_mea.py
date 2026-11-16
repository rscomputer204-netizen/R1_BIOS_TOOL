import sys, os
sys.path.insert(0, r"d:\BIOS_-TOOL\external\MEAnalyzer")

fpath = r'D:\SDD DATA\all bios\Bios\HP\01015fy00-388-g\dump_main.bin'

# Let's inspect where in MEA.py fw_type is assigned
# We can search MEA.py for all occurrences of "fw_type ="
with open(r"d:\BIOS_-TOOL\external\MEAnalyzer\MEA.py", "r", encoding="utf-8", errors="ignore") as f:
    mea_lines = f.readlines()

for idx, line in enumerate(mea_lines):
    if "fw_type =" in line:
        print(f"Line {idx+1}: {line.strip()}")
