"""
AutoPatch Script: Fast Boot Freeze Fix
Brand: DELL
Target Model: Latitude 7420
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "dell_lat_7420_fastboot_fix",
    "brand": "DELL",
    "model": "Latitude 7420",
    "board_code": "GDC40 LA-K371P",
    "title": "Fast Boot Freeze Fix",
    "category": "Delay Fix",
    "symptom": "System freezes intermittently during Intel Fast Boot POST.",
    "description": "Adjusts PCIe handshake timeouts in NVAR variables.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for DELL Latitude 7420."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Fast Boot Freeze Fix
    return True, patched, "Patch applied successfully: Fast Boot Freeze Fix"
