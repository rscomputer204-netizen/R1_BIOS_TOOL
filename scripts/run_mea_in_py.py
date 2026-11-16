import sys, os

# Import MEA directly as module
sys.path.insert(0, r"d:\BIOS_-TOOL\external\MEAnalyzer")
old_argv = sys.argv
sys.argv = ["MEA.py", r"D:\SDD DATA\all bios\Bios\LENOVO\LA-H101P REV1.0\read bin.bin", "-skip", "-exit", "-json"]
import MEA
MEA.mea_main()
