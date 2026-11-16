with open('external/MEAnalyzer/MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    for i, l in enumerate(f):
        if 'cse_lt_struct' in l and ('=' in l or 'if' in l):
            print(f"{i+1}: {l.strip()}")
