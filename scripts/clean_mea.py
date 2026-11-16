with open('external/MEAnalyzer/MEA.py', 'r', encoding='utf-8', errors='ignore') as f:
    code = f.read()

needle = "print('DEBUG_FITC_OFFSET:', hex(fpt_pat_bgn), fitc_major, fitc_minor, fitc_hotfix, fitc_build);"
if needle in code:
    with open('external/MEAnalyzer/MEA.py', 'w', encoding='utf-8') as f:
        f.write(code.replace(needle, ""))
    print("Cleaned MEA.py")
else:
    print("Needle not found")
