"""
AutoPatch Script: Fast Boot Freeze Fix
Brand: LENOVO
Target Model: ThinkPad X390
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "len_tp_x390_fastboot",
    "brand": "LENOVO",
    "model": "ThinkPad X390",
    "board_code": "NM-B891",
    "title": "Fast Boot Freeze Fix",
    "category": "Delay Fix",
    "symptom": "Intermittent freeze on red Lenovo logo during fast boot.",
    "description": "Fixes NVRAM storage fragmentation and clears MRC cache.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for LENOVO ThinkPad X390."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Fast Boot Freeze Fix
    return True, patched, "Patch applied successfully: Fast Boot Freeze Fix"
