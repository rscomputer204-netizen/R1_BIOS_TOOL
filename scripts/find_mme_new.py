with open(r'd:\BIOS_-TOOL\external\MEAnalyzer\MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

idx = text.find('class MME_Header_New')
print(text[idx:idx+800])
