import subprocess
proc = subprocess.Popen(['python', 'external/MEAnalyzer/MEA.py', r'D:\SDD DATA\all bios\Bios\HP\10th gen_DA0X8LMB8D0 REV D\ec outside of ram 25B127DSIG.bin'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
out, err = proc.communicate(input='\n\n\n')
print(out)
