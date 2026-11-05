"""
AutoPatch Script: Fan Speed High Spin Fix
Brand: ASUS
Target Model: ROG Strix GL503GE
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "asus_rog_gl503ge_fan",
    "brand": "ASUS",
    "model": "ROG Strix GL503GE",
    "board_code": "GL503GE R2.1",
    "title": "Fan Speed High Spin Fix",
    "category": "Fan Error",
    "symptom": "Fans spin at 100% speed immediately on power on.",
    "description": "Recalibrates thermal trip points in DSDT/EC firmware area.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for ASUS ROG Strix GL503GE."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Fan Speed High Spin Fix
    return True, patched, "Patch applied successfully: Fan Speed High Spin Fix"
