# 🤖 AI SYSTEM WORKFLOW: BIOS ME Region Repair & Configuration Pipeline

> **IMPORTANT FOR FUTURE AI MODELS:**
> If you are reading this file, you have been assigned to repair a corrupted or "Initialized" Intel BIOS firmware dump, bring it to a "Configured" state, and present the result. *Please strictly follow this workflow to maintain system consistency!*

## 📁 1. Workspace Architecture
- **`TESTING_AREA/MAIN BIOS/`**: The folder where the User will drop corrupt/dirty `.bin` files waiting to be processed.
- **`TESTING_AREA/FINAL BIOS/`**: The directory where your final, repaired, and configured `.bin` files should be output.
- **`Firmware_Repository/ME_Region/`**: Contains clean Intel CSME binaries.
- **`ME Analyzer/`**: Contains `MEA.py`. Use this tool to get the ME version, SKU, and status of any BIOS image.
- **`external/`**: Contains the `FLASH System Tools` directory with correct versions of the Intel Flash Image Tool (`fit.exe`).
- **`fit_automator.py`**: A custom wrapper utility that automatically powers Intel FIT, replaces regions, locks the OEM descriptor, and builds a "Configured" image.

## 🛠️ 2. Step-by-Step AI Repair Workflow

### Step 1: Detect & Analyze
When the User instructs you that a new file is uploaded (e.g., `x61.bin`), first analyze it using ME Analyzer:
```powershell
python "ME Analyzer\MEA.py" "TESTING_AREA\MAIN BIOS\filename.bin"
```
**Look for:**
*   `Version` (e.g., `11.0.0.1194`)
*   `SKU` (e.g., `Consumer LP`)
*   `File System State` (It will usually say `Initialized`. Your job is to make it `Configured`).

### Step 2: Locate Clean Donor
Navigate to `Firmware_Repository/ME_Region/` and locate the matching clean ME Region file. 
*   Always match the major version (`v11`, `v15` etc.) and SKU (`CON_LP`, `COR_H` etc.).
*   It is standard protocol to automatically use the newest available minor update (e.g., `v11.8.92` for an original `v11.0.0.1194`).

### Step 3: Create & Run Repair Script
Do not try to binary-hex the file yourself unless Intel FIT fails! We have written `fit_automator.py` specifically for this task. 
Write a temporary python script in `TESTING_AREA` (e.g., `repair_job.py`) that looks like this:

```python
import sys
from pathlib import Path

ROOT = Path(r"c:\Users\R1 LAB\Desktop\BIOS_TOOL")
sys.path.append(str(ROOT))
import fit_automator

BIOS_FILE = ROOT / "TESTING_AREA" / "MAIN BIOS" / "filename.bin"
CLEAN_ME  = ROOT / "Firmware_Repository" / "ME_Region" / "11.x.y.z_CON_LP_PRD_RGN.bin"
OUTPUT    = ROOT / "TESTING_AREA" / "FINAL BIOS" / "filename_CONFIGURED.bin"

repair_set = { "ME": str(CLEAN_ME) }

# Execute automated Intel FIT pipeline targeting the original file's major version
success = fit_automator.execute_fit_rebuild(
    str(BIOS_FILE),
    repair_set,
    "11.0.0.1194",  # <-- The Original Version string from ME Analyzer results
    str(OUTPUT),
    print,
    "external" 
)

if success: print("Rebuild Successful!")
```
Execute your script: `python TESTING_AREA\repair_job.py`

### Step 4: Verify Output
Run `ME Analyzer` on the newly generated output file in `FINAL BIOS/`. Ensure that:
*   The ME Version is updated.
*   **File System State is explicitly `Configured`.**

### Step 5: Log & Report
Always create a markdown artifact log documenting the Original Version vs Repaired Version and stating the file pathway. The user relies on these records to know exactly what edits were made.

---

> **⚙️ How the Automated Tool Works (Background Info):**
> `fit_automator.execute_fit_rebuild` decompiles the target file into a staging workspace using Intel FIT. It overwrites the decompiled dirty ME binary with the Clean Donor binary you provided. Crucially, it then uses RegEx to parse `config.xml` and forcibly sets `<ManufacturingMode value="No" />`. This final instruction is what forces Intel FIT to build the final CSME image in the locked, 100% production-ready "Configured" state.
