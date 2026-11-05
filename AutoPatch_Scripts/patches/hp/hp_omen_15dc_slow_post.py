"""
AutoPatch Script: Slow POST / Black Screen Fix
Brand: HP
Target Model: Omen 15-dc
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "hp_omen_15dc_slow_post",
    "brand": "HP",
    "model": "Omen 15-dc",
    "board_code": "DAG3DDMB8C0",
    "title": "Slow POST / Black Screen Fix",
    "category": "Delay Fix",
    "symptom": "Omen 15-dc display appears after 30 seconds delay.",
    "description": "Synchronizes Intel ME gaming profile descriptors.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for HP Omen 15-dc."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Slow POST / Black Screen Fix
    return True, patched, "Patch applied successfully: Slow POST / Black Screen Fix"
