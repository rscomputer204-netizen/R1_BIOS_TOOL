import re, struct

with open(r'D:\SDD DATA\all bios\Bios\HP\01015fy00-388-g\dump_main.bin', 'rb') as f:
    reading = f.read()

# Let's inspect FD region at 0x10
flreg1 = struct.unpack('<I', reading[0x44:0x48])[0]
print("FLREG1 (ME Region register):", hex(flreg1))
base = (flreg1 & 0x1FFF) << 12
limit = ((flreg1 >> 16) & 0x1FFF) << 12 | 0xFFF
print("ME start:", hex(base), "ME limit:", hex(limit))
me_data = reading[base:limit+1]
print("ME data length:", hex(len(me_data)))
fpt_pat = re.compile(br'\$FPT(?:\x20|\x21)(?:\x00|\x10|\x20|\x30|\x40|\x50|\x60|\x70|\x80|\x90|\xA0|\xB0|\xC0|\xD0|\xE0|\xF0)', re.DOTALL)
m = list(fpt_pat.finditer(me_data))
print("FPT in ME region:", m)
