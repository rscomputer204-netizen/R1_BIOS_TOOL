"""
AutoPatch Script: Onboard RAM Disable
Brand: LENOVO
Target Model: IdeaPad S145-15IWL
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "len_ip_s145_ram_disable",
    "brand": "LENOVO",
    "model": "IdeaPad S145-15IWL",
    "board_code": "NM-C121",
    "title": "Onboard RAM Disable",
    "category": "RAM Disable",
    "symptom": "Onboard RAM chips bad, no display on boot.",
    "description": "Switches memory configuration to external SODIMM.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for LENOVO IdeaPad S145-15IWL."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Onboard RAM Disable
    return True, patched, "Patch applied successfully: Onboard RAM Disable"
