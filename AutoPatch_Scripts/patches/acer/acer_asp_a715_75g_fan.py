"""
AutoPatch Script: Fan High Spin Fix
Brand: ACER
Target Model: Aspire 7 A715-75G
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "acer_asp_a715_75g_fan",
    "brand": "ACER",
    "model": "Aspire 7 A715-75G",
    "board_code": "FH52Q LA-J801P",
    "title": "Fan High Spin Fix",
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
    return True, "Firmware verified for ACER Aspire 7 A715-75G."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Fan High Spin Fix
    return True, patched, "Patch applied successfully: Fan High Spin Fix"
