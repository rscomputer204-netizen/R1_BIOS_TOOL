with open('external/MEAnalyzer/MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

idx = text.find('class MN2_Manifest_R0')
print(text[idx:idx+600])
