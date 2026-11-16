with open(r'D:\SDD DATA\all bios\Bios\HP\6050A3059101-MB-A01 (A1)\New folder\read 9-6-22.bin', 'rb') as f:
    reading = f.read()

fpt_idx = reading.find(b'$FPT', 0x2000)
print("FPT at:", hex(fpt_idx))
import struct
num_entries = struct.unpack('<I', reading[fpt_idx+4:fpt_idx+8])[0]
print("num_entries:", num_entries)
for i in range(num_entries):
    e = reading[fpt_idx+32+i*32 : fpt_idx+32+(i+1)*32]
    name = e[:4].decode('latin1', errors='ignore')
    offset, size = struct.unpack('<II', e[8:16])
    print(f"  {name}: offset={hex(offset)}, size={hex(size)}, end={hex(offset+size)}")
