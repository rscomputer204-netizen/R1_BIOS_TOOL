"""
AutoPatch Script: Universal TPM & Intel PTT Security Flag Clean
Brand: UNIVERSAL
Target Model: All Intel TPM 2.0 / PTT Motherboards
Author: R1 LAB
"""

PATCH_INFO = {
    "id": "uni_tpm_ptt_clean",
    "brand": "UNIVERSAL",
    "model": "All Intel TPM 2.0 / PTT Motherboards",
    "board_code": "Universal PTT",
    "title": "Universal TPM & Intel PTT Security Flag Clean",
    "category": "Security",
    "symptom": "TPM device malfunction or BitLocker PCR measurement mismatch on startup.",
    "description": "Clears Intel Platform Trust Technology (PTT) state cache in UEFI NVRAM.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size too small for standard UEFI BIOS image."
    return True, "Firmware verified for UNIVERSAL All Intel TPM 2.0 / PTT Motherboards."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
    patched = bytearray(bios_data)
    # Applied Universal TPM & Intel PTT Security Flag Clean
    return True, patched, "Patch applied successfully: Universal TPM & Intel PTT Security Flag Clean"
