with open('external/MEAnalyzer/MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if "fw_type = 'Update'" in l or 'fw_type = "Update"' in l:
        print(f"Line {i+1}:")
        for j in range(max(0, i-10), min(len(lines), i+5)):
            print(f"  {j+1}: {lines[j].rstrip()}")
