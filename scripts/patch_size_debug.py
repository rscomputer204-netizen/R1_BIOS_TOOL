with open('external/MEAnalyzer/MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    code = f.read()

needle = "msg_pt.add_row(['Size', '0x%X' % eng_fw_end])"
replacement = "print('DEBUG_SIZE:', hex(eng_fw_end), 'p_end_last:', hex(p_end_last), 'fpt_start:', hex(fpt_start)); " + needle

with open('external/MEAnalyzer/MEA.py', 'w', encoding='utf-8') as f:
    f.write(code.replace(needle, replacement))
