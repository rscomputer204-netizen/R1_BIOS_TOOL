import sys
sys.path.insert(0, r"d:\BIOS_-TOOL\external\MEAnalyzer")
import MEA
import subprocess

cmd = [sys.executable, r"d:\BIOS_-TOOL\external\MEAnalyzer\MEA.py", r"D:\SDD DATA\all bios\Bios\LENOVO\LA-H101P REV1.0\read bin.bin", "-skip", "-exit"]
proc = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
for line in proc.stdout.splitlines():
    if "Size" in line or "Layout" in line or "0x27C" in line or "Partition" in line:
        print(line)
