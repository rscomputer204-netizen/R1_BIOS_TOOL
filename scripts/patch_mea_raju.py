import sys
sys.path.insert(0, r"d:\BIOS_-TOOL\external\MEAnalyzer")

# Let's read MEA.py and find where 0x27A000 comes from
# In MEA.py, we can print local variables right before printing msg_pt
with open(r"d:\BIOS_-TOOL\external\MEAnalyzer\MEA.py", "r", encoding="utf-8") as f:
    code = f.read()

# Insert print before line 13730
idx = code.find("if rgn_exist or cse_lt_struct")
patch = """
    print('DEBUG MEA: rgn_exist=', rgn_exist, 'cse_lt_struct=', bool(cse_lt_struct), 'eng_fw_end=', hex(eng_fw_end))
    if cse_lt_struct:
        print('DEBUG MEA: cse_lt_part_all=', cse_lt_part_all)
        print('DEBUG MEA: p_end_last=', hex(p_end_last))
"""
new_code = code[:idx] + patch + code[idx:]

with open(r"d:\BIOS_-TOOL\external\MEAnalyzer\MEA_debug.py", "w", encoding="utf-8") as f:
    f.write(new_code)

import subprocess
res = subprocess.run([sys.executable, r"d:\BIOS_-TOOL\external\MEAnalyzer\MEA_debug.py", 
                      r'D:\SDD DATA\all bios\Bios\HP\6050A3059101-MB-A01 (A1)\ok 100\read raju.bin',
                      '-skip', '-exit'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
for line in res.stdout.splitlines():
    if "DEBUG MEA:" in line:
        print(line)
