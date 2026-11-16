fpath = r'D:\SDD DATA\all bios\Bios\HP\6050A3059101-MB-A01 (A1)\ok 100\read raju.bin'
with open(fpath, 'rb') as f:
    data = f.read()

print("File size:", hex(len(data)))
fpt_idx = 0
while True:
    fpt_idx = data.find(b'$FPT', fpt_idx)
    if fpt_idx == -1: break
    print("Found $FPT at:", hex(fpt_idx))
    fpt_idx += 4

# Check Flash Descriptor
print("Starts with FD?", data[:4] == b'\x5a\xa5\xf0\x0f')
# Check CSE Layout Table
cse_idx = data.find(b'CNL\x00')
print("CNL at:", hex(cse_idx) if cse_idx != -1 else "No")
b_idx = data.find(b'BPDT')
print("BPDT at:", hex(b_idx) if b_idx != -1 else "No")
