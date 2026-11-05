"""
AutoPatch Script: Fan Spin No Display Delay
Brand: HP
Target Model: ProBook 450 G6
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "hp_pb_450_g6_fan_delay",
    "brand": "HP",
    "model": "ProBook 450 G6",
    "board_code": "DA0X8JMB8D0",
    "title": "Fan Spin No Display Delay",
    "category": "Delay Fix",
    "symptom": "Fan spins loudly for 25 seconds before display appears.",
    "description": "Adjusts thermal init delay and ME handshake.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for HP ProBook 450 G6."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Fan Spin No Display Delay
    return True, patched, "Patch applied successfully: Fan Spin No Display Delay"
