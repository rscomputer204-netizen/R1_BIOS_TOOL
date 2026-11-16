with open(r'd:\BIOS_-TOOL\external\MEAnalyzer\MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if "cse_lt_" in l and ("re.compile" in l or "search" in l or "find" in l):
        print(f"{i+1}: {l.strip()[:100]}")
