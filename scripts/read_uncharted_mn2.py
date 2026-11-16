with open('external/MEAnalyzer/MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

for i in range(12307, 12342):
    print(f"{i+1}: {lines[i].rstrip()}")
