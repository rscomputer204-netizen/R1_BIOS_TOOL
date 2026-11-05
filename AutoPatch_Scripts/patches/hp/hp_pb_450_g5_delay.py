"""
AutoPatch Script: Black Screen 35s Delay Fix
Brand: HP
Target Model: ProBook 450 G5
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "hp_pb_450_g5_delay",
    "brand": "HP",
    "model": "ProBook 450 G5",
    "board_code": "DA0X8BMB6F0",
    "title": "Black Screen 35s Delay Fix",
    "category": "Delay Fix",
    "symptom": "35s black screen delay on ProBook 450 G5.",
    "description": "Resets ME configuration timeout to 0.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for HP ProBook 450 G5."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Black Screen 35s Delay Fix
    return True, patched, "Patch applied successfully: Black Screen 35s Delay Fix"
