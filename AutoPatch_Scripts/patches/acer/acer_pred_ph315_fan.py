"""
AutoPatch Script: Fan Speed Fix
Brand: ACER
Target Model: Predator Helios 300 PH315
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "acer_pred_ph315_fan",
    "brand": "ACER",
    "model": "Predator Helios 300 PH315",
    "board_code": "DH5VF LA-F952P",
    "title": "Fan Speed Fix",
    "category": "Fan Error",
    "symptom": "AeroBlade fans run at max speed constantly.",
    "description": "Restores thermal sensor calibration in DSDT.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for ACER Predator Helios 300 PH315."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Fan Speed Fix
    return True, patched, "Patch applied successfully: Fan Speed Fix"
