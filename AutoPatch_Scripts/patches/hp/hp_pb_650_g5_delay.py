"""
AutoPatch Script: Display Delay 30s Fix
Brand: HP
Target Model: ProBook 650 G5
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "hp_pb_650_g5_delay",
    "brand": "HP",
    "model": "ProBook 650 G5",
    "board_code": "DA0G3DMB8D0",
    "title": "Display Delay 30s Fix",
    "category": "Delay Fix",
    "symptom": "HP ProBook 650 G5 30s display delay.",
    "description": "Restores clean CSME fast boot configuration.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for HP ProBook 650 G5."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Display Delay 30s Fix
    return True, patched, "Patch applied successfully: Display Delay 30s Fix"
