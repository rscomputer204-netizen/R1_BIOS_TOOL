fpath = r'D:\SDD DATA\all bios\Bios\HP\6050A3059101-MB-A01 (A1)\New folder\read 9-6-22.bin'
with open(fpath, "rb") as f: data = f.read()

print("0x1000..0x1040:", data[0x1000:0x1040].hex())
print("0x1000 is FPT?", data[0x1000:0x1004] == b'$FPT')
print("0x1010 is FPT?", data[0x1010:0x1014] == b'$FPT')
