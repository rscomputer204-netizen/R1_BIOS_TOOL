fpath = r'D:\SDD DATA\all bios\Bios\HP\01015fy00-388-g\dump_main.bin'
with open(fpath, 'rb') as f: data = f.read()
print('len:', hex(len(data)))
print('FPT at:', hex(data.find(b'$FPT')))
print('MN2 at:', hex(data.find(b'$MN2')))
print('FOVD at:', hex(data.find(b'FOVD')))
print('has Flash Descriptor at 0x0?', data[:4] == b'\x5a\xa5\xf0\x0f')
