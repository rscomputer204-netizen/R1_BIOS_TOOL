"""
Deep XML Analysis + Fix:
- Find exact ME Region size in XML FlashLayout
- Find what tags control ME region boundaries
- Auto-fix by adjusting FlashLayout or selecting correct-sized ME
"""
import re
from pathlib import Path

xml_path = Path("FIT_WORKSPACE/config.xml")
xml = xml_path.read_text(encoding="utf-8", errors="replace")

print("=== FLASH LAYOUT TAGS ===")
# Find FlashLayout section
fl_match = re.search(r'<FlashLayout.*?</FlashLayout>', xml, re.DOTALL | re.IGNORECASE)
if fl_match:
    fl_text = fl_match.group(0)
    print(fl_text[:4000])

print("\n=== ME REGION SIZE TAGS ===")
# All tags containing 'ME' and size/region
for m in re.finditer(r'<\w*[Mm][Ee]\w*[^<]*/>', xml):
    line = m.group(0)
    if any(k in line.lower() for k in ['size', 'region', 'limit', 'start', 'end', 'base']):
        print(" ", line.strip()[:200])

print("\n=== INPUTFILE ME TAG ===")
# Find the ME InputFile tag
for m in re.finditer(r'<InputFile[^>]*/>', xml, re.IGNORECASE):
    tag = m.group(0)
    if any(k in tag.lower() for k in ['me', 'engine', 'cse', 'management', 'region']):
        print(" ", tag.strip()[:400])

print("\n=== REGION BOUNDARIES (from map) ===")
# From map file: ME Region: 0x3000 -> 0x6FFFFF  
me_start = 0x3000
me_end   = 0x6FFFFF
me_size  = me_end - me_start + 1
bios_start = 0x750000
print(f"ME Region:   0x{me_start:08X} → 0x{me_end:08X} = {me_size:,} bytes = {me_size/1024/1024:.4f} MB")
print(f"ME Hex size: 0x{me_size:X}")
print(f"BIOS start:  0x{bios_start:08X}")

# Available 11.8.x COR_LP files and sizes
print("\n=== CANDIDATE ME FILES FOR THIS FLASH ===")
repo = Path("Firmware_Repository/ME_Region")
print(f"Required size <= {me_size:,} bytes ({me_size/1024/1024:.2f} MB)")
for f in sorted(repo.glob("11.8.*.bin")):
    s = f.stat().st_size
    fits = "✓ FITS" if s <= me_size else "✗ TOO BIG"
    corp = "COR" if "COR" in f.name else ("CON" if "CON" in f.name else "SLM")
    lp   = "LP" if "LP" in f.name else "H"
    print(f"  {fits} [{corp}/{lp}] {f.name}: {s:,} bytes ({s/1024/1024:.2f} MB)")
