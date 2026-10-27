import os

ASUS_DIR = r"D:\SDD DATA\all bios\Bios\ASUS"

def scan_asus():
    print("=" * 80)
    print("       R1 BIOS RESEARCH LAB - ASUS FIRMWARE DISCOVERY SCANNER")
    print("=" * 80)
    
    matches = []
    for root, dirs, files in os.walk(ASUS_DIR):
        bin_files = [f for f in files if f.lower().endswith(('.bin', '.rom', '.fd'))]
        if not bin_files:
            continue
            
        matching = [f for f in bin_files if any(k in f.lower() for k in ["pass", "lock", "unlock", "clean", "err", "fix", "ok"])]
        if matching or len(bin_files) >= 2:
            matches.append((root, bin_files, matching))
            
    print(f"[*] Found {len(matches)} ASUS candidate directories:\n")
    for idx, (folder, bfiles, mfiles) in enumerate(matches[:25]):
        rel = os.path.relpath(folder, ASUS_DIR)
        print(f"[{idx+1:02d}] {rel}")
        for bf in bfiles:
            tag = " [TARGET]" if bf in mfiles else "         "
            sz = os.path.getsize(os.path.join(folder, bf)) / 1024 / 1024
            print(f"  {tag} {bf} ({sz:.2f} MB)")
        print()

if __name__ == "__main__":
    scan_asus()
