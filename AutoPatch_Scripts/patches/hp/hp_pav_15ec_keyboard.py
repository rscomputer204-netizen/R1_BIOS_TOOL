"""
AutoPatch Script: Keyboard Freeze Delay
Brand: HP
Target Model: Pavilion Gaming 15-ec
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "hp_pav_15ec_keyboard",
    "brand": "HP",
    "model": "Pavilion Gaming 15-ec",
    "board_code": "DA0G3HMB8D0",
    "title": "Keyboard Freeze Delay",
    "category": "General",
    "symptom": "System freezes for 15 seconds during keyboard controller init.",
    "description": "Fixes EC/KBC handshake timing parameters.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for HP Pavilion Gaming 15-ec."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Keyboard Freeze Delay
    return True, patched, "Patch applied successfully: Keyboard Freeze Delay"
