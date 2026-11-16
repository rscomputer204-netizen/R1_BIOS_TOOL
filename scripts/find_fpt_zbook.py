fpath = r'D:\SDD DATA\all bios\Bios\HP\HP ZBook 15 G5 Mobile Workstation DA0XW2MBAG0 XW2A\orginal read no power.bin'
with open(fpath, "rb") as f: data = f.read()

pos = 0
while True:
    pos = data.find(b'$FPT', pos)
    if pos == -1: break
    print(f"$FPT at {hex(pos)}")
    pos += 4
