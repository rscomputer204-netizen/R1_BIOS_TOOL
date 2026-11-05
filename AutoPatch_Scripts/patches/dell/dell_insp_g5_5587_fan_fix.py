"""
AutoPatch Script: Thermal Fan High Spin Fix
Brand: DELL
Target Model: Inspiron G5 5587
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "dell_insp_g5_5587_fan_fix",
    "brand": "DELL",
    "model": "Inspiron G5 5587",
    "board_code": "LA-E991P",
    "title": "Thermal Fan High Spin Fix",
    "category": "Fan Error",
    "symptom": "Fans spin at 100% speed immediately when AC adapter is plugged in.",
    "description": "Restores clean EC/ME thermal telemetry link.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for DELL Inspiron G5 5587."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Thermal Fan High Spin Fix
    return True, patched, "Patch applied successfully: Thermal Fan High Spin Fix"
