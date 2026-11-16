with open(r'd:\BIOS_-TOOL\external\MEAnalyzer\MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

for i, line in enumerate(text.splitlines()):
    if '5a' in line.lower() and 'a5' in line.lower() and 'f0' in line.lower() and '0f' in line.lower():
        print(f"Line {i+1}: {line.strip()[:100]}")
    elif 'fd_match' in line or 'fd_sig' in line or 'Descriptor' in line and 'bgn' in line:
        print(f"Line {i+1}: {line.strip()[:100]}")
