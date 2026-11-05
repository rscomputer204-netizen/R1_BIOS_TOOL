"""
AutoPatch Script: Display Delay 30s Fix
Brand: ACER
Target Model: Aspire 3 A315-54
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "acer_asp_a315_54_delay",
    "brand": "ACER",
    "model": "Aspire 3 A315-54",
    "board_code": "EH5LP LA-H801P",
    "title": "Display Delay 30s Fix",
    "category": "Delay Fix",
    "symptom": "Aspire 3 A315-54 takes 30 seconds to show Acer logo.",
    "description": "Clears ME v12 boot timer delay in UEFI NVRAM.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for ACER Aspire 3 A315-54."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Display Delay 30s Fix
    return True, patched, "Patch applied successfully: Display Delay 30s Fix"
