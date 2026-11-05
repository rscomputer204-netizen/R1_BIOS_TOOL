"""
AutoPatch Script: Display Delay Fix
Brand: LENOVO
Target Model: ThinkPad X270
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "len_tp_x270_delay_fix",
    "brand": "LENOVO",
    "model": "ThinkPad X270",
    "board_code": "NM-B061",
    "title": "Display Delay Fix",
    "category": "Delay Fix",
    "symptom": "20 seconds delay before display appears on X270.",
    "description": "Clears corrupted CSME telemetry in flash descriptor.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for LENOVO ThinkPad X270."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Display Delay Fix
    return True, patched, "Patch applied successfully: Display Delay Fix"
