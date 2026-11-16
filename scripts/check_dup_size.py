with open(r'd:\BIOS_-TOOL\external\MEAnalyzer\MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

for i in range(12450, 12466):
    print(f"{i+1}: {lines[i].rstrip()}")
