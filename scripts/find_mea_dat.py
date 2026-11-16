import json

# Check MEA.dat for 12.0.49.1534
with open('external/MEAnalyzer/MEA.dat', 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        if '12.0.49.1534' in line:
            print(line.strip())
