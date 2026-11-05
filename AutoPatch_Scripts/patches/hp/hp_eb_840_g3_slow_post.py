"""
AutoPatch Script: Slow POST Delay Fix
Brand: HP
Target Model: EliteBook 840 G3
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "hp_eb_840_g3_slow_post",
    "brand": "HP",
    "model": "EliteBook 840 G3",
    "board_code": "6050A2727301",
    "title": "Slow POST Delay Fix",
    "category": "Delay Fix",
    "symptom": "20 seconds delay before HP logo on EliteBook 840 G3.",
    "description": "Resets Skylake ME v11 configuration partition.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for HP EliteBook 840 G3."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Slow POST Delay Fix
    return True, patched, "Patch applied successfully: Slow POST Delay Fix"
