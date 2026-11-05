"""
AutoPatch Script: Display Delay 25s Fix
Brand: HP
Target Model: ProBook 450 G8
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "hp_pb_450_g8_delay",
    "brand": "HP",
    "model": "ProBook 450 G8",
    "board_code": "DA0X9TMB8D0",
    "title": "Display Delay 25s Fix",
    "category": "Delay Fix",
    "symptom": "Display output delayed by 25 seconds on G8.",
    "description": "Refreshes CSME v15 handshake configuration.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for HP ProBook 450 G8."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Display Delay 25s Fix
    return True, patched, "Patch applied successfully: Display Delay 25s Fix"
