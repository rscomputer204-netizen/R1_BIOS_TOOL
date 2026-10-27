import os
import re

HP_DIR = r"D:\SDD DATA\all bios\HP"

TARGET_KEYWORDS = [
    "pass", "lock", "unlock", "clean pass", "clean_pass", "cleanpass",
    "err", "error", "msg", "message", "tpm", "mpm", "fixed", "patch", "repaired"
]

def scan_hp_bios_directory():
    print("=" * 80)
    print("       R1 BIOS RESEARCH LAB - HP PASSWORD & ERROR SCANNER")
    print(f"       Target Directory: {HP_DIR}")
    print("=" * 80)
    
    matches = []
    all_bins = []
    
    for root, dirs, files in os.walk(HP_DIR):
        bin_files = [f for f in files if f.lower().endswith(('.bin', '.rom', '.fd'))]
        if not bin_files:
            continue
            
        all_bins.extend([os.path.join(root, f) for f in bin_files])
        
        # Check if folder or files match target keywords
        folder_match = any(kw in root.lower() for kw in TARGET_KEYWORDS)
        matching_files = [f for f in bin_files if any(kw in f.lower() for kw in TARGET_KEYWORDS)]
        
        if folder_match or matching_files or len(bin_files) >= 2:
            matches.append({
                "folder": root,
                "bin_files": bin_files,
                "matching_files": matching_files,
                "has_target": folder_match or bool(matching_files)
            })
            
    print(f"[*] Total BIOS binary files found: {len(all_bins):,}")
    print(f"[*] Total candidate folders with potential pairs/targets: {len(matches):,}\n")
    
    # Priority 1: Folders containing explicit pass/lock/unlock/error keywords
    priority_cases = [m for m in matches if m["has_target"]]
    print(f"[*] HIGH PRIORITY TARGET FOLDERS ({len(priority_cases)}):")
    print("-" * 80)
    
    for idx, c in enumerate(priority_cases):
        rel_folder = os.path.relpath(c["folder"], HP_DIR)
        print(f"[{idx+1:02d}] {rel_folder}")
        for bf in c["bin_files"]:
            tag = "  --> [MATCH]" if bf in c["matching_files"] else "     "
            fsize = os.path.getsize(os.path.join(c["folder"], bf))
            print(f"  {tag} {bf} ({fsize / 1024 / 1024:.2f} MB)")
        print()

if __name__ == "__main__":
    scan_hp_bios_directory()
