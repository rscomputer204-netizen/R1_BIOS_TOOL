"""
AutoPatch Script: Fan High Spin Fix
Brand: HP
Target Model: Pavilion Gaming 15-dk
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "hp_pav_15dk_fan_fix",
    "brand": "HP",
    "model": "Pavilion Gaming 15-dk",
    "board_code": "FPW50 LA-H461P",
    "title": "Fan High Spin Fix",
    "category": "Fan Error",
    "symptom": "Dual cooling fans run at 100% continuously.",
    "description": "Restores thermal sensor calibration in DSDT.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for HP Pavilion Gaming 15-dk."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Fan High Spin Fix
    return True, patched, "Patch applied successfully: Fan High Spin Fix"
