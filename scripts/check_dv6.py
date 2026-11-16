import subprocess, sys

fpath = r'D:\SDD DATA\all bios\Bios\HP\dv6 DA0LX6MB6H1 REV.H\ok clean main.bin'
res = subprocess.run([sys.executable, r"d:\BIOS_-TOOL\external\MEAnalyzer\MEA.py", fpath, "-skip", "-exit", "-dfpt"],
                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
print(res.stdout)
