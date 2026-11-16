import json
with open(r"d:\BIOS_-TOOL\scripts\hp_benchmark_results.json") as f:
    data = json.load(f)
for d in data["details"]:
    diffs = d.get("diffs", {})
    if "chipset" in diffs and "CMP-H/LP" in diffs["chipset"]:
        print(f"{d['file']} ({d['version']}): {diffs}")
