import os
from pathlib import Path
from fit_automator import execute_fit_decompile
import shutil

# Setup
workspace = Path(r"C:\Users\R1 LAB\Desktop\BIOS_TOOL\Test_Decomp_Area")
workspace.mkdir(exist_ok=True)

# Create a dummy bios
bios_file = workspace / "test_bios.bin"
with open(bios_file, "wb") as f:
    f.write(b"dummy")

def callback(msg, lvl=""):
    print(f"[{lvl}] {msg}")

print("Testing execute_fit_decompile...")
try:
    res = execute_fit_decompile(str(bios_file), "15", str(workspace), callback)
    print("Result:", res)
except Exception as e:
    import traceback
    traceback.print_exc()

print("Checking if test_bios.bin still exists:", bios_file.exists())
