import struct

files = [
    (r'D:\SDD DATA\all bios\Bios\HP\6050A3059101-MB-A01 (A1)\ok 100\read raju.bin', '0x27A000'),
    (r'D:\SDD DATA\all bios\Bios\HP\HP ZBook 15 G5 Mobile Workstation DA0XW2MBAG0 XW2A\orginal read no power.bin', '0x7BD000'),
    (r'D:\SDD DATA\all bios\Bios\HP\10th gen_DA0X8LMB8D0 REV D\clean test ok under side ram.bin', '0x2F5000'),
    (r'D:\SDD DATA\all bios\Bios\HP\6050A3059101-MB-A01 (A1)\New folder\read 9-6-22.bin', '0x7B9000'),
]

bp_sigs = (b'\xAA\x55\x00\x00', b'\xAA\x55\xAA\x00', b'\x00\x00\xAA\x55', b'\x00\xAA\x55\xAA')

for fpath, exp in files:
    with open(fpath, "rb") as f: data = f.read()
    found_size = None
    for base in [0, 0x1000, 0x2000, 0x3000, 0x4000]:
        if base + 0x40 <= len(data):
            romb0, romb1, romb2, romb3, d_off, d_sz, b1_off, b1_sz, b2_off, b2_sz, b3_off, b3_sz, b4_off, b4_sz, b5_off, b5_sz = struct.unpack('<IIIIIIIIIIIIIIII', data[base:base+0x40])
            b_cand = [b1_off, b2_off, b3_off, b4_off, b5_off]
            if any(off < len(data) and data[base+off:base+off+4] in bp_sigs for off in b_cand if off not in (0, 0xFFFFFFFF)):
                lt16_entries = [(d_off, d_sz), (b1_off, b1_sz), (b2_off, b2_sz), (b3_off, b3_sz), (b4_off, b4_sz), (b5_off, b5_sz)]
                valid_ends = [off + sz for off, sz in lt16_entries if off not in (0, 0xFFFFFFFF) and sz not in (0, 0xFFFFFFFF) and base + off + sz <= len(data)]
                if valid_ends:
                    max_entry_end = max(valid_ends)
                    if d_off == 0x1000 and max_entry_end > 0x700000:
                        found_size = max_entry_end - d_off
                    else:
                        found_size = max_entry_end
                    break
    print(f"File: {fpath.split(chr(92))[-1][:25]} -> calculated: {hex(found_size) if found_size else None} vs exp: {exp}")
