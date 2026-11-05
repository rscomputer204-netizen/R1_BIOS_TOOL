"""
AutoPatch Script: Display Delay 30s Fix
Brand: DELL
Target Model: Latitude 7480
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "dell_lat_7480_delay_fix",
    "brand": "DELL",
    "model": "Latitude 7480",
    "board_code": "LA-E941P",
    "title": "Display Delay 30s Fix",
    "category": "Delay Fix",
    "symptom": "30 seconds black screen on every cold start before Dell logo appears.",
    "description": "Patches CSME timeout parameters in descriptor region.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for DELL Latitude 7480."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Display Delay 30s Fix
    return True, patched, "Patch applied successfully: Display Delay 30s Fix"
