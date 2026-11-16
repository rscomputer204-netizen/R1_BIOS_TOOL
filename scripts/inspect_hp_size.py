import json
with open(r"d:\BIOS_-TOOL\scripts\hp_benchmark_results.json") as f:
    data = json.load(f)
for d in data["details"]:
    diffs = d.get("diffs", {})
    if "size" in diffs:
        print(f"{d['file']} ({d['version']}): {diffs['size']}")
