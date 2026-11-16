fpath = r'D:\SDD DATA\all bios\Bios\HP\hp 840 g6 Crescent-6050A3022501-MB-A01 (A1)\HP 840 G6 crescent-6050a3022501-mb-a01\New folder\Orig+R70_010600\nasir\g6.bin'
with open(fpath, "rb") as f: data = f.read()

print("len:", hex(len(data)))
print("Starts with FD?", data[:4] == b'\x5A\xA5\xF0\x0F')
print("FD at 0x10?", data[0x10:0x14] == b'\x5A\xA5\xF0\x0F')
print("FPT count:", data.count(b'$FPT'))
print("MN2 count:", data.count(b'$MN2'))
print("CPD count:", data.count(b'$CPD'))
