with open("external/MEAnalyzer/MEA.py", "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()
for i, l in enumerate(lines):
    if "class MN2_Manifest_R0" in l:
        for j in range(i, min(len(lines), i+30)):
            print(f"{j+1}: {lines[j].rstrip()}")
        break
