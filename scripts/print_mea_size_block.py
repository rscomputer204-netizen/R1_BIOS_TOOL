import sys
# Let's inspect MEA lines 12460-12485
with open(r'd:\BIOS_-TOOL\external\MEAnalyzer\MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

idx = text.find('if cse_lt_struct :')
print(text[idx:idx+1200])
