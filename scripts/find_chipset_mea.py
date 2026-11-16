with open(r'd:\BIOS_-TOOL\external\MEAnalyzer\MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

for line in text.splitlines():
    if "Chipset Support" in line or "msg_pt.add_row(['Chipset" in line:
        print(line[:120])
