import sys
fpath = r'D:\SDD DATA\all bios\Bios\HP\HP ZBook 15 G5 Mobile Workstation DA0XW2MBAG0 XW2A\orginal read no power.bin'

# Run MEA and inspect
sys.argv = ['MEA.py', fpath, '-skip', '-exit']
sys.path.insert(0, r"d:\BIOS_-TOOL\external\MEAnalyzer")
import MEA
