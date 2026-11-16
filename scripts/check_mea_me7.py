with open(r'd:\BIOS_-TOOL\external\MEAnalyzer\MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

# Let's search where $MAN or $MN2 or ME 7 is found without $FPT
# Let's search for "7.1.52.1176" in MEA.py or how MEA analyzes ME 7
for line in text.splitlines():
    if "7.1.52.1176" in line:
        print("Found version:", line)
