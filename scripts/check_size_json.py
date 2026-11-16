with open(r'd:\BIOS_-TOOL\external\MEAnalyzer\MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

# Search for "Size" in json output
start = 0
while True:
    idx = text.find("'Size'", start)
    if idx == -1: break
    print(text[idx-50:idx+80])
    start = idx + 10
