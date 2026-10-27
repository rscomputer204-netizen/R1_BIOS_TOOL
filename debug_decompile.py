import os
import subprocess
from pathlib import Path

fit_exe = r"C:\Users\R1 LAB\Desktop\BIOS_TOOL\external\FLASH System Tools\CSME System Tools v15.0 r15\Flash Image Tool\WIN32\fit.exe"
workspace = Path(r"C:\Users\R1 LAB\Desktop\BIOS_TOOL\WORKSPACE")
workspace.mkdir(exist_ok=True, parents=True)
xml_path = workspace / "config.xml"
temp_bios = workspace / "image.bin"

# Write a dummy bin so it exists
with open(temp_bios, "wb") as f:
    f.write(b"A" * 1024)

try:
    print(f"Executing: {fit_exe}")
    res = subprocess.run([fit_exe, "-b", "-save", str(xml_path), "-f", str(temp_bios)], 
                           cwd=str(workspace), capture_output=True, text=True)
    print("Return code:", res.returncode)
    print("Stdout:", res.stdout)
    print("Stderr:", res.stderr)
except Exception as e:
    import traceback
    traceback.print_exc()
