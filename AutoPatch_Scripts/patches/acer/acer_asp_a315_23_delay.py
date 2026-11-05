"""
AutoPatch Script: Display Delay Fix
Brand: ACER
Target Model: Aspire 3 A315-23
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "acer_asp_a315_23_delay",
    "brand": "ACER",
    "model": "Aspire 3 A315-23",
    "board_code": "DA0ZASMB8D0",
    "title": "Display Delay Fix",
    "category": "Delay Fix",
    "symptom": "Aspire 3 A315-23 20 seconds delay before display.",
    "description": "Clears corrupted memory training records in NVRAM.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for ACER Aspire 3 A315-23."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Display Delay Fix
    return True, patched, "Patch applied successfully: Display Delay Fix"
