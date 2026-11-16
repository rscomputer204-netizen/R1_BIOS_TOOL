with open(r'D:\SDD DATA\all bios\Bios\HP\840 g1\25Q128_Clear me.bin', 'rb') as f:
    reading = f.read()

# Let's check from 0x4ca000 to 0x705000
print("At 0x4ca000 + 0x3000 = 0x4cd000:", reading[0x4cd000:0x4cd020])
print("At 0x705000:", reading[0x705000:0x705020])
# Is there non-0xFF between 0x4cd000 and 0x705000?
non_ff = [i for i, b in enumerate(reading[0x4cd000:0x705000]) if b != 0xFF and b != 0x00]
print("Number of non-FF/00 bytes:", len(non_ff))
