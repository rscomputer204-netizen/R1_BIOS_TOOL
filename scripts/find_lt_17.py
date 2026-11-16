with open(r'd:\BIOS_-TOOL\external\MEAnalyzer\MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

idx = text.find('class CSE_Layout_Table_17')
print(text[idx:idx+1500])
