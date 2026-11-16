with open('external/MEAnalyzer/MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

idx = text.find('def get_manifest')
print(text[idx:idx+600])
