import sys
sys.path.insert(0, r'd:\BIOS_-TOOL\external\MEAnalyzer')
import MEA

# Let's inspect MEA.py by running it on test ok.bin and catching eng_fw_end
import subprocess
cmd = [sys.executable, r"d:\BIOS_-TOOL\external\MEAnalyzer\MEA.py", r"D:\SDD DATA\all bios\Bios\LENOVO\NM-B891 BIOS T490S\test ok.bin", "-skip", "-exit", "-json"]
subprocess.run(cmd)

import json
with open(r"d:\BIOS_-TOOL\external\MEAnalyzer\test ok.bin.json") as f:
    print(json.load(f))
