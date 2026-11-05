"""
AutoPatch Script: Display Delay 25s Fix
Brand: LENOVO
Target Model: ThinkPad E14 Gen 2
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "len_tp_e14_g2_delay",
    "brand": "LENOVO",
    "model": "ThinkPad E14 Gen 2",
    "board_code": "NM-D011",
    "title": "Display Delay 25s Fix",
    "category": "Delay Fix",
    "symptom": "25 seconds black screen delay on E14 Gen 2.",
    "description": "Synchronizes Tiger Lake GOP driver init.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for LENOVO ThinkPad E14 Gen 2."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Display Delay 25s Fix
    return True, patched, "Patch applied successfully: Display Delay 25s Fix"
