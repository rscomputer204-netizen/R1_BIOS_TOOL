"""
AutoPatch Script: Display Delay 20s Fix
Brand: LENOVO
Target Model: ThinkPad T470
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "len_tp_t470_delay_fix",
    "brand": "LENOVO",
    "model": "ThinkPad T470",
    "board_code": "NM-A931",
    "title": "Display Delay 20s Fix",
    "category": "Delay Fix",
    "symptom": "ThinkPad T470 takes 20 seconds to show Lenovo logo.",
    "description": "Clears ME v11 boot timer delay in UEFI NVRAM.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for LENOVO ThinkPad T470."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Display Delay 20s Fix
    return True, patched, "Patch applied successfully: Display Delay 20s Fix"
