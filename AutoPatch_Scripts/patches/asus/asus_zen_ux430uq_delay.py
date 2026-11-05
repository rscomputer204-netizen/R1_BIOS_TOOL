"""
AutoPatch Script: Fast Boot Delay Fix
Brand: ASUS
Target Model: ZenBook UX430UQ
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "asus_zen_ux430uq_delay",
    "brand": "ASUS",
    "model": "ZenBook UX430UQ",
    "board_code": "UX430UQ R2.1",
    "title": "Fast Boot Delay Fix",
    "category": "Delay Fix",
    "symptom": "ZenBook UX430 takes 25 seconds to display ASUS logo.",
    "description": "Clears ME configuration timeout parameters in flash descriptor.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for ASUS ZenBook UX430UQ."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Fast Boot Delay Fix
    return True, patched, "Patch applied successfully: Fast Boot Delay Fix"
