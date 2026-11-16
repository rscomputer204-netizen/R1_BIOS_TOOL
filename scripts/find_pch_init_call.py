with open('external/MEAnalyzer/MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'pch_init_anl(' in l:
        print(f"{i+1}: {l.strip()}")
