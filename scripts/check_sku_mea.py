fpath = r'D:\SDD DATA\all bios\Bios\HP\6050A3059101-MB-A01 (A1)\New folder\read 9-6-22.bin'
with open(r'd:\BIOS_-TOOL\external\MEAnalyzer\MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

# Let's search how SKU is determined in MEA
# For CSE, it uses CSE Extension 0B (FWSKUAttrib)
idx = text.find('class CSE_Ext_0B')
print(text[idx:idx+800])
