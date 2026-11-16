with open("external/MEAnalyzer/MEA.py", "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()
for j in range(12300, 12370):
    print(f"{j+1}: {lines[j].rstrip()}")
