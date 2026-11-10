"""
R1 EC Finder - Intelligent Carver & Detection Engine
=====================================================
Analyzes binary dumps, update packages, and ROMs to locate,
rank, and carve clean Embedded Controller (EC / KBC) firmware blocks.

Engine Pipeline:
1. Intel Flash Descriptor (FD) Region 8 Detection (Hardware Guarantee)
2. ARM Cortex-M Vector Table Scanner (Nuvoton / Microchip / Realtek)
3. 8051 Interrupt Vector Scanner (ITE / ENE)
4. Vendor Header Pattern Matching (Insyde / HP / Lenovo / Acer / Dell)
5. Shannon Entropy & Code Density Validation
6. Multi-Candidate Ranking & Auto-Deduplication
"""

import os
import math
import struct
from typing import List, Dict, Any, Tuple, Optional
from .signatures import (
    EC_SIZES,
    VENDOR_MARKERS,
    CORTEX_M_SRAM_RANGES,
    E8051_RESET_PATTERNS
)


def calc_shannon_entropy(data: bytes) -> float:
    """Calculates Shannon entropy of byte data (0.0 = uniform/empty, 8.0 = random/compressed)."""
    if not data:
        return 0.0
    freq = [0] * 256
    for b in data:
        freq[b] += 1
    total = len(data)
    entropy = 0.0
    for count in freq:
        if count > 0:
            p = count / total
            entropy -= p * math.log2(p)
    return entropy


class ECCandidate:
    """Represents a detected EC candidate block with metadata and confidence scoring."""

    def __init__(self, offset: int, size: int, chip_family: str, detection_method: str, confidence: int, notes: str = ""):
        self.offset = offset
        self.size = size
        self.chip_family = chip_family
        self.detection_method = detection_method
        self.confidence = min(100, max(0, confidence))
        self.notes = notes
        self.entropy: float = 0.0
        self.sha256: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "offset": self.offset,
            "offset_hex": f"0x{self.offset:08X}",
            "size": self.size,
            "size_kb": self.size // 1024,
            "size_str": f"{self.size / 1024:.0f} KB" if self.size < 1048576 else f"{self.size / (1024*1024):.2f} MB",
            "chip_family": self.chip_family,
            "detection_method": self.detection_method,
            "confidence": self.confidence,
            "notes": self.notes,
            "entropy": round(self.entropy, 2)
        }


class ECCarverEngine:
    """Core detection engine for Embedded Controller firmware."""

    def __init__(self, buffer: bytes):
        self.buffer = buffer
        self.total_size = len(buffer)
        self.candidates: List[ECCandidate] = []

    def scan(self) -> List[ECCandidate]:
        """Runs all detection strategies and returns ranked candidates."""
        self.candidates.clear()

        # Strategy 1: Intel Flash Descriptor (Region 8 = EC)
        self._scan_intel_flash_descriptor()

        # Strategy 2: Vendor Markers & Insyde Headers
        self._scan_vendor_markers()

        # Strategy 3: ARM Cortex-M Vector Tables (Nuvoton NPCX / Microchip MEC)
        self._scan_cortex_m_vectors()

        # Strategy 4: 8051 Jump & Vector Tables (ITE IT85xx / ENE KB90xx)
        self._scan_8051_vectors()

        # Deduplicate, compute entropy, and rank
        results = self._finalize_candidates()
        return results

    # ── Strategy 1: Intel Flash Descriptor (Region 8) ────────────────
    def _scan_intel_flash_descriptor(self):
        if self.total_size < 0x1000:
            return

        # Check descriptor magic signature at offset 0x10: 0x0FF0A55A
        magic_pos = self.buffer.find(b"\x5a\xa5\xf0\x0f")
        if magic_pos == -1 or magic_pos > 0x100:
            return

        desc_base = max(0, magic_pos - 0x10)
        # Read Flash Region Base Address (FRBA) offset at descriptor base + 0x14
        if desc_base + 0x18 > self.total_size:
            return

        flmap0 = struct.unpack("<I", self.buffer[desc_base + 0x14 : desc_base + 0x18])[0]
        frba = ((flmap0 >> 12) & 0xFF) << 4

        # In modern CSME (100-series through 700-series), Region 8 is EC Region
        # Region entries are 4 bytes each: [15:0] Base, [31:16] Limit
        # Region 8 is at frba + (8 * 4) = frba + 0x20
        reg8_offset = desc_base + frba + 0x20
        if reg8_offset + 4 <= self.total_size:
            reg8_val = struct.unpack("<I", self.buffer[reg8_offset : reg8_offset + 4])[0]
            base_blocks = reg8_val & 0x7FFF
            limit_blocks = (reg8_val >> 16) & 0x7FFF
            if 0 < base_blocks < limit_blocks:
                ec_start = base_blocks << 12
                ec_limit = (limit_blocks << 12) | 0xFFF
                ec_size = (ec_limit - ec_start) + 1

                if ec_start + ec_size <= self.total_size and ec_size >= 0x10000:
                    cand = ECCandidate(
                        offset=ec_start,
                        size=ec_size,
                        chip_family="Intel Flash Descriptor Region 8 (Hardware Defined)",
                        detection_method="Intel FD Hardware Map",
                        confidence=100,
                        notes=f"Hardware-locked EC Region (Base: 0x{ec_start:X}, Size: {ec_size // 1024} KB)"
                    )
                    self.candidates.append(cand)

    # ── Strategy 2: Vendor Header Markers ────────────────────────────
    def _scan_vendor_markers(self):
        for vm in VENDOR_MARKERS:
            pattern = vm["pattern"]
            pos = 0
            while True:
                idx = self.buffer.find(pattern, pos)
                if idx == -1:
                    break
                pos = idx + len(pattern)

                cand_start = idx + vm["offset_adjust"]
                # Align candidate to 0x10 or 0x100
                cand_start = (cand_start + 15) & ~15

                for sz in EC_SIZES:
                    if cand_start + sz <= self.total_size:
                        cand = ECCandidate(
                            offset=cand_start,
                            size=sz,
                            chip_family=f"{vm['vendor']} Payload",
                            detection_method=f"Marker: {vm['name']}",
                            confidence=vm["confidence"],
                            notes=f"Located immediately following header marker '{pattern.decode('ascii', errors='ignore')}'"
                        )
                        self.candidates.append(cand)

    # ── Strategy 3: ARM Cortex-M Vector Tables ──────────────────────
    def _scan_cortex_m_vectors(self):
        """
        Detects modern 32-bit ARM Cortex-M embedded controllers
        (Nuvoton NPCX586/NPCX797, Microchip MEC1404/MEC1633, Realtek).
        """
        step = 0x100  # Scan aligned to 256 bytes for performance & precision
        limit = min(self.total_size - 0x10000, 32 * 1024 * 1024)

        for off in range(0, limit, step):
            # Check 16 bytes: SP (Word 0) and Reset Handler (Word 1)
            chunk = self.buffer[off : off + 16]
            if len(chunk) < 16:
                continue

            sp, reset_h = struct.unpack("<II", chunk[:8])

            # SP must be 4-byte aligned (bits 0,1 == 0)
            if (sp & 3) != 0:
                continue

            # Verify SP falls in known microcontroller internal SRAM bounds
            valid_sram = False
            for s_start, s_end in CORTEX_M_SRAM_RANGES:
                if s_start <= sp <= s_end:
                    valid_sram = True
                    break

            if not valid_sram:
                continue

            # Reset handler must have Thumb bit set (bit 0 == 1)
            if (reset_h & 1) != 1:
                continue

            reset_code_addr = reset_h & ~1
            # Reset code must point within local flash memory space
            # Cortex-M vectors typically map flash at 0x00000000 or 0x10000000
            local_offset = reset_code_addr & 0x000FFFFF
            if local_offset < 8 or local_offset > 0x100000:
                continue

            # Check next two vectors: NMI (Word 2) and HardFault (Word 3)
            nmi, hf = struct.unpack("<II", chunk[8:16])
            if (nmi & 1) != 1 or (hf & 1) != 1:
                continue

            # Valid ARM Cortex-M vector table found!
            # Test applicable standard sizes: 256KB, 384KB, 512KB, 1MB
            for test_sz in [262144, 393216, 524288, 1048576]:
                if off + test_sz <= self.total_size:
                    block_ent = calc_shannon_entropy(self.buffer[off : off + min(test_sz, 65536)])
                    if block_ent >= 4.5:
                        cand = ECCandidate(
                            offset=off,
                            size=test_sz,
                            chip_family="Nuvoton NPCX / Microchip MEC (ARM Cortex-M)",
                            detection_method="Cortex-M Vector Table",
                            confidence=92 if test_sz in (524288, 1048576) else 82,
                            notes=f"Initial SP: 0x{sp:08X}, Reset Vector: 0x{reset_h:08X}"
                        )
                        self.candidates.append(cand)
                        break

    # ── Strategy 4: 8051 / ITE / ENE Jump Vectors ───────────────────
    def _scan_8051_vectors(self):
        """
        Detects 8051-based embedded controllers (ITE IT8586E, ENE KB9012, etc.).
        """
        step = 0x100
        limit = min(self.total_size - 0x10000, 32 * 1024 * 1024)

        for off in range(0, limit, step):
            head_3 = self.buffer[off : off + 3]
            if head_3 in E8051_RESET_PATTERNS:
                # In 8051, 0x02 is LJMP (3 bytes)
                # Check for secondary interrupt vectors around 0x03, 0x0B, 0x13
                sub_chunk = self.buffer[off : off + 0x40]
                ljmp_count = sub_chunk.count(b"\x02")
                if ljmp_count >= 2:
                    # Check entropy of first 32KB
                    ent = calc_shannon_entropy(self.buffer[off : off + 32768])
                    if 4.2 <= ent <= 7.8:
                        # Standard 8051 sizes are 128KB, 160KB, 256KB
                        for sz in [131072, 163840, 262144]:
                            if off + sz <= self.total_size:
                                cand = ECCandidate(
                                    offset=off,
                                    size=sz,
                                    chip_family="ITE IT85xx / ENE KB90xx (8051 Core)",
                                    detection_method="8051 LJMP Vector Structure",
                                    confidence=88 if sz == 131072 else 78,
                                    notes=f"Found 8051 LJMP vector table at offset 0x{off:X}"
                                )
                                self.candidates.append(cand)
                                break

    # ── Post-Processing & Ranking ────────────────────────────────────
    def _finalize_candidates(self) -> List[ECCandidate]:
        """Calculates entropy, validates, deduplicates, and ranks candidates."""
        unique_map: Dict[Tuple[int, int], ECCandidate] = {}

        for c in self.candidates:
            key = (c.offset, c.size)
            if key in unique_map:
                if c.confidence > unique_map[key].confidence:
                    unique_map[key] = c
            else:
                unique_map[key] = c

        validated: List[ECCandidate] = []
        for c in unique_map.values():
            if c.offset + c.size > self.total_size:
                continue

            # Calculate entropy of the full carved block
            data_sample = self.buffer[c.offset : c.offset + c.size]
            c.entropy = calc_shannon_entropy(data_sample)

            # Eliminate flat empty blocks (all 0x00 or all 0xFF)
            if c.entropy < 1.0:
                continue

            # Penalty for suspicious entropy
            if c.entropy < 3.5:
                c.confidence -= 20
            elif c.entropy > 7.95:
                # Likely encrypted or compressed
                c.notes += " (High Entropy / Likely Compressed or Encrypted)"

            validated.append(c)

        # Sort by confidence DESC, then offset ASC
        validated.sort(key=lambda x: (x.confidence, -x.offset), reverse=True)
        return validated

