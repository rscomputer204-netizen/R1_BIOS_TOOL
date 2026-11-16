with open(r'D:\SDD DATA\all bios\Bios\HP\6050a2930901-mb-a01(a1)\EC16MB\read meraj.bin', 'rb') as f:
    d = f.read()

import re
fpt_pat = re.compile(br'\$FPT(?:\x20|\x21)(?:\x00|\x10|\x20|\x30|\x40|\x50|\x60|\x70|\x80|\x90|\xA0|\xB0|\xC0|\xD0|\xE0|\xF0)', re.DOTALL)
for m in fpt_pat.finditer(d):
    print("Valid $FPT match at:", hex(m.start()))
    import struct
    hdr = d[m.start():m.start()+32]
    fit_maj, fit_min, fit_hot, fit_bld = struct.unpack('<HHHH', hdr[0x18:0x20])
    print(f"  FIT: {fit_maj}.{fit_min}.{fit_hot}.{fit_bld}")
