import sys, os
sys.path.insert(0, r'd:\BIOS_-TOOL\external\MEAnalyzer')
import MEA

# Let's inspect MEA on read meraj.bin
fpath = r'D:\SDD DATA\all bios\Bios\HP\6050a2930901-mb-a01(a1)\EC16MB\read meraj.bin'
# MEA command line parameters
sys.argv = ['MEA.py', fpath]
# Let's run MEA.mea_analyze or see how MEA is called
print("Running MEA directly...")
