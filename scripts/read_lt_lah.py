with open(r"D:\SDD DATA\all bios\Bios\LENOVO\LA-H101P REV1.0\read bin.bin", "rb") as f:
    d = f.read()

import struct

# In LA-H101P, where is the CSE Layout Table?
# Check at 0x1000 (me_fd_start)
me_start = 0x1000
lt_hdr = d[me_start:me_start+0x40]
print("LT at 0x1000:", lt_hdr[:32].hex())
# Fields in CSE_Layout_Table_17:
# [0:16] res
# [16:18] Size (0x40)
# [18:19] Flags
# [19:20] Res
# [20:24] Checksum
# [24:28] DataOffset, [28:32] DataSize
# [32:36] BP1Offset, [36:40] BP1Size
# [40:44] BP2Offset, [44:48] BP2Size
# [48:52] BP3Offset, [52:56] BP3Size
# [56:60] BP4Offset, [60:64] BP4Size
# [64:68] BP5Offset, [68:72] BP5Size
lt_size = struct.unpack('<H', lt_hdr[16:18])[0]
print("lt_size:", hex(lt_size))
if lt_size in (0x40, 0x48):
    for i in range(6):
        off = 24 + i*8
        poff = struct.unpack('<I', lt_hdr[off:off+4])[0]
        psz = struct.unpack('<I', lt_hdr[off+4:off+8])[0]
        name = "Data" if i == 0 else f"BP{i}"
        print(f"  {name}: off={hex(poff)}, sz={hex(psz)}, end={hex(poff+psz)}")
