with open(r'd:\BIOS_-TOOL\external\MEAnalyzer\MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

idx = text.find('class CSE_Layout_Table_17')
idx2 = text.find('class CSE_Layout_Table_16')
print("LT 16:")
print(text[idx2:idx2+600])
print("="*50)
print("LT 17:")
print(text[idx:idx+600])
