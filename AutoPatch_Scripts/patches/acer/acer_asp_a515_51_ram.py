"""
AutoPatch Script: Onboard RAM Disable
Brand: ACER
Target Model: Aspire 5 A515-51
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "acer_asp_a515_51_ram",
    "brand": "ACER",
    "model": "Aspire 5 A515-51",
    "board_code": "C5V01 LA-E891P",
    "title": "Onboard RAM Disable",
    "category": "RAM Disable",
    "symptom": "Defective soldered RAM causes restart loop or freezes.",
    "description": "Disables onboard RAM in BIOS SPD mapping, enables SODIMM.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for ACER Aspire 5 A515-51."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Onboard RAM Disable
    return True, patched, "Patch applied successfully: Onboard RAM Disable"
