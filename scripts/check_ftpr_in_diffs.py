import json, os

HP_DIR = r"D:\SDD DATA\all bios\Bios\HP"
with open('scripts/hp_remaining_diffs.json') as f:
    diffs = json.load(f)

for d in diffs:
    if 'chipset' in d['diffs']:
        fpath = os.path.join(HP_DIR, d['file'])
        with open(fpath, 'rb') as f:
            data = f.read()
        fpt_idx = data.find(b'$FPT')
        has_fpt = fpt_idx != -1
        has_ftpr = b'FTPR' in data[fpt_idx:fpt_idx+1024] if has_fpt else False
        print(f"{d['file'][:50]}: has_fpt={has_fpt}, has_ftpr={has_ftpr}, diff={d['diffs']['chipset']}")
