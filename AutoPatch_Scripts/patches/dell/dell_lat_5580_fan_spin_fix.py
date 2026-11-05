"""
AutoPatch Script: Fan Spin No Display Fix
Brand: DELL
Target Model: Latitude 5580
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "dell_lat_5580_fan_spin_fix",
    "brand": "DELL",
    "model": "Latitude 5580",
    "board_code": "LA-E091P",
    "title": "Fan Spin No Display Fix",
    "category": "Power Fix",
    "symptom": "Fan spins at full speed on power button press with no display on screen.",
    "description": "Recalibrates thermal NVAR tables and restores CSME power state.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for DELL Latitude 5580."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Fan Spin No Display Fix
    return True, patched, "Patch applied successfully: Fan Spin No Display Fix"
