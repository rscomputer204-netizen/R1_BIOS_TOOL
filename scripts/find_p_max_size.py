with open('external/MEAnalyzer/MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    for i, l in enumerate(f):
        if "p_max_size" in l:
            print(f"{i+1}: {l.strip()}")
