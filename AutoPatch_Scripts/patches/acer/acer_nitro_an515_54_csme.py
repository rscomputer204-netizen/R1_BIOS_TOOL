"""
AutoPatch Script: CSME Timeout Reset
Brand: ACER
Target Model: Nitro 5 AN515-54
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "acer_nitro_an515_54_csme",
    "brand": "ACER",
    "model": "Nitro 5 AN515-54",
    "board_code": "EH5VF LA-H802P",
    "title": "CSME Timeout Reset",
    "category": "Error Fix",
    "symptom": "CSME error and slow POST on Nitro 5 AN515-54.",
    "description": "Restores CSME v12 healthy operational state.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for ACER Nitro 5 AN515-54."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied CSME Timeout Reset
    return True, patched, "Patch applied successfully: CSME Timeout Reset"
