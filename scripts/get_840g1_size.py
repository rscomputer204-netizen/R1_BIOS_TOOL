import subprocess

cmd = ['python', 'external/MEAnalyzer/MEA.py', '-skip', r'D:\SDD DATA\all bios\Bios\HP\840 g1\25Q128_Clear me.bin']
p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, text=True)
out, err = p.communicate(input="\n\n\n", timeout=10)
for line in out.splitlines():
    if 'DEBUG_SIZE' in line:
        print(line)
