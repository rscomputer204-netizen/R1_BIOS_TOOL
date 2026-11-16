import sys
fpath = r'D:\SDD DATA\all bios\Bios\HP\6050A3059101-MB-A01 (A1)\New folder\read 9-6-22.bin'

# Let's inspect where sku_init comes from in MEA.py
with open(r'd:\BIOS_-TOOL\external\MEAnalyzer\MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

for i, line in enumerate(text.splitlines()):
    if "sku_init =" in line:
        print(f"{i+1}: {line.strip()[:100]}")
