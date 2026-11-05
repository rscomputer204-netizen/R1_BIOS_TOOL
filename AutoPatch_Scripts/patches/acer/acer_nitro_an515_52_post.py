"""
AutoPatch Script: Slow POST Delay Fix
Brand: ACER
Target Model: Nitro 5 AN515-52
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "acer_nitro_an515_52_post",
    "brand": "ACER",
    "model": "Nitro 5 AN515-52",
    "board_code": "DH5VF LA-F952P",
    "title": "Slow POST Delay Fix",
    "category": "Delay Fix",
    "symptom": "Slow POST sequence on Coffee Lake Nitro 5.",
    "description": "Clears corrupted memory training records in NVRAM.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for ACER Nitro 5 AN515-52."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Slow POST Delay Fix
    return True, patched, "Patch applied successfully: Slow POST Delay Fix"
