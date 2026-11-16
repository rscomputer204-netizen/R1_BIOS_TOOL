with open(r'd:\BIOS_-TOOL\external\MEAnalyzer\MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if "bpdt_part_all" in l and ("max" in l or "end" in l or "size" in l):
        print(f"{i+1}: {l.strip()[:100]}")
