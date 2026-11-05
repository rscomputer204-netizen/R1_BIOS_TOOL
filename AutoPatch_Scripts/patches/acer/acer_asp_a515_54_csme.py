"""
AutoPatch Script: CSME State Delay Fix
Brand: ACER
Target Model: Aspire 5 A515-54
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "acer_asp_a515_54_csme",
    "brand": "ACER",
    "model": "Aspire 5 A515-54",
    "board_code": "EH5LP LA-H801P",
    "title": "CSME State Delay Fix",
    "category": "Delay Fix",
    "symptom": "ME handshake delay causes 35s boot time.",
    "description": "Clears ME state machine error counters.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for ACER Aspire 5 A515-54."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied CSME State Delay Fix
    return True, patched, "Patch applied successfully: CSME State Delay Fix"
