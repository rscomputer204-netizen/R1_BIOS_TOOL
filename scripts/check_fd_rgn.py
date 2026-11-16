# Let's inspect fd_anl_rgn for this file:
with open(r'd:\BIOS_-TOOL\external\MEAnalyzer\MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

# Let's check how fd_me_rgn_exist is set in MEA
start_fd = text.find('def fd_anl_rgn')
print(text[start_fd:start_fd+1500])
