with open(r'd:\BIOS_-TOOL\external\MEAnalyzer\MEA.dat', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

for line in text.splitlines():
    if "12.0.49.1534" in line:
        print(line)
