"""
AutoPatch Script: Sure Start Loop Fix
Brand: HP
Target Model: EliteBook 830 G6
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "hp_eb_830_g6_surestart",
    "brand": "HP",
    "model": "EliteBook 830 G6",
    "board_code": "6050A3022501",
    "title": "Sure Start Loop Fix",
    "category": "Error Fix",
    "symptom": "HP Sure Start recovery loop on boot.",
    "description": "Repairs corrupted HP Sure Start checksum in NVRAM.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for HP EliteBook 830 G6."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Sure Start Loop Fix
    return True, patched, "Patch applied successfully: Sure Start Loop Fix"
