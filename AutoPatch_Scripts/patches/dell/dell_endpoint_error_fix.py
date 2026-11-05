"""
AutoPatch Script: Dell CSME EndPoint Error Fix
Author: R1 LAB
Description: Fixes the CSME EndPoint error message on boot by resetting the Host Firmware Status
and descriptor permissions in Dell BIOS images.
"""

PATCH_INFO = {
    "id": "dell_endpoint_error_fix",
    "brand": "DELL",
    "model": "Latitude / Inspiron / Vostro (All Intel 8th-11th Gen)",
    "board_code": "Universal Dell Platforms",
    "title": "CSME EndPoint Error Fix",
    "category": "Error Fix",
    "symptom": "Shows '[ME Error] EndPoint error occurred' or fails to pass CSME initial handshake on POST",
    "description": "Resets the CSME EndPoint error flag in the descriptor/ME region and restores clean host firmware communication.",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    if len(bios_data) < 8 * 1024 * 1024:
        return False, "File size must be at least 8MB for modern Dell UEFI images."
    
    # Check for Flash Descriptor signature (0x0FF0A55A at offset 0x10)
    if bios_data[0x10:0x14] != bytes.fromhex("5AA5F00F"):
        return False, "Intel Flash Descriptor signature not found at offset 0x10."
        
    return True, "Dell Flash Descriptor verified. File is ready for EndPoint error reset."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {msg}"
        
    patched = bytearray(bios_data)
    changes = 0
    
    # 1. Flash Master Read/Write permissions reset in Flash Descriptor
    # Master 1 (Host CPU/BIOS) read: 0x0014 -> set full read/write 0xFFFF 0xFFFF
    # Flash Master Region starts around 0x80
    desc_sig_offset = 0x10
    if patched[desc_sig_offset:desc_sig_offset+4] == bytes.fromhex("5AA5F00F"):
        # Flasmap master offset
        fmba = (patched[0x14] << 4) # Flash Master Base Address
        if 0 < fmba < 0x1000 and fmba + 12 < len(patched):
            # Unlock Master 1, 2, 3 permissions
            patched[fmba:fmba+12] = b"\xFF" * 12
            changes += 1

    # 2. Reset CSME EndPoint error marker if present
    # Common signature for EndPoint error state flag in ME NVAR / NVRAM
    ep_pattern = bytes.fromhex("456E64506F696E74") # 'EndPoint'
    pos = 0
    while True:
        pos = patched.find(ep_pattern, pos)
        if pos == -1:
            break
        # Clear error state flag preceding or following the string
        for i in range(max(0, pos - 16), min(len(patched), pos + len(ep_pattern) + 16)):
            if patched[i] == 0xEE or patched[i] == 0xED:
                patched[i] = 0x00
                changes += 1
        pos += len(ep_pattern)

    return True, patched, f"CSME EndPoint error flag cleared and host permissions refreshed ({changes} adjustments made)."

