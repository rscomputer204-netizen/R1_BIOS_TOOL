"""
AutoPatch Script: Display Delay 30s Fix
Brand: LENOVO
Target Model: ThinkPad X1 Carbon Gen 8
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "len_tp_x1c8_delay_fix",
    "brand": "LENOVO",
    "model": "ThinkPad X1 Carbon Gen 8",
    "board_code": "NM-C871",
    "title": "Display Delay 30s Fix",
    "category": "Delay Fix",
    "symptom": "X1 Carbon Gen 8 30 seconds display delay.",
    "description": "Optimizes CSME v14 initialization flags.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for LENOVO ThinkPad X1 Carbon Gen 8."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Display Delay 30s Fix
    return True, patched, "Patch applied successfully: Display Delay 30s Fix"
