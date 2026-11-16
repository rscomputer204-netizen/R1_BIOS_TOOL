with open(r'd:\BIOS_-TOOL\external\MEAnalyzer\MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

# Let's find where cse_lt_hdr_info is populated
idx = text.find('cse_lt_hdr_info =')
if idx == -1: idx = text.find('cse_lt_hdr_info.append')
print(text[idx-100:idx+400])
