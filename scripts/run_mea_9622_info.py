import subprocess, sys

cmd = [sys.executable, r"d:\BIOS_-TOOL\external\MEAnalyzer\MEA.py", 
       r"D:\SDD DATA\all bios\Bios\HP\6050A3059101-MB-A01 (A1)\New folder\read 9-6-22.bin",
       "-skip", "-exit", "-dfpt"]
res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
for l in res.stdout.splitlines():
    if "Size" in l or "Data" in l or "Boot" in l:
        print(l)
