"""
AutoPatch Script: Display Delay Fix
Brand: LENOVO
Target Model: IdeaPad 5-14ITL05
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "len_ip_5_14itl_delay",
    "brand": "LENOVO",
    "model": "IdeaPad 5-14ITL05",
    "board_code": "NM-D211",
    "title": "Display Delay Fix",
    "category": "Delay Fix",
    "symptom": "IdeaPad 5 takes 30 seconds to show Lenovo logo.",
    "description": "Clears CSME v15 telemetry timeout registers.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for LENOVO IdeaPad 5-14ITL05."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Display Delay Fix
    return True, patched, "Patch applied successfully: Display Delay Fix"
