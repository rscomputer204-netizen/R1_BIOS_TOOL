import subprocess
import sys
import json

files = [
    r"D:\SDD DATA\all bios\Bios\LENOVO\LA-H101P REV1.0\clear mes\clear mes.bin",
    r"D:\SDD DATA\all bios\Bios\LENOVO\LA-H101P REV1.0\read bin.bin",
    r"D:\SDD DATA\all bios\Bios\LENOVO\GE4B0-GE5B0nm-d011.rev 1.0\GE4B0 GE5B0 NM-D011\outeimage bin.rom",
]

for f in files:
    subprocess.run([sys.executable, r"d:\BIOS_-TOOL\external\MEAnalyzer\MEA.py", f, "-skip", "-exit", "-json"], stdout=subprocess.DEVNULL)
    import os
    jname = os.path.join(r"d:\BIOS_-TOOL\external\MEAnalyzer", os.path.basename(f) + ".json")
    if os.path.exists(jname):
        with open(jname) as fp:
            d = json.load(fp)
            for k, v in d.items():
                if "Management Engine" in v and v["Management Engine"]:
                    me = v["Management Engine"][0]
                    print(os.path.basename(f), "-> Size:", me.get("Size"), "Family:", me.get("Family"), "Ver:", me.get("Version"))
