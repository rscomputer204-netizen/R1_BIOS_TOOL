import sys, subprocess

code = """
import sys
sys.path.insert(0, r"d:\\BIOS_-TOOL\\external\\MEAnalyzer")
import MEA
"""

# Let's inspect MEA variables directly by patching MEA temporarily to print variables
with open(r"d:\BIOS_-TOOL\external\MEAnalyzer\MEA.py", "r", encoding="utf-8") as f:
    text = f.read()

# Find line 12480 and add print
target = "if (cse_lt_struct and not rgn_exist) or (rgn_exist and p_end_last != p_max_size) :"
replacement = """if (cse_lt_struct and not rgn_exist) or (rgn_exist and p_end_last != p_max_size) :
        if cse_lt_struct:
            print(f"DEBUG_CALC: file={os.path.basename(file_in)} cse_lt_size={hex(cse_lt_size)} cse_lt_dp_size={hex(cse_lt_dp_size)} cse_lt_bp_size={hex(cse_lt_bp_size)} p_end_last_before={hex(p_end_last)} fpt_start={hex(fpt_start)}")
"""
patched = text.replace(target, replacement, 1)
with open(r"d:\BIOS_-TOOL\external\MEAnalyzer\MEA_test_calc.py", "w", encoding="utf-8") as f:
    f.write(patched)

for fpath in [
    r'D:\SDD DATA\all bios\Bios\HP\HP ZBook 15 G5 Mobile Workstation DA0XW2MBAG0 XW2A\orginal read no power.bin',
    r'D:\SDD DATA\all bios\Bios\HP\6050A3059101-MB-A01 (A1)\New folder\read 9-6-22.bin',
    r'D:\SDD DATA\all bios\Bios\HP\10th gen_DA0X8LMB8D0 REV D\clean test ok under side ram.bin',
    r'D:\SDD DATA\all bios\Bios\HP\6050A3059101-MB-A01 (A1)\ok 100\read raju.bin'
]:
    res = subprocess.run([sys.executable, r"d:\BIOS_-TOOL\external\MEAnalyzer\MEA_test_calc.py", fpath, "-skip", "-exit"],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    for l in res.stdout.splitlines():
        if "DEBUG_CALC:" in l:
            print(l)
