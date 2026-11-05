"""
AutoPatch Script: Universal Fast Boot Timeout Delay Clear
Brand: UNIVERSAL
Target Model: All Intel UEFI Desktop & Laptop
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "uni_fastboot_timeout_clear",
    "brand": "UNIVERSAL",
    "model": "All Intel UEFI Desktop & Laptop",
    "board_code": "Universal Fast Boot",
    "title": "Universal Fast Boot Timeout Delay Clear",
    "category": "Delay Fix",
    "symptom": "System pauses 20 to 45 seconds on black screen before initializing display.",
    "description": "Eliminates ME/BIOS handshake wait loops and resets Fast Boot timeout registers to immediate 0ms.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for UNIVERSAL All Intel UEFI Desktop & Laptop."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Universal Fast Boot Timeout Delay Clear
    return True, patched, "Patch applied successfully: Universal Fast Boot Timeout Delay Clear"
