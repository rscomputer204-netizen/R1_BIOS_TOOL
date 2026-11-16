import struct

fpath = r'D:\SDD DATA\all bios\Bios\HP\HP ZBook 15 G5 Mobile Workstation DA0XW2MBAG0 XW2A\orginal read no power.bin'
with open(fpath, "rb") as f: data = f.read()

bp_sigs = (b'\xAA\x55\x00\x00', b'\xAA\x55\xAA\x00', b'\x00\x00\xAA\x55', b'\x00\xAA\x55\xAA')

for base in [0, 0x1000, 0x2000, 0x3000, 0x4000]:
    if base + 56 <= len(data):
        sz = struct.unpack("<H", data[base + 0x10 : base + 0x12])[0]
        if sz in (0x40, 0x48):
            r0, r1, r2, r3, sz, flg, res, csum, data_off, data_sz, bp1_off, bp1_sz, bp2_off, bp2_sz, bp3_off, bp3_sz = struct.unpack("<IIIIHBBIIIIIIIII", data[base : base + 56])
            print("base:", hex(base))
            print("data_off:", hex(data_off), "data_sz:", hex(data_sz))
            print("bp1_off:", hex(bp1_off), "bp1_sz:", hex(bp1_sz))
            print("bp2_off:", hex(bp2_off), "bp2_sz:", hex(bp2_sz))
            entries = [(data_off, data_sz), (bp1_off, bp1_sz), (bp2_off, bp2_sz), (bp3_off, bp3_sz)]
            valid_ends = [base + off + s for off, s in entries if off not in (0, 0xFFFFFFFF) and s not in (0, 0xFFFFFFFF) and base + off + s <= len(data)]
            print("valid_ends:", [hex(v) for v in valid_ends])
            max_entry_end = max(valid_ends)
            print("max_entry_end:", hex(max_entry_end))
            print("max_entry_end - base:", hex(max_entry_end - base))
