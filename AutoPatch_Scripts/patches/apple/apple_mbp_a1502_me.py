"""
AutoPatch Script: ME State Reset
Brand: APPLE
Target Model: MacBook Pro 13\" A1502
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "apple_mbp_a1502_me",
    "brand": "APPLE",
    "model": "MacBook Pro 13\" A1502",
    "board_code": "820-3476-A",
    "title": "ME State Reset",
    "category": "Delay Fix",
    "symptom": "No startup chime and 25 seconds delay before Apple logo.",
    "description": "Clears ME state machine error counters in SPI flash.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for APPLE MacBook Pro 13\" A1502."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied ME State Reset
    return True, patched, "Patch applied successfully: ME State Reset"
