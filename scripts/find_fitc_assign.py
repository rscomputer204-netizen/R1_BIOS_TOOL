with open('external/MEAnalyzer/MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    for i, l in enumerate(f):
        if "fitc_ver_found" in l or "fitc_major" in l:
            print(f"{i+1}: {l.strip()}")
