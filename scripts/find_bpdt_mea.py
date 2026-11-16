fpath = r'D:\SDD DATA\all bios\Bios\HP\6050A3059101-MB-A01 (A1)\ok 100\read raju.bin'

with open(r'd:\BIOS_-TOOL\external\MEAnalyzer\MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

# Let's search how BPDT is parsed in MEA
# Search for bpdt_pat or bpdt_part_all
for line in text.splitlines():
    if "bpdt_part_all" in line and "=" in line:
        print(line[:100])
