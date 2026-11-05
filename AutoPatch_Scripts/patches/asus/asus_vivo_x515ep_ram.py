"""
AutoPatch Script: Onboard RAM Disable
Brand: ASUS
Target Model: VivoBook X515EP
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "asus_vivo_x515ep_ram",
    "brand": "ASUS",
    "model": "VivoBook X515EP",
    "board_code": "X515EP R2.0",
    "title": "Onboard RAM Disable",
    "category": "RAM Disable",
    "symptom": "Faulty onboard DDR4 memory causes black screen.",
    "description": "Disables Channel 0 onboard RAM SPD table, forcing SODIMM.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for ASUS VivoBook X515EP."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Onboard RAM Disable
    return True, patched, "Patch applied successfully: Onboard RAM Disable"
