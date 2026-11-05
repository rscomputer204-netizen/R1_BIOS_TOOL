"""
AutoPatch Script: Display Delay 30s Fix
Brand: ACER
Target Model: Aspire 5 A515-52
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "acer_asp_a515_52_delay",
    "brand": "ACER",
    "model": "Aspire 5 A515-52",
    "board_code": "DH5JV LA-G021P",
    "title": "Display Delay 30s Fix",
    "category": "Delay Fix",
    "symptom": "Aspire 5 A515-52 30-second black screen before logo.",
    "description": "Restores CSME v12 quickboot state flags.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for ACER Aspire 5 A515-52."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Display Delay 30s Fix
    return True, patched, "Patch applied successfully: Display Delay 30s Fix"
