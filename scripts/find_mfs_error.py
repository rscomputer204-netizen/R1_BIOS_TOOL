with open('external/MEAnalyzer/MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    for i, l in enumerate(f):
        if "mfs_state = 'Error'" in l or "mfs_state = " in l:
            print(f"{i+1}: {l.strip()}")
