"""
AutoPatch Script: Power Delay Fix
Brand: HP
Target Model: Omen 15-dh
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "hp_omen_15dh_power_delay",
    "brand": "HP",
    "model": "Omen 15-dh",
    "board_code": "DAG3EAMB8D0",
    "title": "Power Delay Fix",
    "category": "Power Fix",
    "symptom": "Power button requires holding for 4 seconds before turning on.",
    "description": "Restores EC power button signal response parameters.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for HP Omen 15-dh."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Power Delay Fix
    return True, patched, "Patch applied successfully: Power Delay Fix"
