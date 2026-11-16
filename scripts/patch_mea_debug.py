with open('external/MEAnalyzer/MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

target = "print('DEBUG_SIZE:', hex(eng_fw_end), 'p_end_last:', hex(p_end_last), 'fpt_start:', hex(fpt_start))"
repl = target + "; print('LT_INFO:', cse_lt_struct is not None, hex(cse_lt_dp_size) if cse_lt_struct else '', hex(cse_lt_bp_size) if cse_lt_struct else '', cse_lt_hdr_info if cse_lt_struct else '')"
if target in text:
    text = text.replace(target, repl)
    with open('external/MEAnalyzer/MEA.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print('Replaced!')
else:
    print('Target not found')
