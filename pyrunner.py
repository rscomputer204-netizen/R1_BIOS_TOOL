"""
Standalone Python Script Runner for R1 BIOS Tool
Allows external scripts (ME Analyzer, MCExtractor, BGScriptTool, etc.)
to run on any Windows PC without requiring Python to be installed.
"""
import sys
import os
import runpy

# Ensure critical standard library C-extensions and modules are bundled by PyInstaller
import lzma
import bz2
import ctypes
import hashlib
import urllib.request
import struct
import re
import subprocess
import threading
import itertools
import traceback
import importlib.util
import optparse
import html
import html.parser
import csv
import zipfile
import shutil
import math
import json
import platform
import glob
import datetime
import sqlite3
import zlib

def main():
    if len(sys.argv) < 2:
        print("Usage: pyrunner <script.py> [args...]")
        sys.exit(1)

    script_path = os.path.abspath(sys.argv[1])
    if not os.path.isfile(script_path):
        print(f"Error: Script not found: {script_path}")
        sys.exit(1)

    # Shift argv so the target script sees its own name at argv[0]
    sys.argv = sys.argv[1:]

    # Ensure script directory and common dependency paths are in sys.path
    script_dir = os.path.dirname(script_path)
    deps_dir = os.path.join(script_dir, "_deps")
    app_root = os.path.dirname(os.path.abspath(sys.executable)) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))

    paths_to_add = [
        script_dir,
        deps_dir,
        os.path.join(app_root, "ME Analyzer", "_deps"),
        os.path.join(app_root, "external", "MEAnalyzer", "_deps"),
    ]

    for p in paths_to_add:
        if os.path.isdir(p) and p not in sys.path:
            sys.path.insert(0, p)

    # Provide builtins.exit and builtins.quit for scripts that rely on them
    import builtins
    builtins.exit = sys.exit
    builtins.quit = sys.exit

    # Clear sys.frozen so scripts like MEA.py don't mistake pyrunner for their own exe
    if hasattr(sys, 'frozen'):
        del sys.frozen

    # Execute the target script
    try:
        runpy.run_path(script_path, run_name='__main__')
    except SystemExit as se:
        sys.exit(se.code)
    except Exception as e:
        print(f"Error running {os.path.basename(script_path)}: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
