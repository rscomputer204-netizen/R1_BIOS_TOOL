with open(r"D:\SDD DATA\all bios\Bios\LENOVO\LA-H101P REV1.0\read bin.bin", "rb") as f:
    d = f.read()

# Check non-ff from 0x1000 to 0x400000 (ME region)
# Where is ME region in FD for read bin.bin?
b_raw = int.from_bytes(d[0x48:0x4a], "little")
l_raw = int.from_bytes(d[0x4a:0x4c], "little")
print("ME in FD (at 0x48):", hex(b_raw*0x1000), hex((l_raw+1)*0x1000))

# What is after 0x252800?
print("0x252800..0x280000 non-ff:")
chunk = d[0x252800:0x280000]
print("len of chunk:", hex(len(chunk)))
print("non-ff len:", hex(len(chunk.rstrip(b'\xff'))))
print("end offset:", hex(0x252800 + len(chunk.rstrip(b'\xff'))))
