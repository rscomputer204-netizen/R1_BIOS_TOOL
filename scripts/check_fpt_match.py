import re

with open(r'D:\SDD DATA\all bios\Bios\HP\01015fy00-388-g\dump_main.bin', 'rb') as f:
    reading = f.read()

fpt_pat = re.compile(br'\$FPT(?:\x20|\x21)(?:\x00|\x10|\x20|\x30|\x40|\x50|\x60|\x70|\x80|\x90|\xA0|\xB0|\xC0|\xD0|\xE0|\xF0)', re.DOTALL)
m = fpt_pat.search(reading)
print("FPT match:", m)
if m:
    print("Offset:", hex(m.start()))
    print("Header bytes:", reading[m.start():m.start()+32])
