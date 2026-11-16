with open('R1_CSME_Analyzer/r1_csme_parser.py', 'r', encoding='utf-8', errors='ignore') as f:
    for i, l in enumerate(f):
        if "bpdt" in l.lower():
            print(f"{i+1}: {l.strip()}")
