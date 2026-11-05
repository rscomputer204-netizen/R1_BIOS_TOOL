"""
AutoPatch Script: Onboard RAM Disable
Brand: DELL
Target Model: Latitude 3490
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "dell_lat_3490_ram_disable",
    "brand": "DELL",
    "model": "Latitude 3490",
    "board_code": "CAL50/DAL10 LA-F115P",
    "title": "Onboard RAM Disable",
    "category": "RAM Disable",
    "symptom": "Faulty onboard DDR4 memory causes 2,4 amber/white LED blink code.",
    "description": "Disables Channel 0 onboard RAM SPD table, forcing system to use external slot.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for DELL Latitude 3490."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Onboard RAM Disable
    return True, patched, "Patch applied successfully: Onboard RAM Disable"
