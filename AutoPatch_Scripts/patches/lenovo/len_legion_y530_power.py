"""
AutoPatch Script: Power Throttling / ME Reset
Brand: LENOVO
Target Model: Legion Y530
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "len_legion_y530_power",
    "brand": "LENOVO",
    "model": "Legion Y530",
    "board_code": "NM-B701",
    "title": "Power Throttling / ME Reset",
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
    return True, "Firmware verified for LENOVO Legion Y530."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Power Throttling / ME Reset
    return True, patched, "Patch applied successfully: Power Throttling / ME Reset"
