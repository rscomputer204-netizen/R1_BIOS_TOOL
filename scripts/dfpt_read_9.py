import subprocess

cmd = ['python', 'external/MEAnalyzer/MEA.py', '-skip', '-dfpt', r'D:\SDD DATA\all bios\Bios\HP\6050A3059101-MB-A01 (A1)\New folder\read 9-6-22.bin']
p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, text=True)
out, err = p.communicate(input="\n\n\n", timeout=10)
print(out)
