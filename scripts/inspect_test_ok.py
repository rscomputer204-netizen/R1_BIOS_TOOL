with open(r'D:\SDD DATA\all bios\Bios\LENOVO\NM-B891 BIOS T490S\test ok.bin', 'rb') as f:
    d = f.read()

me_start = 0x3000
me_end = 0xa00000
chunk = d[me_start:me_end]
non_ff_len = len(chunk.rstrip(b'\xff'))
print("non_ff_len:", hex(non_ff_len))
print("aligned:", hex((non_ff_len + 0xfff) & ~0xfff))
print("byte at non_ff_len-1:", hex(chunk[non_ff_len-1]))
print("bytes around 0x77c000:", chunk[0x77c000-16:0x77c000+32].hex())
