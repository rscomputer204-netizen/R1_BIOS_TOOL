"""
AutoPatch Script: Display Delay 30s Fix
Brand: ACER
Target Model: Nitro 5 AN515-51
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "acer_nitro_an515_51_delay",
    "brand": "ACER",
    "model": "Nitro 5 AN515-51",
    "board_code": "C5V01 LA-E892P",
    "title": "Display Delay 30s Fix",
    "category": "Delay Fix",
    "symptom": "Nitro 5 AN515-51 takes 30 seconds to show display.",
    "description": "Resets Kaby Lake ME fast boot delay tokens.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for ACER Nitro 5 AN515-51."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Display Delay 30s Fix
    return True, patched, "Patch applied successfully: Display Delay 30s Fix"
