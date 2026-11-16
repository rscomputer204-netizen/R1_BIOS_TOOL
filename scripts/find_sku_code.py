with open(r'd:\BIOS_-TOOL\external\MEAnalyzer\MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

# Let's search for "sku = " in MEA.py
for i, line in enumerate(text.splitlines()):
    if "sku =" in line or "sku_result =" in line:
        print(f"{i+1}: {line.strip()[:100]}")
