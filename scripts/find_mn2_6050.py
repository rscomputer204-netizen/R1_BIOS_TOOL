with open(r'D:\SDD DATA\all bios\Bios\HP\6050A2637901-MB-A02\HP_6050A2637901_Clear me.bin\HP_6050A2637901_Clear me.bin', 'rb') as f:
    data = f.read()

idx = 0x4cc000
while idx < 0x600000:
    idx = data.find(b'$MN2', idx)
    if idx == -1: break
    print(f'MN2 tag at 0x{idx:x}, header at 0x{idx-0x1c:x}, name: {data[idx-0x1c+0x284:idx-0x1c+0x284+8]}')
    idx += 4
