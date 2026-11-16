with open('external/MEAnalyzer/MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if "Chipset" in l and "add_row" in l:
        print(f"--- Line {i+1} ---")
        for j in range(max(0, i-15), min(len(lines), i+15)):
            print(f"{j+1}: {lines[j].rstrip()}")
