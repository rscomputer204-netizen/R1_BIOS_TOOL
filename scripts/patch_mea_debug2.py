with open('external/MEAnalyzer/MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    code = f.read()

needle = "print('DEBUG_FITC:', fitc_major, fitc_minor, fitc_hotfix, fitc_build, 'fpt_hdr:', fpt_hdr.FitMajor if fpt_hdr else None);"
replacement = "print('DEBUG_FITC_OFFSET:', hex(fpt_pat_bgn), fitc_major, fitc_minor, fitc_hotfix, fitc_build);"

if needle in code:
    with open('external/MEAnalyzer/MEA.py', 'w', encoding='utf-8') as f:
        f.write(code.replace(needle, replacement))
