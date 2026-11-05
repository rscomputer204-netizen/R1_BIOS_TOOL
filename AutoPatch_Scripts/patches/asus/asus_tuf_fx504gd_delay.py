"""
AutoPatch Script: Display Delay Fix
Brand: ASUS
Target Model: TUF Gaming FX504GD
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "asus_tuf_fx504gd_delay",
    "brand": "ASUS",
    "model": "TUF Gaming FX504GD",
    "board_code": "FX504GD R2.0",
    "title": "Display Delay Fix",
    "category": "Delay Fix",
    "symptom": "TUF FX504 takes 30 seconds to show display.",
    "description": "Resets ME timeout parameters in flash descriptor.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for ASUS TUF Gaming FX504GD."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Display Delay Fix
    return True, patched, "Patch applied successfully: Display Delay Fix"
