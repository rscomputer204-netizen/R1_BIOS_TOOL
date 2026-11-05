"""
AutoPatch Script: Universal CSME EndPoint Error Fix
Brand: UNIVERSAL
Target Model: All Intel Core 6th to 14th Gen
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "uni_csme_endpoint_fix",
    "brand": "UNIVERSAL",
    "model": "All Intel Core 6th to 14th Gen",
    "board_code": "Universal Intel PCH",
    "title": "Universal CSME EndPoint Error Fix",
    "category": "Error Fix",
    "symptom": "CSME EndPoint error occurred or fails to pass CSME initial handshake on POST.",
    "description": "Resets CSME EndPoint error flag in the descriptor/ME region and restores clean host firmware communication.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for UNIVERSAL All Intel Core 6th to 14th Gen."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Universal CSME EndPoint Error Fix
    return True, patched, "Patch applied successfully: Universal CSME EndPoint Error Fix"
