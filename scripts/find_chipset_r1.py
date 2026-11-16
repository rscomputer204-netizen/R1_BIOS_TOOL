with open(r'd:\BIOS_-TOOL\R1_CSME_Analyzer\r1_csme_parser.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'self.info["chipset"]' in l or "self.info['chipset']" in l:
        print(f"{i+1}: {l.strip()[:100]}")
