with open('external/MEAnalyzer/MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
for m in re.finditer(r'(\$CPD|cpd_header|cpd_entry|uncharted)', text, re.IGNORECASE):
    idx = m.start()
    line_start = text.rfind('\n', 0, idx)
    line_end = text.find('\n', idx)
    print(f"Line: {text[:idx].count(chr(10))+1}: {text[line_start:line_end].strip()[:120]}")
