import subprocess, sys

res = subprocess.run([sys.executable, r"d:\BIOS_-TOOL\external\MEAnalyzer\MEA_debug.py", 
                      r'D:\SDD DATA\all bios\Bios\HP\6050A3059101-MB-A01 (A1)\ok 100\read raju.bin',
                      '-skip', '-exit'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
print("STDOUT len:", len(res.stdout))
print("STDERR:", res.stderr)
for l in res.stdout.splitlines()[-20:]:
    print(l)
