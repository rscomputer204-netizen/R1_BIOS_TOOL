fpath = r'D:\SDD DATA\all bios\Bios\HP\6050A3059101-MB-A01 (A1)\ok 100\read raju.bin'

# Let's inspect MEA execution by importing MEA with sys.argv
import sys
sys.argv = ['MEA.py', fpath, '-skip', '-exit', '-json']
sys.path.insert(0, r"d:\BIOS_-TOOL\external\MEAnalyzer")
import MEA
