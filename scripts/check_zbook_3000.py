fpath = r'D:\SDD DATA\all bios\Bios\HP\HP ZBook 15 G5 Mobile Workstation DA0XW2MBAG0 XW2A\orginal read no power.bin'
with open(fpath, "rb") as f: data = f.read()

print("0x3000..0x3040:", data[0x3000:0x3040].hex())
