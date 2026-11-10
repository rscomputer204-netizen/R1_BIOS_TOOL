"""
R1 EC Finder - Command Line Interface (CLI)
===========================================
Usage:
    python cli.py [options] <filepath>

Options:
    -128             Filter for 128 KB EC blocks
    -160             Filter for 160 KB EC blocks
    -192             Filter for 192 KB EC blocks
    -256             Filter for 256 KB EC blocks
    -512             Filter for 512 KB EC blocks
    -1024            Filter for 1024 KB (1MB) EC blocks
    -o <outdir>      Specify output directory (default: current working dir)
    -h, --help       Show this help message
"""

import os
import sys

# Ensure parent directory is in python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from R1_EC_Finder.carver_engine import ECCarverEngine


def print_help():
    print("""
R1 EC Finder - Command Line Interface (CLI)
===========================================
Usage:
    python -m R1_EC_Finder.cli [options] <filepath>

Parameters:
    -128          Filter/Carve only 128 KB EC blocks
    -160          Filter/Carve only 160 KB EC blocks
    -192          Filter/Carve only 192 KB EC blocks
    -256          Filter/Carve only 256 KB EC blocks
    -512          Filter/Carve only 512 KB EC blocks
    -1024         Filter/Carve only 1024 KB (1MB) EC blocks
    -o <dir>      Output destination directory
    -h, --help    Show help message
""")


def main():
    args = sys.argv[1:]
    if not args or "-h" in args or "--help" in args:
        print_help()
        return

    req_size_kb = None
    out_dir = os.getcwd()
    target_file = None

    i = 0
    while i < len(args):
        a = args[i]
        if a in ["-128", "-160", "-192", "-256", "-320", "-384", "-512", "-1024"]:
            req_size_kb = int(a.lstrip("-"))
        elif a == "-o" and i + 1 < len(args):
            out_dir = args[i + 1]
            i += 1
        elif not a.startswith("-"):
            target_file = a
        i += 1

    if not target_file or not os.path.isfile(target_file):
        print(f"[ERROR] Target file not specified or does not exist: {target_file}")
        return

    print("=" * 65)
    print(" R1 EC FINDER — EMBEDDED CONTROLLER CARVER CLI")
    print("=" * 65)
    print(f"Target File : {target_file}")
    print(f"File Size   : {os.path.getsize(target_file) / (1024*1024):.2f} MB")
    if req_size_kb:
        print(f"Size Filter : {req_size_kb} KB")
    print("-" * 65)

    with open(target_file, "rb") as f:
        data = f.read()

    engine = ECCarverEngine(data)
    candidates = engine.scan()

    if req_size_kb:
        candidates = [c for c in candidates if (c.size // 1024) == req_size_kb]

    print(f"Discovered {len(candidates)} candidate(s):\n")
    if not candidates:
        print("No matching EC candidate found.")
        return

    base_name = os.path.splitext(os.path.basename(target_file))[0]
    os.makedirs(out_dir, exist_ok=True)

    for idx, c in enumerate(candidates, 1):
        info = c.to_dict()
        print(f"[{idx}] Confidence: {info['confidence']}% | Offset: {info['offset_hex']} | Size: {info['size_str']}")
        print(f"    Architecture: {info['chip_family']}")
        print(f"    Entropy     : {info['entropy']} | Method: {info['detection_method']}")

        # Auto-carve best match (or all matches)
        out_name = f"{base_name}_EC_0x{c.offset:X}_{info['size_kb']}KB.bin"
        out_path = os.path.join(out_dir, out_name)
        with open(out_path, "wb") as out_f:
            out_f.write(data[c.offset : c.offset + c.size])
        print(f"    -> Exported: {out_name}\n")


if __name__ == "__main__":
    main()

