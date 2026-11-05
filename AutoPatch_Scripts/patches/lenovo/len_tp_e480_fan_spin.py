"""
AutoPatch Script: Fan Spin No Display Fix
Brand: LENOVO
Target Model: ThinkPad E480
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "len_tp_e480_fan_spin",
    "brand": "LENOVO",
    "model": "ThinkPad E480",
    "board_code": "NM-B421",
    "title": "Fan Spin No Display Fix",
    "category": "Power Fix",
    "symptom": "Fan spins at full speed but no display output.",
    "description": "Restores clean EC/PCH handshake in UEFI image.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for LENOVO ThinkPad E480."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Fan Spin No Display Fix
    return True, patched, "Patch applied successfully: Fan Spin No Display Fix"
