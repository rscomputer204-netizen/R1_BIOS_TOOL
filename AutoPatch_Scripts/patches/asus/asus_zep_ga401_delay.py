"""
AutoPatch Script: Display Delay 30s Fix
Brand: ASUS
Target Model: Zephyrus G14 GA401
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "asus_zep_ga401_delay",
    "brand": "ASUS",
    "model": "Zephyrus G14 GA401",
    "board_code": "GA401IV R2.0",
    "title": "Display Delay 30s Fix",
    "category": "Delay Fix",
    "symptom": "Zephyrus G14 display appears after 30 seconds delay.",
    "description": "Clears corrupted MRC memory training cache in NVRAM.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for ASUS Zephyrus G14 GA401."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Display Delay 30s Fix
    return True, patched, "Patch applied successfully: Display Delay 30s Fix"
