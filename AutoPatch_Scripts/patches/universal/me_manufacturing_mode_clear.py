"""
AutoPatch Script: Universal Intel CSME Manufacturing Mode 0x33 Warning Clear
Author: R1 LAB
Description: Closes Intel ME/CSME Manufacturing Mode and suppresses the 0x33 warning prompt
during initial boot.
"""

PATCH_INFO = {
    "id": "me_manufacturing_mode_clear",
    "brand": "UNIVERSAL",
    "model": "All Intel Core 4th to 14th Gen",
    "board_code": "Universal",
    "title": "Manufacturing Mode 0x33 Warning Clear",
    "category": "General",
    "symptom": "Sets the ME Manufacturing Mode flag to closed/disabled in Flash Partition Table and NVAR settings to suppress the 0x33 warning.",
    "description": "Sets the ME Manufacturing Mode flag to closed/disabled in Flash Partition Table and NVAR settings to suppress the 0x33 warning.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [4, 8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size must be at least 4MB."
    
    # Check for FPT header or ME region marker
    if b"$FPT" not in bios_data and bytes.fromhex("5AA5F00F") not in bios_data:
        return False, "No Intel Flash Descriptor or $FPT partition table found."
        
    return True, "Intel ME partition headers verified. Ready to close Manufacturing Mode."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
        
    patched = bytearray(bios_data)
    count = 0
    
    # Search for $FPT marker
    fpt_pos = patched.find(b"$FPT")
    if fpt_pos != -1:
        # FPT Flags are at offset 0x1C from $FPT
        flags_offset = fpt_pos + 0x1C
        if flags_offset + 4 < len(patched):
            # Bit 0 of FPT flags: 1 = Manufacturing Mode Open, 0 = Closed
            flags = patched[flags_offset]
            if flags & 0x01:
                patched[flags_offset] = flags & (~0x01)
                count += 1
                
    # Also search for 'MfgMode' string in NVRAM variables
    mfg_marker = b"MfgMode"
    pos = 0
    while True:
        pos = patched.find(mfg_marker, pos)
        if pos == -1:
            break
        # Null out or disable following value byte
        val_idx = pos + len(mfg_marker) + 4
        if val_idx < len(patched):
            if patched[val_idx] != 0:
                patched[val_idx] = 0
                count += 1
        pos += len(mfg_marker)
        
    return True, patched, f"Manufacturing mode flags set to closed ({count} locations updated). Error 0x33 suppressed."

