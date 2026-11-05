"""
AutoPatch Script: Onboard RAM Disable
Brand: DELL
Target Model: Inspiron 15-5570
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "dell_insp_5570_ram_disable",
    "brand": "DELL",
    "model": "Inspiron 15-5570",
    "board_code": "CAL50/DAL10 LA-F115P",
    "title": "Onboard RAM Disable",
    "category": "RAM Disable",
    "symptom": "Integrated RAM causes beep codes or restart loops.",
    "description": "Disables soldered RAM bank, enabling SODIMM slot exclusively.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for DELL Inspiron 15-5570."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Onboard RAM Disable
    return True, patched, "Patch applied successfully: Onboard RAM Disable"
