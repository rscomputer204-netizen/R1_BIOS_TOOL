with open('external/MEAnalyzer/MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'class CPD_Entry' in l:
        for j in range(i, i+25):
            print(f"{j+1}: {lines[j].rstrip()}")
