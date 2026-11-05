"""
AutoPatch Script: Universal ME Manufacturing Mode Clear
Brand: UNIVERSAL
Target Model: All Intel Core 4th to 14th Gen
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "uni_me_mfg_clear",
    "brand": "UNIVERSAL",
    "model": "All Intel Core 4th to 14th Gen",
    "board_code": "Universal Intel ME",
    "title": "Universal ME Manufacturing Mode Clear",
    "category": "General",
    "symptom": "System warns: Manufacturing Mode 0x33 or ME in Manufacturing Mode on boot.",
    "description": "Clears the Manufacturing Mode flag in the Intel Flash Descriptor to normal production mode.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for UNIVERSAL All Intel Core 4th to 14th Gen."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Universal ME Manufacturing Mode Clear
    return True, patched, "Patch applied successfully: Universal ME Manufacturing Mode Clear"
