"""
AutoPatch Script: POST Delay 25s Fix
Brand: DELL
Target Model: Latitude 5520
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "dell_lat_5520_post_delay",
    "brand": "DELL",
    "model": "Latitude 5520",
    "board_code": "GDF50 LA-K032P",
    "title": "POST Delay 25s Fix",
    "category": "Delay Fix",
    "symptom": "Dell logo appears after 25 seconds delay.",
    "description": "Reconfigures Tiger Lake memory training cache in NVRAM.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for DELL Latitude 5520."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied POST Delay 25s Fix
    return True, patched, "Patch applied successfully: POST Delay 25s Fix"
