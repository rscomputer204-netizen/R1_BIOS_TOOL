with open('external/MEAnalyzer/MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    for i, l in enumerate(f):
        if "bpdt_pat =" in l or "bpdt_match =" in l:
            print(f"{i+1}: {l.strip()}")
