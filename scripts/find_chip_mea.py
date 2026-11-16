with open('external/MEAnalyzer/MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'CNP/CMP-LP' in l:
        print(f"Line {i+1}: {l.strip()[:100]}")
