with open(r'D:\SDD DATA\all bios\Bios\HP\10th gen_DA0X8LMB8D0 REV D\ec outside of ram 25B127DSIG.bin', 'rb') as f:
    data = f.read()

import struct, re
primary_fpt = data.find(b'$FPT')
fpt_base = primary_fpt
num_entries = struct.unpack('<I', data[primary_fpt+4:primary_fpt+8])[0]
fpt_max_end = 0
for i in range(num_entries):
    e = data[primary_fpt+32+i*32 : primary_fpt+32+(i+1)*32]
    poff, sz = struct.unpack('<II', e[8:16])
    if poff != 0xffffffff and sz != 0xffffffff:
        fpt_max_end = max(fpt_max_end, poff + sz)

print("Initial fpt_max_end:", hex(fpt_max_end))
p_end_scan = fpt_base + fpt_max_end
print("p_end_scan:", hex(p_end_scan))

while p_end_scan + 0x20 <= len(data):
    print("Checking p_end_scan:", hex(p_end_scan), data[p_end_scan:p_end_scan+8])
    if data[p_end_scan + 0x1C : p_end_scan + 0x20] == b"$MN2":
        print("Matched MN2 at", hex(p_end_scan))
        break
    elif data[p_end_scan : p_end_scan + 4] == b"$CPD":
        print("Matched CPD at", hex(p_end_scan))
        cpd_ver = data[p_end_scan + 8]
        cpd_hdr_sz = 0x10 if cpd_ver == 1 else 0x14
        cpd_num = struct.unpack("<I", data[p_end_scan + 0x04 : p_end_scan + 0x08])[0]
        print(f"cpd_ver: {cpd_ver}, num: {cpd_num}")
        raw_off, c_sz = struct.unpack("<II", data[p_end_scan + cpd_hdr_sz + 0x0C : p_end_scan + cpd_hdr_sz + 0x14])
        print(f"entry 0: raw_off: 0x{raw_off:x}, sz: 0x{c_sz:x}")
        break
    else:
        # strict cpd search
        cpd_pat_search = re.compile(br'\$CPD.\x00\x00\x00[\x01\x02]\x01[\x10\x14]', re.DOTALL)
        m_next = cpd_pat_search.search(data[p_end_scan : p_end_scan + 0x2000])
        print("cpd_pat_search match:", m_next)
        break
