import subprocess

cmd = ['python', 'external/MEAnalyzer/MEA.py', '-dfpt', r'D:\SDD DATA\all bios\Bios\HP\17817-1\CSME 11.8 Repository r34\CSME 11.8 Repository r34\11.8.50.3399_COR_H_DA_PRD_RGN.bin']
p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
out, err = p.communicate(input='\n\n\n')
print(out)
