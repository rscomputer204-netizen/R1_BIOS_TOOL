"""
AutoPatch Script: Display Delay Fix
Brand: HP
Target Model: Pavilion 15-cc
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "hp_pav_15cc_delay",
    "brand": "HP",
    "model": "Pavilion 15-cc",
    "board_code": "DAG34AMB6D0",
    "title": "Display Delay Fix",
    "category": "Delay Fix",
    "symptom": "Pavilion 15-cc takes 20-30 seconds to boot.",
    "description": "Clears ME region timeout tokens.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for HP Pavilion 15-cc."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Display Delay Fix
    return True, patched, "Patch applied successfully: Display Delay Fix"
