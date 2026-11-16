with open('external/MEAnalyzer/MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'cse_lt_dp_size' in l or 'cse_lt_bp_size' in l:
        print(f"Line {i+1}: {l.strip()[:100]}")
