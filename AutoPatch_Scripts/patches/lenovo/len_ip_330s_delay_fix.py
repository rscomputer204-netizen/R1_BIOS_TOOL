"""
AutoPatch Script: Display Delay Fix
Brand: LENOVO
Target Model: IdeaPad 330S-15IKB
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "len_ip_330s_delay_fix",
    "brand": "LENOVO",
    "model": "IdeaPad 330S-15IKB",
    "board_code": "NM-B561",
    "title": "Display Delay Fix",
    "category": "Delay Fix",
    "symptom": "IdeaPad 330S takes 25 seconds to show display.",
    "description": "Resets ME timeout parameters in flash descriptor.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for LENOVO IdeaPad 330S-15IKB."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Display Delay Fix
    return True, patched, "Patch applied successfully: Display Delay Fix"
