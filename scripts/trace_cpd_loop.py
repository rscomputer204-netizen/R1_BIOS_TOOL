import struct

path = r'D:\SDD DATA\all bios\Bios\HP\17817-1\CSME 11.8 Repository r34\CSME 11.8 Repository r34\11.8.50.3399_COR_H_DA_PRD_RGN.bin'
with open(path, 'rb') as f:
    data = f.read()

def get_cpd_size(data, offset):
    if offset + 0x10 > len(data): return 0
    cpd_ver = data[offset + 8]
    cpd_hdr_sz = 0x10 if cpd_ver == 1 else 0x14
    num_modules = struct.unpack('<I', data[offset+4:offset+8])[0]
    
    # 1. cpd_end_last
    cpd_offset_last = 0
    cpd_end_last = 0
    for i in range(num_modules):
        e_off = offset + cpd_hdr_sz + i * 0x18
        if e_off + 24 > len(data): break
        raw_off, sz = struct.unpack('<II', data[e_off+12:e_off+20])
        c_off = raw_off & 0x01FFFFFF
        if c_off > cpd_offset_last:
            cpd_offset_last = c_off
            cpd_end_last = c_off + sz
            
    # 2. cse_ext_part_size from manifest
    mn2_start = offset + cpd_hdr_sz + num_modules * 0x18
    cse_ext_part_size = 0
    if mn2_start + 16 <= len(data):
        # check if MN2
        mn2_tag = data[mn2_start+0x14:mn2_start+0x18] # wait, where is MN2 tag or header length?
        # In MN2, header length is at mn2_start + 4
        hdr_len = struct.unpack('<I', data[mn2_start+4:mn2_start+8])[0] * 4
        curr = mn2_start + hdr_len
        for _ in range(10):
            if curr + 8 > len(data): break
            ext_type, ext_len = struct.unpack('<II', data[curr:curr+8])
            if ext_type in (0x3, 0x16):
                cse_ext_part_size = struct.unpack('<I', data[curr+0xc:curr+0x10])[0]
                break
            if ext_len == 0: break
            curr += ext_len
            
    return max(cse_ext_part_size, cpd_end_last)

p_end_last = 0x634000
while p_end_last < len(data) and data[p_end_last:p_end_last+4] == b'$CPD':
    part_name = data[p_end_last+0xc:p_end_last+0x10].rstrip(b'\x00')
    sz = get_cpd_size(data, p_end_last)
    print(f"CPD at 0x{p_end_last:x}: {part_name}, sz=0x{sz:x}")
    if sz == 0: break
    p_end_last += sz

print(f"Final p_end_last: 0x{p_end_last:x}")
