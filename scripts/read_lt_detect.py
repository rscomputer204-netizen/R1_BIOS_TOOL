with open('external/MEAnalyzer/MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

for i in range(11515, 11540):
    print(f"{i+1}: {lines[i].rstrip()}")
