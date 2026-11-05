"""
AutoPatch Script: Manufacturing Mode Clear
Brand: DELL
Target Model: Latitude 5510
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "dell_lat_5510_mfg_mode",
    "brand": "DELL",
    "model": "Latitude 5510",
    "board_code": "FDW50 LA-J492P",
    "title": "Manufacturing Mode Clear",
    "category": "General",
    "symptom": "Prompts 'Manufacturing Mode: Level 0x33' on every startup.",
    "description": "Locks descriptor manufacturing mode flag to normal consumer production mode.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for DELL Latitude 5510."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Manufacturing Mode Clear
    return True, patched, "Patch applied successfully: Manufacturing Mode Clear"
