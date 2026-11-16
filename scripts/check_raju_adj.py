fpath = r'D:\SDD DATA\all bios\Bios\HP\6050A3059101-MB-A01 (A1)\ok 100\read raju.bin'
with open(fpath, 'rb') as f:
    reading = f.read()

# MEA adjusts reading when FD is at 0x10!
# Remember line 10021 in MEA.py:
# if start_man_match and (start_fd_match < start_man_match < start_fd_match + fd_comp_all_size) ...
# reading = reading[start_fd_match:start_fd_match + fd_comp_all_size] # Update input file buffer in RAM
print("First 16 bytes of file:", reading[:16].hex())
# If reading is sliced at 0x10:
reading_adj = reading[0x10:]
fpt_adj = reading_adj.find(b'$FPT')
print("FPT in reading_adj at:", hex(fpt_adj) if fpt_adj != -1 else "No")
fpt_orig = reading.find(b'$FPT')
print("FPT in reading at:", hex(fpt_orig) if fpt_orig != -1 else "No")
