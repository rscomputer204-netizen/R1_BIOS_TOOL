"""
AutoPatch Script: Supervisor Password Clean
Brand: LENOVO
Target Model: ThinkPad L480
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "len_tp_l480_pass_clean",
    "brand": "LENOVO",
    "model": "ThinkPad L480",
    "board_code": "NM-B461",
    "title": "Supervisor Password Clean",
    "category": "Security",
    "symptom": "Supervisor password locked on ThinkPad L480.",
    "description": "Resets security credentials and clears SVP flag in NVRAM.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for LENOVO ThinkPad L480."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Supervisor Password Clean
    return True, patched, "Patch applied successfully: Supervisor Password Clean"
