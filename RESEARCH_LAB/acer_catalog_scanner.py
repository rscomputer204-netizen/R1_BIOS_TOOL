import os

ACER_DIR = r"D:\SDD DATA\all bios\Bios\ACER"

TARGET_KEYWORDS = [
    "pass", "lock", "unlock", "unpass", "svp", "clean", "err", "error", "fixed", "ok", "patch"
]

def scan_acer():
    print("=" * 80)
    print("       R1 BIOS RESEARCH LAB - ACER FIRMWARE DISCOVERY SCANNER")
    print("=" * 80)
    
    matches = []
    for root, dirs, files in os.walk(ACER_DIR):
        bin_files = [f for f in files if f.lower().endswith(('.bin', '.rom', '.fd'))]
        if not bin_files:
            continue
            
        matching = [f for f in bin_files if any(k in f.lower() for k in TARGET_KEYWORDS)]
        has_folder_kw = any(k in root.lower() for k in ["pass", "lock", "unlock", "clean", "fix", "nitro", "aspire"])
        
        if matching or has_folder_kw or len(bin_files) >= 2:
            matches.append((root, bin_files, matching))
            
    print(f"[*] Found {len(matches)} ACER candidate directories:\n")
    for idx, (folder, bfiles, mfiles) in enumerate(matches):
        rel = os.path.relpath(folder, ACER_DIR)
        print(f"[{idx+1:02d}] {rel}")
        for bf in bfiles:
            tag = " [TARGET]" if bf in mfiles else "         "
            fpath = os.path.join(folder, bf)
            sz = os.path.getsize(fpath) / 1024 / 1024
            print(f"  {tag} {bf} ({sz:.2f} MB)")
        print()

if __name__ == "__main__":
    scan_acer()
