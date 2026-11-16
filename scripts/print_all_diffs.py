import json
with open(r'd:\BIOS_-TOOL\scripts\remaining_diffs.json') as f:
    diffs = json.load(f)

# Let's see all unique diff keys and patterns
from collections import Counter
diff_keys = Counter()
for d in diffs:
    for k in d['diffs']:
        diff_keys[k] += 1
print('Keys:', diff_keys)

# Print all 83 file names and their diffs
for i, d in enumerate(diffs):
    print(f"{i+1:2d}. {d['file']} -> {d['diffs']}")
