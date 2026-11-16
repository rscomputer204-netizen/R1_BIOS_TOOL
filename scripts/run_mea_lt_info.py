import subprocess, sys

script = """
import sys, struct
sys.path.insert(0, r"d:\\BIOS_-TOOL\\external\\MEAnalyzer")
import MEA
"""
# Let's see what MEA does by running a small script that inspects MEA.
# We can run MEA with python -c and inspect
cmd = [sys.executable, r"d:\BIOS_-TOOL\external\MEAnalyzer\MEA.py", 
       r"D:\SDD DATA\all bios\Bios\HP\HP ZBook 15 G5 Mobile Workstation DA0XW2MBAG0 XW2A\orginal read no power.bin",
       "-skip", "-exit", "-dfpt"]
res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
for l in res.stdout.splitlines():
    if "Size" in l or "Data" in l or "Boot" in l:
        print(l)
