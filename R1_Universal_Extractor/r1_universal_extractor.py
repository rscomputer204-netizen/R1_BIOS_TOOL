"""
R1_Universal_Extractor: r1_universal_extractor.py
==================================================
Main Executable Entry Point for R1 Universal Extractor.
Run with or without arguments:
- CLI mode: python r1_universal_extractor.py "bios_file.exe" ["output_dir"]
- GUI mode: python r1_universal_extractor.py
"""

import sys
import os

# Set paths
sys.path.insert(0, os.path.dirname(__file__))
from r1_extractor_core import R1ExtractorCore


def main():
    if len(sys.argv) > 1 and sys.argv[1] not in ("--gui", "-g"):
        target_file = sys.argv[1]
        out_dir = sys.argv[2] if len(sys.argv) > 2 else None
        
        print(f"[CLI] Starting R1 Universal Extractor on: {target_file}")
        summary = R1ExtractorCore.extract(target_file, out_dir, logger=print)
        
        sys.exit(0 if summary.get("success") else 1)
    else:
        from r1_extractor_gui import main as gui_main
        gui_main()


if __name__ == "__main__":
    main()
