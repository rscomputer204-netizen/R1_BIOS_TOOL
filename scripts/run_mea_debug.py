import subprocess, sys

fpath = r'D:\SDD DATA\all bios\Bios\HP\6050A3059101-MB-A01 (A1)\New folder\read 9-6-22.bin'
res = subprocess.run([sys.executable, r"d:\BIOS_-TOOL\external\MEAnalyzer\MEA.py", fpath, "-skip", "-exit"],
                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
print(res.stdout)
