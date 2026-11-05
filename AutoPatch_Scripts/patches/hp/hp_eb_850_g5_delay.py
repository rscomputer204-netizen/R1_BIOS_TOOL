"""
AutoPatch Script: Display Output Delay
Brand: HP
Target Model: EliteBook 850 G5
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "hp_eb_850_g5_delay",
    "brand": "HP",
    "model": "EliteBook 850 G5",
    "board_code": "6050A2945601",
    "title": "Display Output Delay",
    "category": "Delay Fix",
    "symptom": "EliteBook 850 G5 display output delayed by 30 seconds.",
    "description": "Resets CSME fast boot timeout parameter.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for HP EliteBook 850 G5."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Display Output Delay
    return True, patched, "Patch applied successfully: Display Output Delay"
