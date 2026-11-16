import sys, struct
sys.path.insert(0, r'd:\BIOS_-TOOL')
from R1_CSME_Analyzer.r1_csme_parser import R1CSMEAnalyzer

fpath = r'D:\SDD DATA\all bios\Bios\HP\6050a2930901-mb-a01(a1)\EC16MB\read meraj.bin'
with open(fpath, 'rb') as f:
    d = f.read()

pos = 0
found = []
sig = b"$F" + b"PT"
while True:
    idx = d.find(sig, pos)
    if idx == -1: break
    found.append(idx)
    pos = idx + 4

print("Found $FPT at:", [hex(x) for x in found])
for f_idx in found:
    hdr = d[f_idx:f_idx+32]
    fit_maj, fit_min, fit_hot, fit_bld = struct.unpack('<HHHH', hdr[0x18:0x20])
    print(f"  Offset {hex(f_idx)}: FIT={fit_maj}.{fit_min}.{fit_hot}.{fit_bld}")
