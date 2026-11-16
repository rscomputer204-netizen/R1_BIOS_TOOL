path = r'D:\SDD DATA\all bios\Bios\HP\17817-1\CSME 11.8 Repository r34\CSME 11.8 Repository r34\11.8.50.3399_COR_H_DA_PRD_RGN.bin'
with open(path, 'rb') as f:
    data = f.read()

idx = 0
while True:
    idx = data.find(b'$CPD', idx)
    if idx == -1: break
    part_name = data[idx+0xc:idx+0x10]
    print(f"CPD at 0x{idx:x}: {part_name}")
    idx += 4
