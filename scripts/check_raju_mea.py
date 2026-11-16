import subprocess, sys

fpath = r'D:\SDD DATA\all bios\Bios\HP\6050A3059101-MB-A01 (A1)\ok 100\read raju.bin'
res = subprocess.run([sys.executable, r"d:\BIOS_-TOOL\external\MEAnalyzer\MEA.py", fpath, "-skip", "-exit"],
                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
print(res.stdout)
