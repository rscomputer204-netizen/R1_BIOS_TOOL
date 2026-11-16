with open('external/MEAnalyzer/MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if "platform = 'NaN'" in l or "platform = " in l and "pch_init_final" in l:
        print(f"{i+1}: {l.strip()}")
