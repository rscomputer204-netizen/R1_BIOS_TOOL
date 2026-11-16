import subprocess

cmd = ['python', 'external/MEAnalyzer/MEA.py', '-skip', r'D:\SDD DATA\all bios\Bios\HP\6050a2930901-mb-a01(a1)\EC16MB\read meraj.bin']
p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, text=True)
out, err = p.communicate(input="\n\n\n", timeout=10)
for line in out.splitlines():
    if 'DEBUG' in line:
        print(line)
