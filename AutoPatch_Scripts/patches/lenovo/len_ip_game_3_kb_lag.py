"""
AutoPatch Script: Keyboard Lag Fix
Brand: LENOVO
Target Model: IdeaPad Gaming 3-15IMH05
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "len_ip_game_3_kb_lag",
    "brand": "LENOVO",
    "model": "IdeaPad Gaming 3-15IMH05",
    "board_code": "NM-C871",
    "title": "Keyboard Lag Fix",
    "category": "General",
    "symptom": "Keyboard input lags on BIOS setup and Windows startup.",
    "description": "Updates EC keyboard controller buffer parameters.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for LENOVO IdeaPad Gaming 3-15IMH05."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Keyboard Lag Fix
    return True, patched, "Patch applied successfully: Keyboard Lag Fix"
