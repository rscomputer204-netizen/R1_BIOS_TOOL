import sys, subprocess

fpath = r'D:\SDD DATA\all bios\Bios\HP\01015fy00-388-g\dump_main.bin'
subprocess.run([sys.executable, r"d:\BIOS_-TOOL\external\MEAnalyzer\MEA.py", fpath, "-skip", "-exit"])
