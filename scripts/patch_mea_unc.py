with open('external/MEAnalyzer/MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

target = 'if not fd_exist and not cse_lt_struct and reading[p_end_last:p_end_last + 0x4] != b\'$CPD\' :'
repl = 'print(\"DEBUG_CHECK_UNCHARTED:\", hex(p_end_last), not fd_exist, not cse_lt_struct); ' + target
if target in text:
    with open('external/MEAnalyzer/MEA.py', 'w', encoding='utf-8') as f:
        f.write(text.replace(target, repl))
    print('Patched MEA for uncharted debug')
