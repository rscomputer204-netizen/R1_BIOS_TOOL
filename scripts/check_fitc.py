import struct

with open(r'D:\SDD DATA\all bios\Bios\HP\6050a2930901-mb-a01(a1)\EC16MB\read meraj.bin', 'rb') as f:
    d = f.read()

fpt_idx = d.find(b'$FPT')
print("$FPT at:", hex(fpt_idx))
if fpt_idx != -1:
    hdr = d[fpt_idx:fpt_idx+32]
    # Header format:
    # Tag (4), NumEntries (4), HeaderVer (1), EntryVer (1), HeaderLen (1), Checksum (1),
    # Ticks (2), Flags (2), FitMajor (2), FitMinor (2), FitHotfix (2), FitBuild (2)
    # Let's inspect bytes 0x10 to 0x20
    fit_maj, fit_min, fit_hot, fit_bld = struct.unpack('<HHHH', hdr[0x18:0x20])
    print(f"FIT in $FPT: {fit_maj}.{fit_min}.{fit_hot}.{fit_bld}")
