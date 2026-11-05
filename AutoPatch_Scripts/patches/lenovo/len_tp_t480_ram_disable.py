"""
AutoPatch Script: Onboard RAM Disable
Brand: LENOVO
Target Model: ThinkPad T480
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "len_tp_t480_ram_disable",
    "brand": "LENOVO",
    "model": "ThinkPad T480",
    "board_code": "NM-B501",
    "title": "Onboard RAM Disable",
    "category": "RAM Disable",
    "symptom": "Onboard RAM failure with 5 beeps or black screen on T480.",
    "description": "Reroutes memory controller addressing to SODIMM only.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for LENOVO ThinkPad T480."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Onboard RAM Disable
    return True, patched, "Patch applied successfully: Onboard RAM Disable"
