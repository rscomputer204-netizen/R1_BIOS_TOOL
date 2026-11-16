fpath = r'D:\SDD DATA\all bios\Bios\HP\6050A3059101-MB-A01 (A1)\ok 100\read raju.bin'
with open(fpath, 'rb') as f:
    reading = f.read()

# Let's search for partition names
for name in [b'FTPR', b'RBEP', b'PMCP', b'OEMP', b'WCOD', b'LOCL', b'NFTP']:
    p = 0
    while True:
        p = reading.find(name, p)
        if p == -1: break
        print(f"Found {name.decode()} at {hex(p)}")
        p += 4
