with open('external/MEAnalyzer/MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'sku =' in l and 13000 <= i <= 13500:
        print(f"{i+1}: {l.strip()}")
