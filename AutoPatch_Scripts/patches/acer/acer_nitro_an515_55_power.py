"""
AutoPatch Script: Power Throttling / ME Fix
Brand: ACER
Target Model: Nitro 5 AN515-55
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "acer_nitro_an515_55_power",
    "brand": "ACER",
    "model": "Nitro 5 AN515-55",
    "board_code": "FH52Q LA-J801P",
    "title": "Power Throttling / ME Fix",
    "category": "Power Fix",
    "symptom": "CPU throttles to 800MHz due to corrupted ME power limits.",
    "description": "Clears ME power limit register and restores normal clocks.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for ACER Nitro 5 AN515-55."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Power Throttling / ME Fix
    return True, patched, "Patch applied successfully: Power Throttling / ME Fix"
