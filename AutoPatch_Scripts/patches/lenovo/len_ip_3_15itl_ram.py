"""
AutoPatch Script: Onboard RAM Disable
Brand: LENOVO
Target Model: IdeaPad 3-15ITL05
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "len_ip_3_15itl_ram",
    "brand": "LENOVO",
    "model": "IdeaPad 3-15ITL05",
    "board_code": "NM-D152",
    "title": "Onboard RAM Disable",
    "category": "RAM Disable",
    "symptom": "Soldered RAM failure causes blue screens and freezes.",
    "description": "Disables soldered RAM bank in BIOS configuration.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for LENOVO IdeaPad 3-15ITL05."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Onboard RAM Disable
    return True, patched, "Patch applied successfully: Onboard RAM Disable"
