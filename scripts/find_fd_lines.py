with open(r'd:\BIOS_-TOOL\R1_CSME_Analyzer\r1_csme_parser.py') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if "me_fd_start" in l or "me_fd_end" in l or "Descriptor" in l and "def " in l:
        print(f"Line {i+1}: {l.strip()[:100]}")
