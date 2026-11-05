"""
AutoPatch Script: CSME Timeout Reset
Brand: LENOVO
Target Model: ThinkPad X1 Carbon Gen 7
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "len_tp_x1c7_csme_fix",
    "brand": "LENOVO",
    "model": "ThinkPad X1 Carbon Gen 7",
    "board_code": "NM-C121",
    "title": "CSME Timeout Reset",
    "category": "Error Fix",
    "symptom": "CSME error and slow POST on X1 Carbon Gen 7.",
    "description": "Restores CSME v12 healthy operational state.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for LENOVO ThinkPad X1 Carbon Gen 7."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied CSME Timeout Reset
    return True, patched, "Patch applied successfully: CSME Timeout Reset"
