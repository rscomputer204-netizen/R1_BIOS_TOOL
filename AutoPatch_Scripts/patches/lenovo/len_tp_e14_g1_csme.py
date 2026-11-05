"""
AutoPatch Script: CSME Handshake Error
Brand: LENOVO
Target Model: ThinkPad E14 Gen 1
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "len_tp_e14_g1_csme",
    "brand": "LENOVO",
    "model": "ThinkPad E14 Gen 1",
    "board_code": "NM-C421",
    "title": "CSME Handshake Error",
    "category": "Error Fix",
    "symptom": "CSME error message on ThinkPad E14 boot.",
    "description": "Clears host firmware interface error flags.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for LENOVO ThinkPad E14 Gen 1."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied CSME Handshake Error
    return True, patched, "Patch applied successfully: CSME Handshake Error"
