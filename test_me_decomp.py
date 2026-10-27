import os
from fit_automator import execute_fit_decompile
def cb(*args): print(args)
me_file = r'C:\Users\R1 LAB\Desktop\BIOS_-TOOL\15.0.55.2751_CON_LP_B_PRD_EXTR_0DB49713\15.0.55.2751_CON_LP_B_PRD_EXTR_0DB49713.bin'
res = execute_fit_decompile(me_file, '15.0', r'C:\Users\R1 LAB\Desktop\BIOS_-TOOL\TESTING_AREA\decomp_me_test', cb)
print('RESULT:', res)
