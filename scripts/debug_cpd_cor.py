import struct

path = r'D:\SDD DATA\all bios\Bios\HP\17817-1\CSME 11.8 Repository r34\CSME 11.8 Repository r34\11.8.50.3399_COR_H_DA_PRD_RGN.bin'
with open(path, 'rb') as f:
    data = f.read()

print(f"File size: 0x{len(data):x}")

# Let's see FPT and Uncharted
p_end_last = 0x634000
while p_end_last < len(data) and data[p_end_last:p_end_last+4] == b'$CPD':
    cpd_ver = data[p_end_last + 8]
    cpd_hdr_sz = 0x10 if cpd_ver == 1 else 0x14
    num_modules = struct.unpack('<I', data[p_end_last+4:p_end_last+8])[0]
    part_name = data[p_end_last+0xc:p_end_last+0x10]
    print(f"CPD at 0x{p_end_last:x}: ver={cpd_ver}, num_modules={num_modules}, name={part_name}")
    
    cpd_offset_last = 0
    cpd_end_last = 0
    for i in range(num_modules):
        e_off = p_end_last + cpd_hdr_sz + i * 0x18
        name = data[e_off:e_off+12].rstrip(b'\x00')
        raw_off, sz = struct.unpack('<II', data[e_off+12:e_off+20])
        c_off = raw_off & 0x01FFFFFF
        if c_off > cpd_offset_last:
            cpd_offset_last = c_off
            cpd_end_last = c_off + sz
        print(f"  Entry {i}: {name} raw=0x{raw_off:x} off=0x{c_off:x} sz=0x{sz:x} (end=0x{c_off+sz:x})")
    
    print(f"  CPD total end relative: 0x{cpd_end_last:x}")
    p_end_last += cpd_end_last
    print(f"  New p_end_last: 0x{p_end_last:x}")

print(f"Final calculated size: 0x{p_end_last:x}")
