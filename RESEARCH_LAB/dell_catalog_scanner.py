import os

DELL_DIRS = [
    r"D:\SDD DATA\all bios\Dell",
    r"D:\SDD DATA\all bios\Bios\DELL"
]

TARGET_KEYWORDS = [
    "pass", "lock", "unlock", "clean_pass", "clean pass", "unpass",
    "tpm", "err", "error", "fixed", "patch", "repaired", "clean", "ok"
]

def scan_dell():
    print("=" * 80)
    print("       R1 BIOS RESEARCH LAB - DELL FIRMWARE DISCOVERY SCANNER")
    print("=" * 80)
    
    candidates = []
    
    for base in DELL_DIRS:
        if not os.path.exists(base):
            continue
        print(f"[*] Scanning base directory: {base}")
        for root, dirs, files in os.walk(base):
            bin_files = [f for f in files if f.lower().endswith(('.bin', '.rom', '.fd'))]
            if not bin_files:
                continue
                
            has_kw_folder = any(kw in root.lower() for kw in ["pass", "lock", "unlock", "tpm", "err", "fix", "repair"])
            matching_files = [f for f in bin_files if any(kw in f.lower() for kw in ["pass", "lock", "unlock", "tpm", "err", "fix", "clean", "patch", "ok"])]
            
            if has_kw_folder or (len(bin_files) >= 2 and matching_files):
                candidates.append({
                    "folder": root,
                    "bin_files": bin_files,
                    "matching": matching_files
                })
                
    print(f"\n[*] Found {len(candidates)} candidate folders in Dell collections:\n")
    for idx, c in enumerate(candidates):
        print(f"[{idx+1:02d}] {c['folder']}")
        for f in c["bin_files"]:
            fpath = os.path.join(c["folder"], f)
            sz = os.path.getsize(fpath) / (1024 * 1024)
            tag = " [TARGET]" if f in c["matching"] else "         "
            print(f"  {tag} {f} ({sz:.2f} MB)")
        print()

if __name__ == "__main__":
    scan_dell()
