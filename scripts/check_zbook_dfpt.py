import subprocess, sys

fpath = r'D:\SDD DATA\all bios\Bios\HP\HP ZBook 15 G5 Mobile Workstation DA0XW2MBAG0 XW2A\orginal read no power.bin'
res = subprocess.run([sys.executable, r"d:\BIOS_-TOOL\external\MEAnalyzer\MEA.py", fpath, "-skip", "-exit", "-dfpt"],
                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
print(res.stdout)
