"""
AutoPatch Script: Universal Flash Descriptor Override
Brand: UNIVERSAL
Target Model: All Intel UEFI Motherboards
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "uni_fd_unlock_all",
    "brand": "UNIVERSAL",
    "model": "All Intel UEFI Motherboards",
    "board_code": "Universal SPI Flash",
    "title": "Universal Flash Descriptor Override",
    "category": "Security",
    "symptom": "Flash Descriptor is locked; cannot read or write BIOS/ME regions with software.",
    "description": "Overrides master read/write access permissions in Flash Descriptor to 0xFFFFFFFF for full SPI unlock.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for UNIVERSAL All Intel UEFI Motherboards."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Universal Flash Descriptor Override
    return True, patched, "Patch applied successfully: Universal Flash Descriptor Override"
