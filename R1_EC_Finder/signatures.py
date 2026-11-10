"""
R1 EC Finder - Signatures & Pattern Definitions
================================================
Comprehensive database of signatures, vector tables, memory maps,
and boundary sizes for laptop Embedded Controllers (EC / KBC).

Supports:
- ITE (IT85xx, IT82xx, IT81xx, IT89xx)
- ENE (KB9012, KB9022, KB9028, KB930, etc.)
- Nuvoton (NPCE288, NPCE388, NPCX586, NPCX797, NPCX997)
- Microchip / SMSC (MEC1404, MEC1428, MEC1633, MEC1515, MEC5035)
- Intel Flash Descriptor (Hardware-defined EC Region)
- Vendor Headers (HP Insyde, Lenovo ThinkPad/IdeaPad, Acer, Asus)
"""

# Standard EC Binary Sizes in Bytes
EC_SIZES = [
    65536,    # 64 KB   - Legacy ITE/Winbond
    131072,   # 128 KB  - Standard ITE (IT8586/IT8585), ENE (KB9012/KB9022)
    163840,   # 160 KB  - Extended ITE / Special Lenovo
    196608,   # 192 KB  - Special ENE / Dell
    262144,   # 256 KB  - ENE KB9028, Nuvoton NPCE288/388
    327680,   # 320 KB  - Intel Flash Descriptor Defined (Dell Latitude)
    393216,   # 384 KB  - Nuvoton NPCX / Microchip
    524288,   # 512 KB  - Modern Nuvoton (NPCX797), Microchip (MEC1404/MEC1633)
    1048576,  # 1024 KB - Modern Gaming & Workstation ECs (MEC1515, ITE IT8227)
]

# Magic Strings & Vendor Header Markers
VENDOR_MARKERS = [
    {
        "name": "Insyde EC Image Marker",
        "pattern": b"$_IFLASH_EC_IMG",
        "offset_adjust": 16,
        "vendor": "Insyde / Multi-Vendor",
        "confidence": 95
    },
    {
        "name": "Insyde Flash Marker",
        "pattern": b"$_IFLASH_BIOSIMG",
        "offset_adjust": 16,
        "vendor": "Insyde / Multi-Vendor",
        "confidence": 75
    },
    {
        "name": "Lenovo EC Header Marker",
        "pattern": b"$EC_HEADER$",
        "offset_adjust": 16,
        "vendor": "Lenovo",
        "confidence": 95
    },
    {
        "name": "HP Insyde EC Block Marker",
        "pattern": b"EC_IMAGE",
        "offset_adjust": 16,
        "vendor": "HP",
        "confidence": 85
    },
    {
        "name": "Acer EC FW Block",
        "pattern": b"ACER_EC_FIRMWARE",
        "offset_adjust": 20,
        "vendor": "Acer",
        "confidence": 90
    },
    {
        "name": "Dell Embedded Controller",
        "pattern": b"DELL_EC_BINARY",
        "offset_adjust": 16,
        "vendor": "Dell",
        "confidence": 90
    }
]

# Known SRAM Base Ranges for ARM Cortex-M ECs (Initial Stack Pointer)
# Initial SP (first 4 bytes) is typically at top of SRAM
CORTEX_M_SRAM_RANGES = [
    (0x10000000, 0x10040000),  # Nuvoton NPCX internal SRAM
    (0x20000000, 0x20040000),  # Standard Cortex-M SRAM base
    (0x20010000, 0x20080000),  # Extended SRAM (MEC14xx/16xx)
    (0x10008000, 0x10020000),  # Low-power SRAM (Nuvoton/ITE)
    (0x00100000, 0x00140000),  # Microchip internal TCM
]

# 8051 Common Reset & Interrupt Jump Patterns
# 8051 instruction 0x02 = LJMP (Long Jump) followed by 16-bit address
# Often starts at 0x0000 with 02 xx xx or 00 00 00 followed by LJMP
E8051_RESET_PATTERNS = [
    b"\x02\x00\x00",
    b"\x02\x00\x10",
    b"\x02\x00\x20",
    b"\x02\x00\x30",
    b"\x02\x00\x40",
    b"\x02\x00\x60",
    b"\x02\x01\x00",
    b"\x02\x02\x00",
    b"\x02\x04\x00",
    b"\x02\x08\x00",
]

