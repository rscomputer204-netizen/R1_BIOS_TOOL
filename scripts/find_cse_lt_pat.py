fpath = r'D:\SDD DATA\all bios\Bios\HP\6050A3059101-MB-A01 (A1)\ok 100\read raju.bin'
with open(fpath, 'rb') as f:
    reading = f.read()

# Let's search how MEA finds cse_lt_struct
# In MEA, it searches for cse_lt_pat
# Let's check MEA.py for cse_lt_pat
with open(r'd:\BIOS_-TOOL\external\MEAnalyzer\MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

for line in text.splitlines():
    if "cse_lt_pat =" in line:
        print(line)
