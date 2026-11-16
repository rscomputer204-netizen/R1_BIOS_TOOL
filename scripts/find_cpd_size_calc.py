with open('external/MEAnalyzer/MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'def cpd_size_calc' in l:
        for j in range(i, i+30):
            print(f"{j+1}: {lines[j].rstrip()}")
