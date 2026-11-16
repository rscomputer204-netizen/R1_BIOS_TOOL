with open(r'd:\BIOS_-TOOL\external\MEAnalyzer\MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if "fpt_start =" in l or "fpt_start=" in l:
        print(f"{i+1}: {l.strip()[:100]}")
