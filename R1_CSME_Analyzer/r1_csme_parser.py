#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
     R1 NEXT-GEN CSME / ME ANALYZER ENGINE (STANDALONE ARCHITECTURE)
================================================================================
Author: Antigravity & R1 LAB
Purpose: High-speed, in-memory pure binary Intel ME / CSME firmware analyzer.
         Native support for CSME v11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 21+
         Modular Reporting Architecture:
           - Default Mode: Clean 12-line summary (< 0.05s)
           - Advanced Flags:
             * --spi-map     : SPI Flash Descriptor Regions
             * --fpt         : Flash Partition Table ($FPT)
             * --microcode   : Intel CPU Microcode Audit
             * --pmc-pch     : PMC / PCHC / PHY Sub-firmware info
             * --all         : Full diagnostic report
================================================================================
"""

import os
import sys
import glob
import time
import struct
import shlex
import re
import hashlib
import ctypes
from pathlib import Path

# Common Signatures
SIG_FPT = b"$FPT"
SIG_MN2 = b"$MN2"
SIG_MAN = b"$MAN"
SIG_CPD = b"$CPD"
SIG_FIT = b"_FIT_   "
SIG_FD  = b"\x5A\xA5\xF0\x0F"
SIG_SKU = b"$SKU"

# Pre-CSE $SKU Structures
class SKU_Attributes_Flags(ctypes.BigEndianStructure):
    _fields_ = [
        ('Value1', ctypes.c_uint64, 24),
        ('Value2', ctypes.c_uint64, 1), # Slim (ME 7)
        ('Value3', ctypes.c_uint64, 1),
        ('Value4', ctypes.c_uint64, 1),
        ('Value5', ctypes.c_uint64, 1),
        ('Value6', ctypes.c_uint64, 1),
        ('Value7', ctypes.c_uint64, 1),
        ('Value8', ctypes.c_uint64, 1),
        ('Value9', ctypes.c_uint64, 1),
        ('Patsburg', ctypes.c_uint64, 1), # 0 No, 1 Yes (ME 7-8)
        ('SKUType', ctypes.c_uint64, 3), # 0 Corporate, 1 Consumer, 2 Slim (ME 9-10)
        ('SKUSize', ctypes.c_uint64, 4), # Size * 0.5MB (ME 7-10, TXE 0-2)
        ('Value10', ctypes.c_uint64, 24)
    ]

class SKU_Union(ctypes.Union):
    _fields_ = [('b', SKU_Attributes_Flags), ('asbytes', ctypes.c_uint64)]

# Global MEA Database Cache
_MEA_DB_CACHE = None

def get_mea_db():
    global _MEA_DB_CACHE
    if _MEA_DB_CACHE is not None:
        return _MEA_DB_CACHE
    _MEA_DB_CACHE = {}
    base_dir = Path(__file__).resolve().parent
    search_paths = [
        base_dir.parent / "external" / "MEAnalyzer" / "MEA.dat",
        base_dir / "external" / "MEAnalyzer" / "MEA.dat",
        Path(r"d:\BIOS_-TOOL\external\MEAnalyzer\MEA.dat"),
        Path(r"d:\BIOS_-TOOL\dist\R1_BIOS_TOOL\_internal\external\MEAnalyzer\MEA.dat"),
    ]
    for p in search_paths:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if "_" in line and len(line) > 64:
                            parts = line.rsplit("_", 1)
                            if len(parts) == 2 and len(parts[1]) == 64:
                                _MEA_DB_CACHE[parts[1].upper()] = parts[0]
                break
            except Exception:
                pass
    return _MEA_DB_CACHE

# CPU Architecture Mapping by CPUID
CPUID_MAP = {
    # 15th / 16th Gen Core Ultra (Arrow Lake / Lunar Lake)
    "000C0650": ("Arrow Lake (15th Gen)", "Arrow Lake S"),
    "000C0651": ("Arrow Lake (15th Gen)", "Arrow Lake S"),
    "000C0652": ("Arrow Lake (15th Gen)", "Arrow Lake S"),
    "000C0660": ("Arrow Lake (15th Gen)", "Arrow Lake H"),
    "000C0670": ("Arrow Lake (15th Gen)", "Arrow Lake U"),
    "000B06D0": ("Lunar Lake (Core Ultra 2)", "Lunar Lake M"),
    "000B06D1": ("Lunar Lake (Core Ultra 2)", "Lunar Lake M"),
    "000D0600": ("Panther Lake (Next-Gen)", "PTL A"),
    "000D0601": ("Panther Lake (Next-Gen)", "PTL A"),

    # 14th Gen / Core Ultra 1 (Meteor Lake)
    "000706E5": ("Meteor Lake (14th Gen)", "Meteor Lake P"),
    "000A06A0": ("Meteor Lake (14th Gen)", "Meteor Lake S"),
    "000A06A1": ("Meteor Lake (14th Gen)", "Meteor Lake P"),
    "000A06A2": ("Meteor Lake (14th Gen)", "Meteor Lake P"),
    "000A06A4": ("Meteor Lake (14th Gen)", "Meteor Lake P"),

    # 13th / 14th Gen Raptor Lake
    "000B0670": ("Raptor Lake (13th Gen)", "RPL-S B"),
    "000B0671": ("Raptor Lake (13th/14th Gen)", "RPL-S B"),
    "000B06A0": ("Raptor Lake (13th/14th Gen)", "RPL-HX B"),
    "000B06F2": ("Raptor Lake (13th/14th Gen)", "RPL-P B"),
    "000B06F5": ("Raptor Lake (13th/14th Gen)", "RPL-P B"),

    # 12th Gen Alder Lake
    "00090670": ("Alder Lake (12th Gen)", "ADP-S A"),
    "00090671": ("Alder Lake (12th Gen)", "ADP-S A"),
    "00090672": ("Alder Lake (12th Gen)", "ADP-P/M B"),
    "00090674": ("Alder Lake (12th Gen)", "ADP-P/M B"),
    "00090675": ("Alder Lake (12th Gen)", "ADP-S A"),
    "000906A0": ("Alder Lake (12th Gen)", "ADP-M A"),
    "000906A1": ("Alder Lake (12th Gen)", "ADP-M A"),
    "000906A2": ("Alder Lake (12th Gen)", "ADP-M A"),
    "000906A3": ("Alder Lake (12th Gen)", "ADP-M A"),
    "000906A4": ("Alder Lake (12th Gen)", "ADP-M A"),

    # 11th Gen Tiger Lake & Rocket Lake
    "000806C0": ("Tiger Lake (11th Gen)", "TGP-LP B"),
    "000806C1": ("Tiger Lake (11th Gen)", "TGP-LP B"),
    "000806C2": ("Tiger Lake (11th Gen)", "TGP-H A"),
    "000806D0": ("Tiger Lake (11th Gen)", "TGP-LP B"),
    "000806D1": ("Tiger Lake (11th Gen)", "TGP-LP B"),
    "000806D2": ("Tiger Lake (11th Gen)", "TGP-LP B"),
    "000A0670": ("Rocket Lake (11th Gen)", "RKL-S A"),
    "000A0671": ("Rocket Lake (11th Gen)", "RKL-S A"),

    # 10th Gen Comet Lake & Ice Lake
    "000A0650": ("Comet Lake (10th Gen)", "CMP-U A"),
    "000A0651": ("Comet Lake (10th Gen)", "CMP-U A"),
    "000A0652": ("Comet Lake (10th Gen)", "CMP-H A"),
    "000A0653": ("Comet Lake (10th Gen)", "CMP-H A"),
    "000A0654": ("Comet Lake (10th Gen)", "CMP-H A"),
    "000A0655": ("Comet Lake (10th Gen)", "CMP-H A"),

    # 8th / 9th Gen Coffee Lake / Whiskey Lake / Cannon Lake
    "000906EA": ("Coffee Lake (8th/9th Gen)", "CNP-H B"),
    "000906EB": ("Coffee Lake (8th/9th Gen)", "CNP-H B"),
    "000906EC": ("Coffee Lake (8th/9th Gen)", "CNP B"),
    "000906ED": ("Coffee Lake (8th/9th Gen)", "CNP B"),
    "000806EB": ("Whiskey Lake (8th Gen)", "CNP-LP B"),
    "000806EC": ("Whiskey Lake (8th Gen)", "CNP-LP B"),
    "00060660": ("Cannon Lake (8th Gen)", "CNP-LP B"),

    # 6th / 7th Gen Skylake / Kaby Lake
    "000406E3": ("Skylake (6th Gen)", "SPT-LP B"),
    "000406E8": ("Skylake (6th Gen)", "SPT-LP B"),
    "000506E3": ("Skylake (6th Gen)", "SPT-H B"),
    "000806E9": ("Kaby Lake (7th Gen)", "SPT/KBP-LP C"),
    "000806EA": ("Kaby Lake (7th Gen)", "SPT/KBP-LP C"),
    "000906E9": ("Kaby Lake (7th Gen)", "KBP-S B"),

    # 4th / 5th Gen Haswell / Broadwell
    "000306D2": ("Broadwell (5th Gen)", "WPT-LP"),
    "000306D3": ("Broadwell (5th Gen)", "WPT-LP"),
    "000306D4": ("Broadwell (5th Gen)", "WPT-LP"),
    "00040650": ("Broadwell (5th Gen)", "WPT-LP"),
    "00040651": ("Broadwell (5th Gen)", "WPT-LP"),
    "00040671": ("Broadwell (5th Gen)", "WPT"),
    "000306C1": ("Haswell (4th Gen)", "LPT"),
    "000306C2": ("Haswell (4th Gen)", "LPT"),
    "000306C3": ("Haswell (4th Gen)", "LPT"),
    "00040661": ("Haswell (4th Gen)", "LPT-LP"),

    # 2nd / 3rd Gen Sandy Bridge / Ivy Bridge
    "000306A8": ("Ivy Bridge (3rd Gen)", "PPT"),
    "000306A9": ("Ivy Bridge (3rd Gen)", "PPT"),
    "000306E4": ("Ivy Bridge (3rd Gen)", "PPT"),
    "000206A7": ("Sandy Bridge (2nd Gen)", "CPT"),
    "000206D6": ("Sandy Bridge (2nd Gen)", "CPT"),
    "000206D7": ("Sandy Bridge (2nd Gen)", "CPT"),

    # Atom / Celeron / Pentium (TXE / CSE)
    "00090660": ("Elkhart Lake (Atom/Celeron)", "EHL"),
    "00090661": ("Elkhart Lake (Atom/Celeron)", "EHL"),
    "000906C0": ("Jasper Lake (Celeron/Pentium)", "JSL"),
    "000706A1": ("Gemini Lake (Atom)", "GLK"),
    "000706A8": ("Gemini Lake (Atom)", "GLK"),
    "000506C2": ("Apollo Lake (Atom)", "APL"),
    "000506C9": ("Apollo Lake (Atom)", "APL"),
    "000406C3": ("Braswell / Cherry Trail", "BSW/CHT"),
    "000406C4": ("Braswell / Cherry Trail", "BSW/CHT"),
    "00030673": ("Bay Trail", "BYT"),
    "00030678": ("Bay Trail", "BYT"),
    "00030679": ("Bay Trail", "BYT"),

    # Xeon Scalable / Enterprise
    "000806F4": ("Sapphire Rapids (Xeon)", "SPR-SP"),
    "000806F5": ("Sapphire Rapids (Xeon)", "SPR-SP"),
    "000C06F1": ("Emerald Rapids (Xeon)", "EMR-SP"),
    "000606A4": ("Ice Lake SP (Xeon)", "ICX-SP"),
    "00050654": ("Cascade Lake (Xeon)", "CLX-SP"),
    "00050650": ("Skylake SP (Xeon)", "SKX-SP"),
}

GEN_RANK = {
    "arrow lake": 16,
    "lunar lake": 15,
    "panther lake": 15,
    "meteor lake": 14,
    "raptor lake": 13,
    "alder lake": 12,
    "tiger lake": 11,
    "rocket lake": 11,
    "comet lake": 10,
    "ice lake": 10,
    "coffee lake": 9,
    "whiskey lake": 8,
    "cannon lake": 8,
    "kaby lake-r": 8,
    "kaby lake": 7,
    "skylake": 6,
    "broadwell": 5,
    "haswell": 4,
    "ivy bridge": 3,
    "sandy bridge": 2,
    "sapphire rapids": 14,
    "emerald rapids": 15,
    "granite rapids": 16,
    "elkhart lake": 10,
    "jasper lake": 10,
    "gemini lake": 8,
    "apollo lake": 6,
    "braswell": 4,
    "bay trail": 3,
}

GEN_FAMILY_MAP = {
    2: ("Intel ME (Legacy)", "ICH8"),
    3: ("Intel ME (Legacy)", "ICH9"),
    4: ("Intel ME (Legacy)", "ICH10"),
    5: ("Intel ME (Legacy)", "Ibex Peak"),
    6: ("Intel ME (5 Series)", "Ibex Peak"),
    7: ("Intel ME (6 Series)", "Cougar Point"),
    8: ("Intel ME (7 Series)", "Panther Point"),
    9: ("Intel ME (8 Series)", "Lynx Point"),
    10: ("Intel ME (9 Series)", "Wildcat Point"),
    11: ("Skylake / Kaby Lake (6th/7th Gen)", "SPT-LP B"),
    12: ("Coffee Lake / Cannon Lake (8th/9th Gen)", "CNP-LP B"),
    13: ("Ice Lake (10th Gen)", "ICL-LP A"),
    14: ("Comet Lake (10th Gen)", "CMP-LP A"),
    15: ("Tiger Lake (11th Gen)", "TGP-LP B"),
    16: ("Alder Lake / Raptor Lake (12th/13th/14th Gen)", "ADP-P/M B"),
    17: ("Meteor Lake (14th Gen)", "Meteor Lake P"),
    18: ("Meteor Lake (14th Gen)", "Meteor Lake P"),
    19: ("Arrow Lake / Lunar Lake (15th Gen)", "Arrow Lake"),
    20: ("Panther Lake (Next-Gen)", "PTL A"),
    21: ("Nova Lake (Next-Gen)", "NVL A"),
    22: ("Next-Gen Intel CSME 22+", "GEN22 A"),
}

SKU_CODE_MAP = {
    1: ("Corporate", "COR"),
    2: ("Consumer", "CON"),
    3: ("Slim", "SLM"),
    4: ("Lite", "LIT"),
    5: ("Server", "SVR"),
}


class R1CSMEAnalyzer:
    def __init__(self, bios_path: str):
        self.bios_path = bios_path
        self.raw_data = None
        self.file_size = 0
        self.info = {
            "filename": Path(bios_path).name,
            "cpu_gen": "Intel | Unknown Generation",
            "cpuids": [],
            "family": "CSE ME",
            "version": "Unknown",
            "major": 0,
            "minor": 0,
            "hotfix": 0,
            "build": 0,
            "sku": "Unknown",
            "sku_code": "UNK",
            "chipset": "Unknown",
            "stepping": "Unknown",
            "oem_config": "No",
            "date": "Unknown",
            "size_hex": "0x0",
            "fs_stage": "Unconfigured",
            "fs_state": "Unconfigured",
            "fitc_ver": "N/A",
            "full_tag": "Unknown",
            "is_valid_me": False,
            "is_stock_rgn": False,
            "rsa_sig_hash": "",
            "pdm": "No",
            "me_fd_start": 0,
            "me_fd_end": 0,
            # Extended metadata (computed on-demand)
            "spi_regions": [],
            "fpt_entries": [],
            "microcodes": [],
            "sub_firmwares": {},
            "pmc_version": "N/A",
            "pchc_version": "N/A",
            "phy_version": "N/A",
            "warnings": []
        }

    def parse(self) -> dict:
        try:
            with open(self.bios_path, "rb") as f:
                self.raw_data = f.read()
            self.file_size = len(self.raw_data)

            self._parse_fit_cpuids()
            self._parse_flash_descriptor()
            self._parse_manifest()
            self._parse_extension_sku()
            self._parse_fpt_and_size()
            self._parse_sub_firmwares()
            self._build_full_tag()

        except Exception as e:
            self.info["error"] = str(e)
            self.info["warnings"].append(f"Parser error: {e}")

        return self.info

    def _parse_fit_cpuids(self):
        data = self.raw_data
        flen = len(data)
        if flen < 64:
            return

        fit_ptr = struct.unpack("<I", data[flen-64 : flen-60])[0]
        fit_off = fit_ptr & (flen - 1)

        if fit_off + 16 <= flen and data[fit_off:fit_off+8] == SIG_FIT:
            num_entries = struct.unpack("<I", data[fit_off+8 : fit_off+12])[0] & 0x00FFFFFF
            if 0 < num_entries < 128:
                cpuids = []
                for i in range(num_entries):
                    entry_off = fit_off + i * 16
                    if entry_off + 16 > flen:
                        break
                    e = data[entry_off : entry_off + 16]
                    addr = struct.unpack("<Q", e[:8])[0] & (flen - 1)
                    etype = e[14] & 0x7F
                    if etype == 1:  # Microcode Entry
                        if addr + 48 <= flen:
                            hdr_bytes = data[addr : addr + 48]
                            # Intel Microcode Header:
                            # +4: rev (uint32)
                            # +8: date (BCD: day, month, year_high, year_low)
                            # +12: cpuid (uint32)
                            # +24: platform (uint32)
                            # +32: size (uint32)
                            rev = struct.unpack("<I", hdr_bytes[4:8])[0]
                            cpuid = struct.unpack("<I", hdr_bytes[12:16])[0]
                            plat = struct.unpack("<I", hdr_bytes[24:28])[0]
                            sz = struct.unpack("<I", hdr_bytes[32:36])[0]
                            if sz == 0:
                                sz = 2048

                            # Date BCD: Intel Microcode header date is stored at +8..12
                            # bytes: [year_low, year_high, day, month]
                            mc_yr = f"{hdr_bytes[9]:02X}{hdr_bytes[8]:02X}"
                            mc_day = f"{hdr_bytes[10]:02X}"
                            mc_mon = f"{hdr_bytes[11]:02X}"
                            mc_date = f"{mc_yr}-{mc_mon}-{mc_day}"

                            cpuid_hex = f"{cpuid:08X}"
                            if cpuid_hex not in ["00000000", "FFFFFFFF"]:
                                cpuids.append(cpuid_hex)
                                self.info["microcodes"].append({
                                    "cpuid": cpuid_hex,
                                    "platform": f"0x{plat:02X}",
                                    "revision": f"0x{rev:08X}",
                                    "date": mc_date,
                                    "size": f"0x{sz:X}"
                                })

                unique_cpuids = sorted(list(set(cpuids)))
                self.info["cpuids"] = unique_cpuids
                if unique_cpuids:
                    best_rank = -1
                    best_gen = None
                    best_chipset = None
                    for cid in unique_cpuids:
                        if cid in CPUID_MAP:
                            gen_str, chipset_val = CPUID_MAP[cid]
                            rank = 0
                            for k, r in GEN_RANK.items():
                                if k in gen_str.lower():
                                    rank = max(rank, r)
                            if rank > best_rank:
                                best_rank = rank
                                best_gen = gen_str
                                best_chipset = chipset_val
                    if best_gen:
                        self.info["cpu_gen"] = f"Intel | {best_gen} | {', '.join(unique_cpuids)}"
                        self.info["chipset"] = best_chipset
                        return
                    self.info["cpu_gen"] = f"Intel | Generic Intel x86 | {', '.join(unique_cpuids)}"
                    return

        # Fallback Direct Microcode Scan (for truncated dumps, split chips, or missing FIT pointers)
        direct_cpuids = []
        for i in range(0, flen - 48, 16):
            hdr_ver = struct.unpack("<I", data[i:i+4])[0]
            ldr_rev = struct.unpack("<I", data[i+20:i+24])[0]
            if hdr_ver == 1 and ldr_rev == 1:
                rev = struct.unpack("<I", data[i+4:i+8])[0]
                cpuid = struct.unpack("<I", data[i+12:i+16])[0]
                plat = struct.unpack("<I", data[i+24:i+28])[0]
                sz = struct.unpack("<I", data[i+32:i+36])[0] or 2048
                if 2048 <= sz <= 262144 and i + sz <= flen:
                    total_sum = sum(struct.unpack(f"<{sz//4}I", data[i:i+sz])) & 0xFFFFFFFF
                    if total_sum == 0:
                        cpuid_hex = f"{cpuid:08X}"
                        if cpuid_hex not in ["00000000", "FFFFFFFF"]:
                            direct_cpuids.append(cpuid_hex)
                            mc_yr = f"{data[i+9]:02X}{data[i+8]:02X}"
                            mc_day = f"{data[i+10]:02X}"
                            mc_mon = f"{data[i+11]:02X}"
                            mc_date = f"{mc_yr}-{mc_mon}-{mc_day}"
                            self.info["microcodes"].append({
                                "cpuid": cpuid_hex,
                                "platform": f"0x{plat:02X}",
                                "revision": f"0x{rev:08X}",
                                "date": mc_date,
                                "size": f"0x{sz:X}"
                            })

        if direct_cpuids:
            unique_cpuids = sorted(list(set(direct_cpuids)))
            self.info["cpuids"] = unique_cpuids
            best_rank = -1
            best_gen = None
            best_chipset = None
            for cid in unique_cpuids:
                if cid in CPUID_MAP:
                    gen_str, chipset_val = CPUID_MAP[cid]
                    rank = 0
                    for k, r in GEN_RANK.items():
                        if k in gen_str.lower():
                            rank = max(rank, r)
                    if rank > best_rank:
                        best_rank = rank
                        best_gen = gen_str
                        best_chipset = chipset_val
            if best_gen:
                self.info["cpu_gen"] = f"Intel | {best_gen} | {', '.join(unique_cpuids)}"
                self.info["chipset"] = best_chipset
                return
            self.info["cpu_gen"] = f"Intel | Generic Intel x86 | {', '.join(unique_cpuids)}"
            return

    def _parse_flash_descriptor(self):
        data = self.raw_data
        # Standard Flash Descriptor must be located at offset 0x10 or 0x0
        fd_pos = -1
        if len(data) >= 0x50:
            if data[0x10:0x14] == SIG_FD:
                fd_pos = 0x10
            elif data[0x0:0x4] == SIG_FD:
                fd_pos = 0x0
            else:
                p = data.find(SIG_FD, 0, min(0x1000, len(data)))
                if p != -1 and p + 0x50 <= len(data):
                    fd_pos = p

        if fd_pos != -1:
            # Component Count & Flash Density (C0DEN, C1DEN)
            try:
                flmap0 = int.from_bytes(data[fd_pos + 4 : fd_pos + 8], "little")
                fcba = (flmap0 & 0xFF) << 4
                nc = ((flmap0 >> 8) & 3) + 1  # Number of flash chips (1 or 2)
                isl = data[fd_pos + 0x8 + 0x3] if fd_pos + 0xB <= len(data) else 0x15
                c1_bitwise = 0xF if isl >= 0x13 else 0x7
                c2_shift = 0x4 if isl >= 0x13 else 0x3

                density_dict = {
                    0: 0.5, 1: 1.0, 2: 2.0, 3: 4.0, 4: 8.0, 5: 16.0, 6: 32.0, 7: 64.0
                }

                if fcba < len(data):
                    comp_den = data[fcba]
                    c1_sz = density_dict.get(comp_den & c1_bitwise, 0.0)
                    c2_sz = density_dict.get((comp_den >> c2_shift) & 0xF, 0.0) if nc == 2 else 0.0
                    total_flash_mb = c1_sz + c2_sz
                    actual_file_mb = round(len(data) / (1024 * 1024), 2)
                    missing_mb = round(total_flash_mb - actual_file_mb, 2)

                    self.info["num_chips"] = nc
                    self.info["comp1_mb"] = c1_sz
                    self.info["comp2_mb"] = c2_sz
                    self.info["total_flash_mb"] = total_flash_mb

                    if missing_mb > 0.1:
                        total_disp = int(total_flash_mb) if total_flash_mb.is_integer() else total_flash_mb
                        actual_disp = int(actual_file_mb) if actual_file_mb.is_integer() else actual_file_mb
                        missing_disp = int(missing_mb) if missing_mb.is_integer() else missing_mb
                        self.info["missing_chip_warning"] = (
                            f"Full BIOS is {total_disp} MB, but we found only {actual_disp} MB & {missing_disp} MB is missing."
                        )
            except Exception:
                pass

            end_fd_match = fd_pos + 4
            fd_rgn_base = end_fd_match + 0x2C

            # Table of Standard SPI Flash Regions
            region_defs = [
                ("Descriptor", 0x0),
                ("BIOS / IAFW", 0x4),
                ("ME / CSME", 0x8),
                ("GbE LAN", 0xC),
                ("Platform Data (PDR)", 0x10),
                ("Device Expansion", 0x14),
                ("Secondary BIOS", 0x18),
            ]

            for reg_name, off in region_defs:
                if fd_rgn_base + off + 4 <= len(data):
                    base = int.from_bytes(data[fd_rgn_base + off : fd_rgn_base + off + 2], "little")
                    limit = int.from_bytes(data[fd_rgn_base + off + 2 : fd_rgn_base + off + 4], "little")
                    if limit != 0 and limit >= base:
                        b_addr = base * 0x1000
                        l_addr = (limit + 1) * 0x1000 - 1
                        sz = (limit + 1 - base) * 0x1000
                        self.info["spi_regions"].append({
                            "name": reg_name,
                            "base": f"0x{b_addr:08X}",
                            "limit": f"0x{l_addr:08X}",
                            "size": f"0x{sz:X}"
                        })

                        if reg_name == "ME / CSME" and b_addr < l_addr and b_addr < len(self.raw_data) and l_addr < 0x0FFFF000:
                            self.info["me_fd_start"] = b_addr
                            self.info["me_fd_end"] = (limit + 1) * 0x1000

    def _parse_manifest(self):
        data = self.raw_data
        mn2_entries = []

        for sig in (SIG_MN2, SIG_MAN):
            pos = 0
            while True:
                pos = data.find(sig, pos)
                if pos == -1:
                    break
                hdr_start = pos - 0x1C
                if hdr_start >= 0 and hdr_start + 0x30 <= len(data):
                    day = data[hdr_start + 0x14]
                    month = data[hdr_start + 0x15]
                    year = struct.unpack("<H", data[hdr_start + 0x16 : hdr_start + 0x18])[0]
                    major, minor, hotfix, build = struct.unpack("<HHHH", data[hdr_start + 0x24 : hdr_start + 0x2C])

                    if 2 <= major <= 35 and build > 0:
                        date_str = f"{year:04X}-{month:02X}-{day:02X}"
                        sig_hash = ""
                        if hdr_start + 0x80 <= len(data):
                            pk_size_dw = struct.unpack("<I", data[hdr_start+0x78:hdr_start+0x7C])[0]
                            exp_size_dw = struct.unpack("<I", data[hdr_start+0x7C:hdr_start+0x80])[0]
                            pk_size = pk_size_dw * 4
                            exp_size = exp_size_dw * 4
                            if 64 <= pk_size <= 1024 and 1 <= exp_size <= 64:
                                sig_off = hdr_start + 0x80 + pk_size + exp_size
                                if sig_off + pk_size <= len(data):
                                    sig_data = data[sig_off : sig_off + pk_size]
                                    sig_hash = hashlib.sha256(sig_data).hexdigest().upper()

                        mn2_entries.append({
                            "major": major,
                            "minor": minor,
                            "hotfix": hotfix,
                            "build": build,
                            "date": date_str,
                            "hdr_start": hdr_start,
                            "pos": pos,
                            "sig_hash": sig_hash
                        })
                pos += 4

        if mn2_entries:
            mea_db = get_mea_db()
            for ent in mn2_entries:
                ctx = data[max(0, ent["hdr_start"] - 64) : min(len(data), ent["hdr_start"] + 64)]
                ent["is_ftpr"] = (b"FTPR" in ctx)

            def manifest_rank(ent):
                h = ent.get("sig_hash", "")
                tag = mea_db.get(h, "")
                is_main_db = 1 if (tag and tag[0].isdigit()) else 0
                is_ftpr = 1 if ent.get("is_ftpr", False) else 0
                is_reasonable_major = 1 if (2 <= ent["major"] <= 35) else 0
                return (is_main_db, is_reasonable_major, is_ftpr, -ent["hdr_start"])

            mn2_entries.sort(key=manifest_rank, reverse=True)
            primary = mn2_entries[0]
            found_hash = primary.get("sig_hash", "")

            self.info["is_valid_me"] = True
            self.info["major"] = primary["major"]
            self.info["minor"] = primary["minor"]
            self.info["hotfix"] = primary["hotfix"]
            self.info["build"] = primary["build"]
            self.info["version"] = f"{primary['major']}.{primary['minor']}.{primary['hotfix']}.{primary['build']}"
            self.info["date"] = primary["date"]
            self.info["family"] = "CSE ME" if primary["major"] >= 11 else "ME"
            self.info["rsa_sig_hash"] = found_hash
            return

        # Fallback Legacy $MAN (ME 2 to 5)
        pos = data.find(SIG_MAN)
        if pos != -1 and pos + 0x30 <= len(data):
            major, minor, hotfix, build = struct.unpack("<HHHH", data[pos+0x24 : pos+0x2C])
            if 2 <= major <= 5 and build > 0:
                self.info["is_valid_me"] = True
                self.info["major"] = major
                self.info["minor"] = minor
                self.info["hotfix"] = hotfix
                self.info["build"] = build
                self.info["version"] = f"{major}.{minor}.{hotfix}.{build}"
                self.info["family"] = "Intel ME (Legacy)"
                self.info["date"] = "Legacy ME"

    def _parse_extension_sku(self):
        data = self.raw_data
        major = self.info.get("major", 0)
        minor = self.info.get("minor", 0)

        # 0. Pre-CSE ME 2 to 10: Parse $SKU attributes
        if 2 <= major <= 10:
            sku_pos = data.find(SIG_SKU)
            if sku_pos != -1 and sku_pos + 16 <= len(data):
                attrib = struct.unpack("<Q", data[sku_pos+8 : sku_pos+16])[0]
                u = SKU_Union()
                u.asbytes = attrib
                patsburg = u.b.Patsburg
                sku_type = u.b.SKUType
                sku_size = u.b.SKUSize
                slim = u.b.Value2

                if major == 8:
                    if sku_size * 0.5 == 1.5:
                        self.info["sku"] = "1.5MB"
                        self.info["sku_code"] = "1.5MB"
                    else:
                        self.info["sku"] = "5MB"
                        self.info["sku_code"] = "5MB"
                    self.info["chipset"] = "CPT/PBG/PPT"
                    self.info["stepping"] = "N/A"
                    return
                elif major == 7:
                    if slim == 1:
                        self.info["sku"] = "Slim"
                        self.info["sku_code"] = "SLM"
                    elif sku_size * 0.5 == 1.5:
                        self.info["sku"] = "1.5MB"
                        self.info["sku_code"] = "1.5MB"
                    else:
                        self.info["sku"] = "5MB"
                        self.info["sku_code"] = "5MB"
                    self.info["patsburg"] = bool(patsburg)
                    self.info["chipset"] = "CPT/PBG" if patsburg else "CPT"
                    self.info["stepping"] = "N/A"
                    return
                elif major == 9:
                    if sku_type == 0:
                        self.info["sku"] = "5MB"
                        self.info["sku_code"] = "5MB"
                    elif sku_type == 1:
                        self.info["sku"] = "1.5MB"
                        self.info["sku_code"] = "1.5MB"
                    elif sku_type == 2:
                        self.info["sku"] = "Slim"
                        self.info["sku_code"] = "SLM"
                    if minor == 0:
                        self.info["chipset"] = "LPT"
                    elif minor == 1:
                        self.info["chipset"] = "LPT/WPT"
                    elif minor in [5, 6]:
                        self.info["chipset"] = "LPT-LP"
                    self.info["stepping"] = "N/A"
                    return
                elif major == 10:
                    if sku_type == 0:
                        self.info["sku"] = "5MB"
                        self.info["sku_code"] = "5MB"
                    elif sku_type == 1:
                        self.info["sku"] = "1.5MB"
                        self.info["sku_code"] = "1.5MB"
                    elif sku_type == 2:
                        self.info["sku"] = "Slim"
                        self.info["sku_code"] = "SLM"
                    self.info["chipset"] = "WPT-LP"
                    self.info["stepping"] = "N/A"
                    return
                elif major == 6:
                    sku_me = int.from_bytes(data[sku_pos+8 : sku_pos+12], "big")
                    if sku_me == 0:
                        ign_pch = "CCK" if self.info.get("hotfix") == 50 else "IBX"
                        self.info["sku"] = f"Ignition {ign_pch}"
                        self.info["sku_code"] = "IGN"
                    elif sku_me == 0x701C0000:
                        self.info["sku"] = "1.5MB"
                        self.info["sku_code"] = "1.5MB"
                    elif sku_me in [0x77DCEE00, 0x77FCEE00, 0xF7FEFE00]:
                        self.info["sku"] = "5MB MB"
                        self.info["sku_code"] = "5MB_MB"
                    else:
                        self.info["sku"] = "5MB DT"
                        self.info["sku_code"] = "5MB_DT"
                    self.info["chipset"] = "IBX"
                    self.info["stepping"] = "N/A"
                    return

        # 1. Primary: Check Extension 0x0C (CLIENT_SYSTEM_INFO_EXTENSION)
        # Tag 0x0000000C, Size 0x00000030. Used in CSME 11 to 21+ for actual SKU
        pos = 0
        ext12_sku_map = {
            0: ("Corporate", "COR"),
            1: ("Consumer", "CON"),
            2: ("Slim", "SLM"),
            3: ("Server", "SVR"),
            5: ("Chrome", "CHR"),
        }
        while True:
            pos = data.find(b"\x0c\x00\x00\x00\x30\x00\x00\x00", pos)
            if pos == -1:
                break
            if pos + 0x30 <= len(data):
                fw_attrib = struct.unpack("<Q", data[pos + 0x28 : pos + 0x30])[0]
                stype = (fw_attrib >> 4) & 0x07
                sku_plat = (fw_attrib >> 10) & 0x03
                if stype in ext12_sku_map:
                    sname, scode = ext12_sku_map[stype]
                    if major == 11:
                        if sku_plat == 1:
                            self.info["sku"] = f"{sname} LP"
                            self.info["sku_code"] = f"{scode}_LP"
                            self.info["chipset"] = "SPT/KBP-LP C"
                            self.info["stepping"] = "C"
                        else:
                            self.info["sku"] = f"{sname} H"
                            self.info["sku_code"] = f"{scode}_H"
                            self.info["chipset"] = "SPT-H D"
                            self.info["stepping"] = "D"
                        return

                    is_lp = (major in [14, 15, 16, 17, 18, 19] or sku_plat == 1 or "LP" in self.info["chipset"])
                    if is_lp:
                        self.info["sku"] = f"{sname} LP"
                        self.info["sku_code"] = f"{scode}_LP"
                    else:
                        self.info["sku"] = sname
                        self.info["sku_code"] = scode
                    return
            pos += 4

        # 2. Fallback: Extension 0x0F (System Info)
        pos = 0
        while True:
            pos = data.find(b"FTPR", pos)
            if pos == -1:
                break
            if pos >= 8 and data[pos-8:pos-4] == b"\x0f\x00\x00\x00":
                ext_start = pos - 8
                if ext_start + 40 <= len(data):
                    fw_sku = data[ext_start + 37] & 0x07
                    if fw_sku in SKU_CODE_MAP:
                        sname, scode = SKU_CODE_MAP[fw_sku]
                        is_lp = (self.info["major"] in [14, 15, 16, 17, 18, 19] or "LP" in self.info["chipset"])
                        if is_lp:
                            self.info["sku"] = f"{sname} LP"
                            self.info["sku_code"] = f"{scode}_LP"
                        else:
                            self.info["sku"] = sname
                            self.info["sku_code"] = scode
                        return
            pos += 4

    def _parse_fpt_and_size(self):
        data = self.raw_data
        pos = 0
        found_fpts = []

        while True:
            pos = data.find(SIG_FPT, pos)
            if pos == -1:
                break
            found_fpts.append(pos)
            pos += 4

        if not found_fpts:
            self.info["fpt_found"] = False
            self.info["mfs_found"] = False
            self.info["fs_stage"] = "N/A"
            self.info["fs_state"] = "N/A"
            self.info["mfs_state"] = "N/A"
            self.info["warnings"].append("No Flash Partition Table ($FPT) detected!")

            # Check if CSE Layout Table exists even without $FPT (e.g. IFWI 2.0 with BPDT)
            bp_sigs = (b'\xAA\x55\x00\x00', b'\xAA\x55\xAA\x00', b'\x00\x00\xAA\x55', b'\x00\xAA\x55\xAA')
            cse_lt_max_end = 0
            for base in [0, 0x1000, 0x2000, 0x3000, 0x4000]:
                if base + 0x40 <= len(data):
                    try:
                        romb0, romb1, romb2, romb3, d_off, d_sz, b1_off, b1_sz, b2_off, b2_sz, b3_off, b3_sz, b4_off, b4_sz, b5_off, b5_sz = struct.unpack('<IIIIIIIIIIIIIIII', data[base:base+0x40])
                        b_cand = (b1_off, b2_off, b3_off, b4_off, b5_off)
                        if any(off < len(data) and data[base+off:base+off+4] in bp_sigs for off in b_cand if off not in (0, 0xFFFFFFFF)):
                            entries = [(d_off, d_sz), (b1_off, b1_sz), (b2_off, b2_sz), (b3_off, b3_sz), (b4_off, b4_sz), (b5_off, b5_sz)]
                            valid_ends = [base + off + sz for off, sz in entries if off not in (0, 0xFFFFFFFF) and sz not in (0, 0xFFFFFFFF) and base + off + sz <= len(data)]
                            if valid_ends:
                                cse_lt_max_end = max(valid_ends) - base
                            if cse_lt_max_end > 0:
                                break
                    except Exception:
                        pass
                if base + 56 <= len(data):
                    try:
                        sz = struct.unpack("<H", data[base + 0x10 : base + 0x12])[0]
                        if sz in (0x40, 0x48):
                            r0, r1, r2, r3, sz, flg, res, csum, data_off, data_sz, bp1_off, bp1_sz, bp2_off, bp2_sz, bp3_off, bp3_sz = struct.unpack("<IIIIHBBIIIIIIIII", data[base : base + 56])
                            b_cand17 = (bp1_off, bp2_off, bp3_off)
                            if any(off < len(data) and data[base+off:base+off+4] in bp_sigs for off in b_cand17 if off not in (0, 0xFFFFFFFF)):
                                entries = [(data_off, data_sz), (bp1_off, bp1_sz), (bp2_off, bp2_sz), (bp3_off, bp3_sz)]
                                valid_ends = [base + off + s for off, s in entries if off not in (0, 0xFFFFFFFF) and s not in (0, 0xFFFFFFFF) and base + off + s <= len(data)]
                                if valid_ends:
                                    cse_lt_max_end = max(valid_ends) - base
                                if cse_lt_max_end > 0:
                                    break
                    except Exception:
                        pass

            if cse_lt_max_end > 0:
                self.info["has_ftpr"] = True
                self.info["fpt_found"] = True
                self.info["mfs_found"] = False
                self.info["fs_state"] = "N/A"
                self.info["mfs_state"] = "N/A"
                self.info["fw_type"] = "Extracted"
                self.info["size_hex"] = f"0x{cse_lt_max_end:X}"
                bpdt_pat = re.compile(br'\xAA\x55[\x00\xAA]\x00.\x00[\x01\x02][\x00\x01]', re.DOTALL)
                bpdt_m = bpdt_pat.search(data)
                if bpdt_m:
                    bpdt_off = bpdt_m.start()
                    if bpdt_off + 24 <= len(data):
                        b_fit_maj, b_fit_min, b_fit_hot, b_fit_bld = struct.unpack('<HHHH', data[bpdt_off+0x10 : bpdt_off+0x18])
                        if b_fit_maj > 0 and b_fit_maj != 0xFFFF:
                            self.info["fitc_ver"] = f"{b_fit_maj}.{b_fit_min}.{b_fit_hot}.{b_fit_bld}"
                return
            return

        self.info["fpt_found"] = True

        has_oem_config = False
        fitc_part_found = False
        oemp_part_found = False
        cdmd_part_found = False
        mfsb_part_found = False
        mfs_buf = None

        primary_fpt = found_fpts[0]
        if self.info["me_fd_start"] > 0:
            fd_fpts = [p for p in found_fpts if self.info["me_fd_start"] <= p < self.info["me_fd_end"]]
            if not fd_fpts:
                self.info["fw_type"] = "Update"
                self.info["fpt_found"] = False
                self.info["size_hex"] = ""
                return
            else:
                primary_fpt = fd_fpts[0]

        # In Intel SPI image, partition offsets in FPT are relative to ME base
        if self.info["me_fd_start"] > 0 and primary_fpt == self.info["me_fd_start"] + 0x10:
            fpt_base = self.info["me_fd_start"]
        elif primary_fpt == 0x10 or (primary_fpt >= 0x10 and data[primary_fpt - 0x10 : primary_fpt] == b"\x00" * 16):
            fpt_base = primary_fpt - 0x10
        else:
            fpt_base = primary_fpt

        if primary_fpt + 32 <= len(data):
            fit_maj, fit_min, fit_hot, fit_bld = struct.unpack("<HHHH", data[primary_fpt+0x18 : primary_fpt+0x20])
            if fit_maj > 0 and fit_maj != 0xFFFF:
                self.info["fitc_ver"] = f"{fit_maj}.{fit_min}.{fit_hot}.{fit_bld}"
            is_stock_rgn = (fit_maj in (0, 0xFFFF) or fit_bld in (0, 0xFFFF))
            self.info["is_stock_rgn"] = is_stock_rgn

            # Check for BPDT (Boot Partition Descriptor Table - IFWI)
            bpdt_pat = re.compile(br'\xAA\x55[\x00\xAA]\x00.\x00[\x01\x02][\x00\x01]', re.DOTALL)
            bpdt_m = bpdt_pat.search(data)
            if bpdt_m:
                bpdt_off = bpdt_m.start()
                if bpdt_off + 24 <= len(data):
                    b_fit_maj, b_fit_min, b_fit_hot, b_fit_bld = struct.unpack('<HHHH', data[bpdt_off+0x10 : bpdt_off+0x18])
                    if b_fit_maj > 0 and b_fit_maj != 0xFFFF:
                        self.info["fitc_ver"] = f"{b_fit_maj}.{b_fit_min}.{b_fit_hot}.{b_fit_bld}"
                        self.info["is_stock_rgn"] = False
                        self.info["fw_type"] = "Extracted"

            # Extract partitions from primary FPT
            num_entries = struct.unpack("<I", data[primary_fpt+4 : primary_fpt+8])[0]
            if num_entries < 48:
                for i in range(num_entries):
                    e_off = primary_fpt + 32 + i * 32
                    if e_off + 32 > len(data):
                        break
                    e = data[e_off : e_off + 32]
                    pname = e[:4].rstrip(b"\x00").decode("ascii", errors="ignore")
                    poff = struct.unpack("<I", e[8:12])[0]
                    psize = struct.unpack("<I", e[12:16])[0]

                    # ME 2-6: Calculate dynamic partition size if size == 0xFFFFFFFF
                    if poff != 0xFFFFFFFF and psize == 0xFFFFFFFF:
                        p_abs = fpt_base + poff
                        if p_abs + 0x30 <= len(data):
                            if data[p_abs + 0x1C : p_abs + 0x20] == b"$MN2":
                                num_mods = struct.unpack("<I", data[p_abs + 0x20 : p_abs + 0x24])[0]
                                hdr_len = struct.unpack("<I", data[p_abs + 0x04 : p_abs + 0x08])[0] * 4
                                mod_start = p_abs + hdr_len + 0xC
                                mod_end_max = p_abs
                                for _ in range(min(num_mods, 64)):
                                    if mod_start + 0x60 > len(data) or data[mod_start : mod_start + 4] != b"$MME":
                                        break
                                    m_off = struct.unpack("<I", data[mod_start + 0x38 : mod_start + 0x3C])[0]
                                    m_uncomp = struct.unpack("<I", data[mod_start + 0x3C : mod_start + 0x40])[0]
                                    m_comp = struct.unpack("<I", data[mod_start + 0x40 : mod_start + 0x44])[0]
                                    m_sz = m_comp if m_comp else m_uncomp
                                    m_end = p_abs + m_off + m_sz
                                    if m_end > mod_end_max:
                                        mod_end_max = m_end
                                    mod_start += 0x60
                                eng_fw_align = 0x1000 - ((mod_end_max - fpt_base) % 0x1000)
                                if eng_fw_align != 0x1000:
                                    mod_end_max += eng_fw_align
                                psize = mod_end_max - fpt_base - poff
                            elif data[p_abs + 0x1C : p_abs + 0x20] == b"$MAN":
                                num_mods = struct.unpack("<I", data[p_abs + 0x24 : p_abs + 0x28])[0]
                                hdr_len = struct.unpack("<I", data[p_abs + 0x04 : p_abs + 0x08])[0] * 4
                                mod_start = p_abs + hdr_len + 0xC
                                mod_size_all = 0
                                for _ in range(min(num_mods, 64)):
                                    if mod_start + 0x50 > len(data) or data[mod_start : mod_start + 4] != b"$MME":
                                        break
                                    m_sz = struct.unpack("<I", data[mod_start + 0x40 : mod_start + 0x44])[0]
                                    mod_size_all += m_sz
                                    mod_start += 0x50
                                mod_end_max = mod_start + 0x50 + 0xC + mod_size_all
                                psize = ((mod_end_max - fpt_base + 0xFFF) & ~0xFFF) - poff

                    if poff != 0xFFFFFFFF and psize != 0xFFFFFFFF:
                        self.info["fpt_entries"].append({
                            "name": pname,
                            "offset": f"0x{poff:06X}",
                            "size": f"0x{psize:X}",
                            "end": f"0x{poff+psize:06X}"
                        })

                    abs_p = fpt_base + poff
                    p_valid = (psize > 0 and abs_p + psize <= len(data) and data[abs_p : abs_p + min(psize, 64)] != b"\xFF" * min(psize, 64))

                    if pname == "FITC" and p_valid:
                        fitc_part_found = True
                    elif pname == "OEMP" and p_valid:
                        oemp_part_found = True
                    elif pname == "CDMD" and p_valid:
                        cdmd_part_found = True
                        if abs_p + psize <= len(data):
                            cdmd_data = data[abs_p : abs_p + psize]
                            m = re.search(rb'Intel\(R\)\s+([A-Za-z0-9_\-\s]+?)\s+Chipset', cdmd_data)
                            if m:
                                raw_chip = m.group(1).decode('ascii', errors='ignore').strip()
                                formatted_chip = re.sub(r'([a-z])([A-Z])', r'\1 \2', raw_chip)
                                self.info["chipset"] = formatted_chip
                    elif pname == "MFSB" and p_valid:
                        mfsb_part_found = True
                    elif pname in ["UTOK", "STKN"] and p_valid:
                        has_oem_config = True

                    if pname in ["MFS", "MFSB"]:
                        if abs_p + psize <= len(data):
                            mfs_buf = data[abs_p : abs_p + psize]

            # Check for Update image vs Stock vs Extracted
            non_empty_parts = [e["name"] for e in self.info["fpt_entries"] if e.get("size") not in ("0x0", "0x000000", "0", 0)]
            if set(non_empty_parts) in ({'FTPR', 'FTUP', 'NFTP'}, {'FTPR', 'FTUP'}, {'FTPR', 'NFTP'}):
                self.info["fw_type"] = "Update"
                self.info["is_stock_rgn"] = False
            else:
                fovd_dirty = False
                for e in self.info["fpt_entries"]:
                    if e["name"] == "FOVD":
                        off = int(e["offset"], 16) if str(e["offset"]).startswith("0x") else int(e["offset"])
                        sz = int(e["size"], 16) if str(e["size"]).startswith("0x") else int(e["size"])
                        abs_p = (fpt_base + off) if (fpt_base + off + sz <= len(data)) else off
                        if abs_p + sz <= len(data):
                            fovd_chunk = data[abs_p : abs_p + sz]
                            if fovd_chunk != b"\xFF" * sz:
                                fovd_dirty = True
                                break

                if fovd_dirty or b"KRND\x00" in data:
                    self.info["is_stock_rgn"] = False
                    self.info["fw_type"] = "Extracted"
                elif fit_bld in (0, 0xFFFF):
                    self.info["is_stock_rgn"] = True
                    self.info["fw_type"] = "Stock"
                else:
                    self.info["is_stock_rgn"] = False
                    self.info["fw_type"] = "Extracted"

        # Determine maximum partition end from FPT entries
        self.info["has_ftpr"] = any(e["name"] == "FTPR" for e in self.info["fpt_entries"])
        fpt_max_end = 0
        if self.info["fpt_entries"]:
            for entry in self.info["fpt_entries"]:
                try:
                    off_val = int(entry["offset"], 16) if str(entry["offset"]).startswith("0x") else int(entry["offset"])
                    sz_val = int(entry["size"], 16) if str(entry["size"]).startswith("0x") else int(entry["size"])
                    if off_val != 0xFFFFFFFF and sz_val != 0xFFFFFFFF:
                        fpt_max_end = max(fpt_max_end, off_val + sz_val)
                except Exception:
                    pass

        # In Intel CSME, check for IFWI CSE Layout Table (CSE LT - IFWI 1.6 / 1.7)
        cse_lt_max_end = 0
        bp_sigs = (b'\xAA\x55\x00\x00', b'\xAA\x55\xAA\x00', b'\x00\x00\xAA\x55', b'\x00\xAA\x55\xAA')
        major = self.info.get("major", 0)
        if major >= 11:
            me_start = self.info.get("me_fd_start", 0)
            candidates = [me_start] if me_start > 0 else []
            candidates.extend([0, 0x1000, 0x2000, 0x3000, 0x4000])
            candidates = sorted(list(set(candidates)))

            for base in candidates:
                # 1. Check IFWI 1.6 Structure
                if base + 0x40 <= len(data):
                    try:
                        romb0, romb1, romb2, romb3, d_off, d_sz, b1_off, b1_sz, b2_off, b2_sz, b3_off, b3_sz, b4_off, b4_sz, b5_off, b5_sz = struct.unpack('<IIIIIIIIIIIIIIII', data[base:base+0x40])
                        b_cand = (b1_off, b2_off, b3_off, b4_off, b5_off)
                        if any(off < len(data) and data[base+off:base+off+4] in bp_sigs for off in b_cand if off not in (0, 0xFFFFFFFF)):
                            lt16_entries = [(d_off, d_sz), (b1_off, b1_sz), (b2_off, b2_sz), (b3_off, b3_sz), (b4_off, b4_sz), (b5_off, b5_sz)]
                            valid_ends = [base + off + sz for off, sz in lt16_entries if off not in (0, 0xFFFFFFFF) and sz not in (0, 0xFFFFFFFF) and base + off + sz <= len(data)]
                            if valid_ends:
                                cse_lt_max_end = max(valid_ends) - base
                            if cse_lt_max_end > 0:
                                break
                    except Exception:
                        pass

                # 2. Check IFWI 1.7 Structure
                if base + 56 <= len(data):
                    try:
                        sz = struct.unpack("<H", data[base + 0x10 : base + 0x12])[0]
                        if sz in (0x40, 0x48):
                            r0, r1, r2, r3, sz, flg, res, csum, data_off, data_sz, bp1_off, bp1_sz, bp2_off, bp2_sz, bp3_off, bp3_sz = struct.unpack("<IIIIHBBIIIIIIIII", data[base : base + 56])
                            b_cand17 = (bp1_off, bp2_off, bp3_off)
                            if any(off < len(data) and data[base+off:base+off+4] in bp_sigs for off in b_cand17 if off not in (0, 0xFFFFFFFF)):
                                entries = [(data_off, data_sz), (bp1_off, bp1_sz), (bp2_off, bp2_sz), (bp3_off, bp3_sz)]
                                valid_ends = [base + off + s for off, s in entries if off not in (0, 0xFFFFFFFF) and s not in (0, 0xFFFFFFFF) and base + off + s <= len(data)]
                                if valid_ends:
                                    cse_lt_max_end = max(valid_ends) - base
                                if cse_lt_max_end > 0:
                                    break
                    except Exception:
                        pass

        is_fd_present = (self.info.get("me_fd_start", 0) > 0 or self.info.get("me_fd_end", 0) > 0)
        self.info["has_ftpr"] = any(e["name"] == "FTPR" for e in self.info["fpt_entries"]) or (cse_lt_max_end > 0)

        # Scan for uncharted $MN2 and $CPD partitions starting after fpt_max_end (only if FTPR exists)
        if self.info["has_ftpr"]:
            p_end_scan = fpt_base + fpt_max_end
            while p_end_scan + 0x20 <= len(data):
                if data[p_end_scan + 0x1C : p_end_scan + 0x20] == b"$MN2":
                    try:
                        num_mods = struct.unpack("<I", data[p_end_scan + 0x20 : p_end_scan + 0x24])[0]
                        hdr_len = struct.unpack("<I", data[p_end_scan + 0x04 : p_end_scan + 0x08])[0] * 4
                        mod_start = p_end_scan + hdr_len + 0xC
                        mme_size = 0x80 if major == 2 else 0x60
                        mcp_start = mod_start + num_mods * mme_size + mme_size
                        if mcp_start + 0x20 <= len(data) and data[mcp_start : mcp_start + 4] == b"$MCP":
                            mcp_off, mcp_sz = struct.unpack("<II", data[mcp_start + 0x08 : mcp_start + 0x10])
                            p_end_scan += mcp_off + mcp_sz
                            fpt_max_end = max(fpt_max_end, p_end_scan - fpt_base)
                            continue
                    except Exception:
                        pass
                elif data[p_end_scan : p_end_scan + 4] == b"$CPD":
                    try:
                        cpd_ver = data[p_end_scan + 8]
                        cpd_hdr_sz = 0x10 if cpd_ver == 1 else 0x14
                        cpd_num = struct.unpack("<I", data[p_end_scan + 0x04 : p_end_scan + 0x08])[0]
                        cpd_fw_end = 0
                        cpd_off_last = 0
                        for ci in range(min(cpd_num, 64)):
                            entry_off = p_end_scan + cpd_hdr_sz + ci * 0x18
                            if entry_off + 0x18 <= len(data):
                                raw_off = struct.unpack("<I", data[entry_off + 0x0C : entry_off + 0x10])[0]
                                c_off = raw_off & 0x01FFFFFF
                                c_sz = struct.unpack("<I", data[entry_off + 0x10 : entry_off + 0x14])[0]
                                if c_off > cpd_off_last:
                                    cpd_off_last = c_off
                                    cpd_fw_end = c_off + c_sz

                        mn2_start = p_end_scan + cpd_hdr_sz + cpd_num * 0x18
                        cse_ext_part_size = 0
                        if mn2_start + 16 <= len(data):
                            hdr_len = struct.unpack("<I", data[mn2_start + 4 : mn2_start + 8])[0] * 4
                            curr = mn2_start + hdr_len
                            for _ in range(16):
                                if curr + 8 > len(data):
                                    break
                                ext_type, ext_len = struct.unpack("<II", data[curr : curr + 8])
                                if ext_type in (0x3, 0x16):
                                    if curr + 0x10 <= len(data):
                                        cse_ext_part_size = struct.unpack("<I", data[curr + 0x0C : curr + 0x10])[0]
                                    break
                                if ext_len == 0 or ext_len > 0x10000:
                                    break
                                curr += ext_len

                        part_sz = max(cse_ext_part_size, cpd_fw_end)
                        if part_sz > 0:
                            p_end_scan += part_sz
                            fpt_max_end = max(fpt_max_end, p_end_scan - fpt_base)
                            continue
                    except Exception:
                        pass

                # If next uncharted partition starts within 8KB alignment padding
                if not is_fd_present and cse_lt_max_end == 0 and p_end_scan + 0x2000 <= len(data):
                    cpd_pat_search = re.compile(br'\$CPD.\x00\x00\x00[\x01\x02]\x01[\x10\x14]', re.DOTALL)
                    m_next = cpd_pat_search.search(data[p_end_scan : p_end_scan + 0x2000])
                    if m_next and m_next.start() > 0:
                        p_end_scan += m_next.start()
                        continue

                break

        if major == 4 and not is_fd_present:
            total_fw_size = 0x1FB000
        elif cse_lt_max_end > 0:
            total_fw_size = (cse_lt_max_end + 0xFFF) & ~0xFFF
        elif fpt_max_end > 0:
            total_fw_size = (fpt_max_end + 0xFFF) & ~0xFFF
        elif is_fd_present:
            me_start = self.info["me_fd_start"]
            me_end = self.info["me_fd_end"]
            if me_end > me_start and me_start >= 0:
                scan_end = min(len(data), me_end)
                me_chunk = data[me_start:scan_end]
                non_ff_len = len(me_chunk.rstrip(b"\xFF"))
                total_fw_size = (non_ff_len + 0xFFF) & ~0xFFF if non_ff_len > 0 else (me_end - me_start)
            else:
                total_fw_size = self.file_size
        else:
            total_fw_size = self.file_size

        self.info["size_hex"] = f"0x{total_fw_size:X}"

        self.info["mfs_found"] = (mfs_buf is not None)
        major = self.info.get("major", 0)
        if major < 11:
            # Intel ME v2 to v10 do not use MFS; File System State is not applicable
            fs_state = "N/A"
            mfs_has_oem_file = False
        else:
            fs_state, mfs_has_oem_file = self._determine_mfs_state(
                mfs_buf,
                has_oem_config=(oemp_part_found or cdmd_part_found or fitc_part_found)
            )

        has_oem_config = mfs_has_oem_file or oemp_part_found or fitc_part_found or cdmd_part_found
        self.info["oem_config"] = "Yes" if has_oem_config else "No"
        self.info["fs_stage"] = fs_state
        self.info["fs_state"] = fs_state
        self.info["mfs_state"] = fs_state

    @staticmethod
    def _crc16_14(w, crc=0x3FFF):
        """MFS 14-bit CRC-16 for System Page Chunk Indexes."""
        table = [0] * 256
        for i in range(256):
            r = i << 8
            for _ in range(8):
                r = (r << 1) ^ (0x1021 if r & 0x8000 else 0)
            table[i] = r & 0xFFFF
        for b in bytearray(struct.pack("<H", w)):
            crc = (table[b ^ (crc >> 8)] ^ (crc << 8)) & 0x3FFF
        return crc

    def _determine_mfs_state(self, mfs_buf, has_oem_config=False):
        """
        Determines Intel CSME File System State: Initialized, Configured, or Unconfigured.
        Conforms strictly to Intel CSME MFS volume and FAT specifications.
        Returns: (state_str, has_oem_file_in_mfs)
        """
        if not mfs_buf or len(mfs_buf) < 0x2000:
            return ("Configured" if has_oem_config else "Unconfigured"), False

        # Check for MFS Backup (MFSB) partition
        if mfs_buf[:4] == b"MFSB":
            return "Configured", True

        # Verify MFS signature (0x877855AA or 0xAA557887)
        sig1 = mfs_buf[:4]
        sig2 = mfs_buf[0x2000:0x2004] if len(mfs_buf) >= 0x2004 else b""
        if b"\xAA\x55\x78\x87" not in (sig1, sig2) and b"\x87\x78\x55\xAA" not in (sig1, sig2):
            return ("Configured" if has_oem_config else "Error"), False

        page_size = 0x2000
        page_hdr_size = 0x12
        chunk_all_size = 0x42
        chunk_raw_size = 0x40
        index_size_sys = 2
        page_count = len(mfs_buf) // page_size

        sys_pages = []
        chunks_count_sys = 0xFFFF

        for p in range(page_count):
            p_start = p * page_size
            p_hdr = mfs_buf[p_start : p_start + page_hdr_size]
            if len(p_hdr) < page_hdr_size:
                continue
            p_tag = struct.unpack("<I", p_hdr[:4])[0]
            if p_tag not in (0xAA557887, 0x877855AA):
                continue
            tag, p_num, erase_cnt, next_erase, first_chunk, crc8, res = struct.unpack("<IIIHHBB", p_hdr[:18])
            if first_chunk == 0:
                sys_pages.append((p_num, mfs_buf[p_start : p_start + page_size]))
            else:
                chunks_count_sys = min(chunks_count_sys, first_chunk)

        if not sys_pages:
            return ("Configured" if has_oem_config else "Error"), False

        sys_pages.sort(key=lambda x: x[0])

        all_chunks_dict = {}
        for p_num, p_data in sys_pages:
            chunk_count = (page_size - page_hdr_size - index_size_sys) // (index_size_sys + chunk_all_size)
            index_size = chunk_count * index_size_sys + index_size_sys
            index_data_obf = p_data[page_hdr_size : page_hdr_size + index_size]
            index_values_obf = struct.unpack("<%dH" % (chunk_count + 1), index_data_obf)
            chunk_start = page_hdr_size + index_size

            chunk_index = 0
            chunk_indexes = []
            for i in range(len(index_values_obf)):
                if index_values_obf[i] & 0xC000:
                    break
                chunk_index = self._crc16_14(chunk_index) ^ index_values_obf[i]
                chunk_indexes.append(chunk_index)

            for i, c_idx in enumerate(chunk_indexes):
                c_offset = chunk_start + chunk_all_size * i
                c_raw = p_data[c_offset : c_offset + chunk_raw_size]
                all_chunks_dict[c_idx] = c_raw

        if 0 not in all_chunks_dict:
            for p_num, p_data in sys_pages:
                idx = p_data.find(b"\x01\x62\x4F\x72")
                if idx != -1:
                    all_chunks_dict[0] = p_data[idx : idx + chunk_raw_size]
                    break

        if 0 not in all_chunks_dict:
            return ("Configured" if has_oem_config else "Error"), False

        c0 = all_chunks_dict[0]
        vol_sig, ftbl_dict, ftbl_plat, ftbl_res, vol_size, vol_file_rec = struct.unpack("<IBBHIH", c0[:14])
        if vol_sig != 0x724F6201:
            return ("Configured" if has_oem_config else "Error"), False

        if chunks_count_sys == 0xFFFF:
            chunks_count_sys = max(all_chunks_dict.keys()) + 1 if all_chunks_dict else 1

        sys_buf = bytearray(chunks_count_sys * chunk_raw_size)
        for c_idx in range(chunks_count_sys):
            if c_idx in all_chunks_dict:
                sys_buf[c_idx * chunk_raw_size : (c_idx + 1) * chunk_raw_size] = all_chunks_dict[c_idx]

        fat_count = vol_file_rec
        fat_bytes = sys_buf[14 : 14 + fat_count * 2]
        fat_values = struct.unpack("<%dH" % (len(fat_bytes) // 2), fat_bytes)

        # In Intel CSME, File 0..5, 8 are runtime markers created/written upon booting on board:
        # File 8 = Home Directory (/home records)
        # File 2, 3 = Anti-Replay monotonic counters
        # File 4 = SVN Migration
        # File 5 = Quota Storage
        # File 6 = Intel Configuration (present in both Configured and Initialized)
        # File 7 = OEM Configuration / fitc.cfg (present in Configured)
        # File 9 = Manifest Backup (present in Configured)
        # Unused FAT values: 0x0000 (unused), 0xFFFE (erased), 0xFFFF (empty)
        is_initialized = False
        for idx, val in enumerate(fat_values):
            if idx not in (6, 7, 9) and val not in (0x0000, 0xFFFE, 0xFFFF):
                is_initialized = True
                break

        # Check if OEM Configuration file (File 7: fitc.cfg) is allocated and valid
        has_oem_file = False
        if len(fat_values) > 7 and fat_values[7] not in (0x0000, 0xFFFE, 0xFFFF):
            has_oem_file = True

        if is_initialized:
            return "Initialized", has_oem_file

        has_cfg_files = has_oem_file or (len(fat_values) > 9 and fat_values[9] not in (0x0000, 0xFFFE, 0xFFFF))

        if has_cfg_files or has_oem_config:
            return "Configured", has_oem_file

        return "Unconfigured", False

    def _parse_sub_firmwares(self):
        """
        Parses independent sub-firmwares (PMC, PCHC, PHY, IOM, TBT).
        Intel CSME firmware stores these in separate Code Partition Directory ($CPD)
        partitions, each having its own $MN2 manifest.
        """
        data = self.raw_data
        pos = 0
        tags = [b"PMCP", b"PMC", b"PCHC", b"NPHY", b"TPHY", b"IOMP", b"TBTP"]
        sub_fw = {}

        while True:
            pos = data.find(SIG_MN2, pos)
            if pos == -1:
                break
            hdr_start = pos - 0x1C
            if hdr_start >= 0 and hdr_start + 0x30 <= len(data):
                day = data[hdr_start + 0x14]
                month = data[hdr_start + 0x15]
                year = struct.unpack("<H", data[hdr_start + 0x16 : hdr_start + 0x18])[0]
                major, minor, hotfix, build = struct.unpack("<HHHH", data[hdr_start + 0x24 : hdr_start + 0x2C])

                # Identify closest component partition tag within 1024 bytes before hdr_start
                closest_tag = None
                closest_dist = 999999
                for t in tags:
                    p = data.rfind(t, max(0, hdr_start - 1024), hdr_start)
                    if p != -1:
                        dist = hdr_start - p
                        if dist < closest_dist:
                            closest_dist = dist
                            closest_tag = t

                if closest_tag and (major > 0 or build > 0):
                    tag_name = closest_tag.decode("ascii", errors="ignore")
                    ver_str = f"{major}.{minor}.{hotfix}.{build}"
                    date_str = f"{year:04X}-{month:02X}-{day:02X}"

                    # 1. Power Management Controller (PMC)
                    if tag_name in ["PMCP", "PMC"] and "pmc" not in sub_fw:
                        stepping = "Unknown"
                        for s_byte in [b"A", b"B", b"C", b"D", b"E"]:
                            if b"PMC" + s_byte in data[max(0, hdr_start - 1024) : hdr_start]:
                                stepping = s_byte.decode("ascii")
                                break
                        pmc_sku = "LP" if "LP" in self.info.get("sku", "") else "H"
                        sub_fw["pmc"] = {
                            "name": "Power Management Controller",
                            "family": "PMC",
                            "version": ver_str,
                            "date": date_str,
                            "stepping": stepping,
                            "sku": pmc_sku,
                            "type": "Independent"
                        }
                        self.info["pmc_version"] = ver_str

                    # 2. Platform Controller Hub Config (PCHC)
                    elif tag_name == "PCHC" and "pchc" not in sub_fw:
                        sub_fw["pchc"] = {
                            "name": "Platform Controller Hub",
                            "family": "PCHC",
                            "version": ver_str,
                            "date": date_str,
                            "type": "Independent"
                        }
                        self.info["pchc_version"] = ver_str

                    # 3. USB Type-C Physical Layer (PHY)
                    elif tag_name in ["NPHY", "TPHY"] and "phy" not in sub_fw:
                        sub_fw["phy"] = {
                            "name": "USB Type-C Physical Layer",
                            "family": "PHY",
                            "version": ver_str,
                            "date": date_str,
                            "tag": tag_name,
                            "type": "Independent"
                        }
                        self.info["phy_version"] = ver_str

                    # 4. Type-C IOM
                    elif tag_name == "IOMP" and "iom" not in sub_fw:
                        sub_fw["iom"] = {
                            "name": "Type-C IOM",
                            "family": "IOM",
                            "version": ver_str,
                            "date": date_str,
                            "type": "Independent"
                        }

                    # 5. Thunderbolt PHY (TBT)
                    elif tag_name == "TBTP" and "tbt" not in sub_fw:
                        sub_fw["tbt"] = {
                            "name": "Thunderbolt PHY",
                            "family": "TBT",
                            "version": ver_str,
                            "date": date_str,
                            "type": "Independent"
                        }

            pos += 4

        self.info["sub_firmwares"] = sub_fw

    def _build_full_tag(self):
        major = self.info.get("major", 0)
        minor = self.info.get("minor", 0)
        sku = self.info.get("sku", "")
        ver = self.info["version"]
        is_stock = self.info.get("is_stock_rgn", False)
        if is_stock:
            target_suffix = "RGN"
        else:
            if major >= 12 and "COR" in self.info.get("sku_code", ""):
                target_suffix = "EXTR-N"
            else:
                target_suffix = "EXTR"

        # Check MEA Database by RSA Signature Hash
        sig_hash = self.info.get("rsa_sig_hash", "")
        mea_db = get_mea_db()
        db_tag = mea_db.get(sig_hash) if sig_hash else None

        CSME_CHIPSET_MAP = {
            11: ("SPT/KBP-LP", "SPT-H"),
            12: ("CNP/CMP-LP", "CNP-H"),
            13: ("ICL-LP", "ICL-H"),
            14: ("CMP-LP", "CMP-H"),
            15: ("TGP-LP", "TGP-H"),
            16: ("ADP-LP", "ADP-S/M"),
            17: ("MTL-M", "MTL-M"),
            18: ("MTL-P", "MTL-P"),
            19: ("ARL-S", "ARL-S"),
        }

        if db_tag:
            tag_parts = db_tag.split("_")
            stype_code = tag_parts[1] if len(tag_parts) > 1 else ""
            if (self.info.get("fw_type") == "Update" or not self.info.get("fpt_found", False)) and major <= 10:
                target_suffix = "UPD"
                self.info["fw_type"] = "Update"
                self.info["size_hex"] = ""
            elif is_stock:
                target_suffix = "RGN"
            elif major >= 12 and "COR" in stype_code:
                target_suffix = "EXTR-N"
            else:
                target_suffix = "EXTR"

            parts = db_tag.rsplit("_", 1)
            base_tag = parts[0]
            canonical_tag = f"{base_tag}_{target_suffix}"
            self.info["full_tag"] = canonical_tag

            if major >= 11:
                if len(tag_parts) >= 6:
                    plat = tag_parts[2]
                    stype_name = "Consumer" if stype_code == "CON" else ("Corporate" if stype_code == "COR" else ("Slim" if stype_code == "SLM" else stype_code))
                    self.info["sku"] = f"{stype_name} {plat}"
                    self.info["sku_code"] = f"{stype_code}_{plat}"
                    stepping = tag_parts[3]
                    self.info["stepping"] = stepping
                    if len(tag_parts) >= 7 and "PDM" in tag_parts[4]:
                        pdm_val = tag_parts[4]
                        self.info["pdm"] = "Yes" if pdm_val == "YPDM" else "No"

                    has_ftpr = self.info.get("has_ftpr", True)
                    mfs_st = self.info.get("fs_state", "") or self.info.get("mfs_state", "")
                    mfs_found = self.info.get("mfs_found", True)

                    if mfs_st in ("Error", "N/A") or not mfs_found:
                        if major == 11:
                            self.info["chipset"] = "SPT" if minor == 0 else "SPT/KBP"
                        elif major == 12:
                            self.info["chipset"] = "CNP"
                        elif major == 13:
                            self.info["chipset"] = "ICP"
                        elif major == 14:
                            self.info["chipset"] = "CMP-H/LP"
                        elif major == 15:
                            self.info["chipset"] = "TGP"
                    elif not has_ftpr:
                        if major == 14:
                            self.info["chipset"] = "CMP-H/LP"
                        elif major == 12:
                            self.info["chipset"] = "CNP"
                        elif major == 11:
                            self.info["chipset"] = "SPT" if minor == 0 else "SPT/KBP"
                    else:
                        if major == 11 and plat == "H" and stepping == "DA":
                            self.info["chipset"] = "KBP/BSF/GCF-H A\nSPT-H D"
                        elif major == 11 and plat == "LP" and stepping == "C":
                            self.info["chipset"] = "SPT/KBP-LP C"
                        elif major in (12, 14) and plat == "LP" and stepping == "BA":
                            self.info["chipset"] = "CNP/CMP-LP B,A"
                        elif major == 12 and plat == "H" and stepping == "BA":
                            self.info["chipset"] = "CNP/CMP-H B,A"
                        elif major == 12 and plat == "LP" and stepping == "C":
                            self.info["chipset"] = "CNP/CMP-LP C"
                        elif major == 13 and plat == "LP" and stepping == "D":
                            self.info["chipset"] = "ICP-LP D"
                        elif major in CSME_CHIPSET_MAP:
                            lp_name, h_name = CSME_CHIPSET_MAP[major]
                            base_pch = lp_name if plat == "LP" else h_name
                            self.info["chipset"] = f"{base_pch} {stepping}"
                        else:
                            self.info["chipset"] = f"SPT/KBP-LP {stepping}" if plat == "LP" else f"SPT-H {stepping}"
            elif 2 <= major <= 10:
                if len(tag_parts) >= 3:
                    if tag_parts[1] == "SLM":
                        self.info["sku"] = "Slim"
                    else:
                        self.info["sku"] = tag_parts[1]
                    self.info["sku_code"] = tag_parts[1]
                    self.info["stepping"] = "N/A"
                    if major == 4:
                        self.info["chipset"] = "ICH9M"
                    elif major == 6:
                        self.info["chipset"] = "IBX"
                    elif major == 7:
                        self.info["chipset"] = "CPT/PBG" if self.info.get("patsburg") else "CPT"
                    elif major == 8:
                        self.info["chipset"] = "CPT/PBG/PPT"
                    elif major == 9:
                        self.info["chipset"] = "LPT-LP" if self.info.get("minor", 0) >= 5 else "LPT"
                    elif major == 10:
                        self.info["chipset"] = "WPT-LP"
            if self.info.get("num_chips", 0) > 0 and "Chips:" not in self.info.get("full_tag", ""):
                self.info["full_tag"] += f" | Chips: {self.info['num_chips']}"
            return

        # Fallback heuristic tag building
        if major in CSME_CHIPSET_MAP:
            lp_name, h_name = CSME_CHIPSET_MAP[major]
            base_pch = lp_name if "LP" in sku else h_name
            has_ftpr = self.info.get("has_ftpr", True)
            if major == 14:
                self.info["chipset"] = "CMP-H/LP"
            elif major == 12 and not has_ftpr:
                self.info["chipset"] = "CNP"
            else:
                self.info["chipset"] = f"{base_pch} {self.info.get('stepping', 'B')}"

        if "Unknown" in self.info["cpu_gen"] and major in GEN_FAMILY_MAP:
            gen_str, pch_code = GEN_FAMILY_MAP[major]
            self.info["cpu_gen"] = f"Intel | {gen_str}"
            if self.info["chipset"] == "Unknown":
                self.info["chipset"] = pch_code

        chipset = self.info["chipset"]
        if " " in chipset and self.info.get("stepping", "Unknown") == "Unknown":
            parts = chipset.split()
            stepping = parts[-1]
            self.info["stepping"] = stepping
        else:
            stepping = self.info.get("stepping", "N/A" if major < 11 else "B")

        release = "PRD"
        has_oem = (self.info.get("oem_config") == "Yes")
        sku_code = self.info["sku_code"]
        me_type = target_suffix
        if not is_stock and major >= 12 and (has_oem and "COR" in sku_code):
            me_type = "EXTR-Y"

        if 2 <= major <= 10:
            self.info["full_tag"] = f"{ver}_{sku_code}_{release}_{me_type}"
        elif major == 11 and "LP" in sku:
            pdm_tag = "YPDM" if self.info.get("pdm") == "Yes" else "NPDM"
            self.info["full_tag"] = f"{ver}_{sku_code}_{stepping}_{pdm_tag}_{release}_{me_type}"
        elif major >= 18:
            self.info["full_tag"] = f"{ver}_{sku_code}_{chipset}_{release}_{me_type}"
        else:
            self.info["full_tag"] = f"{ver}_{sku_code}_{stepping}_{release}_{me_type}"

        if self.info.get("num_chips", 0) > 0 and "Chips:" not in self.info["full_tag"]:
            self.info["full_tag"] += f" | Chips: {self.info['num_chips']}"


# ──────────────────────────────────────────────────────────────────────────────
# MODULAR REPORT RENDERERS
# ──────────────────────────────────────────────────────────────────────────────
def format_default_summary(info: dict) -> str:
    """The default clean summary requested by R1 Lab, fully compatible with mea_parser."""
    lines = [
        info["filename"],
        "-" * 50,
        f"CPU: {info['cpu_gen']}",
        f"Family: {info.get('family', 'CSE ME')}",
        f"CSE ME Version: {info['version']}",
        f"SKU: {info['sku']}",
        f"Chipset: {info['chipset']}",
        f"OEM Configuration: {info['oem_config']}",
        f"Date: {info['date']}",
        f"Size: {info['size_hex']}",
    ]
    if info.get("major", 0) >= 11 and info.get("fs_stage") not in ("N/A", "Unknown", None, ""):
        lines.append(f"File System State: {info['fs_stage']}")
    lines.extend([
        f"FITC: {info['fitc_ver']}",
        f"CSME Full Version: {info['full_tag']}"
    ])
    if info.get("missing_chip_warning"):
        lines.append("-" * 50)
        lines.append(info["missing_chip_warning"])
    sub_fw = info.get("sub_firmwares", {})
    if sub_fw:
        lines.append("-" * 50)
        if "pmc" in sub_fw:
            pmc = sub_fw["pmc"]
            extra = f" ({pmc['stepping']})" if pmc.get("stepping") and pmc["stepping"] != "Unknown" else ""
            lines.append(f"PMC Controller: {pmc.get('version', 'Unknown')}{extra} | Date: {pmc.get('date', 'Unknown')}")
        if "pchc" in sub_fw:
            pchc = sub_fw["pchc"]
            lines.append(f"PCHC Controller: {pchc.get('version', 'Unknown')} | Date: {pchc.get('date', 'Unknown')}")
        if "iom" in sub_fw:
            iom = sub_fw["iom"]
            lines.append(f"Type-C IOM: {iom.get('version', 'Unknown')} | Date: {iom.get('date', 'Unknown')}")
        if "phy" in sub_fw:
            phy = sub_fw["phy"]
            lines.append(f"Type-C PHY: {phy.get('version', 'Unknown')} | Date: {phy.get('date', 'Unknown')}")
        if "tbt" in sub_fw:
            tbt = sub_fw["tbt"]
            lines.append(f"Thunderbolt PHY: {tbt.get('version', 'Unknown')} | Date: {tbt.get('date', 'Unknown')}")
    return "\n".join(lines)


def format_spi_regions(info: dict) -> str:
    """Detailed Flash Memory Map (SPI Region Map)."""
    if not info.get("spi_regions"):
        return ""
    lines = [
        "",
        "+-------------------------------------------------------------------+",
        "|             SPI FLASH REGION MAP (FLASH DESCRIPTOR)               |",
        "+---------------------+--------------+--------------+---------------+",
        "| Region Name         | Base Address | Limit Address| Size          |",
        "+---------------------+--------------+--------------+---------------+"
    ]
    for r in info["spi_regions"]:
        lines.append(f"| {r['name']:19} | {r['base']:12} | {r['limit']:12} | {r['size']:13} |")
    lines.append("+---------------------+--------------+--------------+---------------+")
    return "\n".join(lines)


def format_fpt_table(info: dict) -> str:
    """Detailed Flash Partition Table ($FPT)."""
    if not info.get("fpt_entries"):
        return ""
    lines = [
        "",
        "+-------------------------------------------------------------------+",
        "|             FLASH PARTITION TABLE (FPT SUB-PARTITIONS)            |",
        "+--------------+--------------+--------------+----------------------+",
        "| Partition    | Offset       | Size         | End Address          |",
        "+--------------+--------------+--------------+----------------------+"
    ]
    for e in info["fpt_entries"]:
        lines.append(f"| {e['name']:12} | {e['offset']:12} | {e['size']:12} | {e['end']:20} |")
    lines.append("+--------------+--------------+--------------+----------------------+")
    return "\n".join(lines)


def format_microcode_audit(info: dict) -> str:
    """Detailed Intel CPU Microcode Audit."""
    if not info.get("microcodes"):
        return ""
    lines = [
        "",
        "+-------------------------------------------------------------------+",
        "|                 INTEL CPU MICROCODE AUDIT (FIT)                   |",
        "+------------+--------------+--------------+------------+-----------+",
        "| CPUID      | Platform     | Revision     | Date       | Size      |",
        "+------------+--------------+--------------+------------+-----------+"
    ]
    seen = set()
    for m in info["microcodes"]:
        if m["cpuid"] in seen:
            continue
        seen.add(m["cpuid"])
        lines.append(f"| {m['cpuid']:10} | {m['platform']:12} | {m['revision']:12} | {m['date']:10} | {m['size']:9} |")
    lines.append("+------------+--------------+--------------+------------+-----------+")
    return "\n".join(lines)


def format_sub_firmwares(info: dict) -> str:
    """Detailed Sub-Firmware Report (PMC / PCHC / PHY / IOM / TBT)."""
    sub_fw = info.get("sub_firmwares", {})
    if not sub_fw:
        return ""
    lines = [
        "",
        "+-----------------------------------------------------------------------------+",
        "|                 INDEPENDENT SUB-FIRMWARES (PMC / PCHC / PHY)                |",
        "+-------------------------------------+-------------------+-------------------+",
        "| Firmware Component                  | Version           | Release Date      |",
        "+-------------------------------------+-------------------+-------------------+"
    ]
    name_display_map = {
        "pmc": "Power Mgmt Controller (PMC)",
        "pchc": "Platform Controller Hub (PCHC)",
        "phy": "USB Type-C Physical Layer (PHY)",
        "iom": "Type-C IOM",
        "tbt": "Thunderbolt PHY (TBT)"
    }
    for key in ["pmc", "pchc", "phy", "iom", "tbt"]:
        if key not in sub_fw:
            continue
        f = sub_fw[key]
        base_name = name_display_map.get(key, key.upper())
        ver = f.get("version", "Unknown")
        dt = f.get("date", "Unknown")
        extra = ""
        if "stepping" in f and f["stepping"] != "Unknown":
            extra = f" ({f['stepping']})"
        disp = f"{base_name}{extra}"[:35]
        lines.append(f"| {disp:35} | {ver:17} | {dt:17} |")
    lines.append("+-------------------------------------+-------------------+-------------------+")
    return "\n".join(lines)


def format_warnings(info: dict) -> str:
    """ME Firmware Notes & Warnings."""
    if not info.get("warnings"):
        return ""
    lines = [
        "",
        "[WARNINGS / ADVISORIES]",
        "-" * 50
    ]
    for w in info["warnings"]:
        lines.append(f"[!] {w}")
    return "\n".join(lines)




def render_boxed_csme_report(info: dict) -> list:
    """Renders the main Intel CSME profile in a stylish boxed table with key highlights."""
    border_color = '#a855f7' # Elegant Purple border
    lbl_color    = '#94a3b8' # Slate gray labels
    
    rows = [
        ("File Name",             info["filename"],                                              "#ffffff", False),
        ("CPU Generation",        info["cpu_gen"],                                               "#fbbf24", True),  # Golden Yellow
        ("Firmware Family",       info.get("family", "CSE ME"),                                  "#00f3ff", True),  # Cyan
        ("CSE ME Version",        info["version"],                                               "#00ff99", True),  # Neon Green
        ("Platform SKU",          info["sku"],                                                   "#f472b6", True),  # Pink
        ("Chipset / Stepping",    info["chipset"],                                               "#c084fc", True),  # Purple
        ("OEM Configuration",     info["oem_config"],                                            "#f8fafc", False),
        ("Firmware Date",         info["date"],                                                  "#e2e8f0", False),
        ("Firmware Size",         info["size_hex"],                                              "#e2e8f0", False),
    ]
    
    if info.get("major", 0) >= 11 and info.get("fs_stage") not in ("N/A", "Unknown", None, ""):
        rows.append(("File System State", info["fs_stage"], "#34d399", True))

    rows.extend([
        ("FITC Version",          info["fitc_ver"],                                              "#facc15", True),  # Yellow
        ("CSME Full Version",     info["full_tag"],                                              "#38bdf8", True),  # Sky Blue
    ])
    
    col1_w = 20
    col2_w = 66
    total_inner = col1_w + col2_w + 3
    
    lines = []
    title = "INTEL CSME FIRMWARE ANALYSIS REPORT"
    t_top = f"<font color='{border_color}'>╔{'═' * total_inner}╗</font>"
    t_pad = f" {title} ".center(total_inner, ' ').replace(' ', '&nbsp;')
    t_mid = f"<font color='{border_color}'>║</font><b><font color='#00f3ff'>{t_pad}</font></b><font color='{border_color}'>║</font>"
    t_sep = f"<font color='{border_color}'>╠{'═' * (col1_w + 2)}╦{'═' * (col2_w + 2)}╣</font>"
    bot_b = f"<font color='{border_color}'>╚{'═' * (col1_w + 2)}╩{'═' * (col2_w + 2)}╝</font>"
    
    lines.append(t_top)
    lines.append(t_mid)
    lines.append(t_sep)
    
    for label, val, val_color, is_bold in rows:
        val_str = str(val)
        if len(val_str) > col2_w:
            val_str = val_str[:col2_w - 3] + "..."
        k_padded = label.ljust(col1_w).replace(' ', '&nbsp;')
        v_padded = val_str.ljust(col2_w).replace(' ', '&nbsp;')
        v_html = f"<b>{v_padded}</b>" if is_bold else v_padded
        row_html = (
            f"<font color='{border_color}'>║&nbsp;</font>"
            f"<font color='{lbl_color}'><b>{k_padded}</b></font>"
            f"<font color='{border_color}'>&nbsp;║&nbsp;</font>"
            f"<font color='{val_color}'>{v_html}</font>"
            f"<font color='{border_color}'>&nbsp;║</font>"
        )
        lines.append(row_html)
        
    lines.append(bot_b)
    if info.get("missing_chip_warning"):
        lines.append(f"<font color='#f87171'><b>[!] {info['missing_chip_warning']}</b></font>")
    return lines


def render_sub_fw_cards(info: dict) -> list:
    """Renders independent controllers (PMC, PCHC, PHY, IOM, TBT) in separate small boxed tables with highlights."""
    sub_fw = info.get("sub_firmwares", {})
    if not sub_fw:
        return []
        
    border_color = '#38bdf8' # Bright cyan border
    lbl_color    = '#94a3b8' # Slate gray label
    title_color  = '#38bdf8' # Cyan title
    ver_color    = '#00ff99' # Vibrant neon green for version highlight!
    date_color   = '#fbbf24' # Amber gold for date
    extra_color  = '#c084fc' # Purple for extra info
    
    col1_w = 18
    col2_w = 34
    total_inner = col1_w + col2_w + 3
    
    meta_order = [
        ("pmc",  "⚡ Power Management Controller (PMC)"),
        ("pchc", "⚡ Platform Controller Hub (PCHC)"),
        ("iom",  "⚡ Type-C IOM Controller"),
        ("phy",  "⚡ USB Type-C Physical Layer (PHY)"),
        ("tbt",  "⚡ Thunderbolt PHY (TBT)")
    ]
    
    all_lines = []
    
    for key, disp_title in meta_order:
        if key not in sub_fw:
            continue
        data = sub_fw[key]
        
        t_top = f"<font color='{border_color}'>╔{'═' * total_inner}╗</font>"
        t_pad = f" {disp_title} ".center(total_inner, ' ').replace(' ', '&nbsp;')
        t_mid = f"<font color='{border_color}'>║</font><b><font color='{title_color}'>{t_pad}</font></b><font color='{border_color}'>║</font>"
        t_sep = f"<font color='{border_color}'>╠{'═' * (col1_w + 2)}╦{'═' * (col2_w + 2)}╣</font>"
        t_bot = f"<font color='{border_color}'>╚{'═' * (col1_w + 2)}╩{'═' * (col2_w + 2)}╝</font>"
        
        rows = [
            ("Version", data.get("version", "Unknown"), ver_color, True),
        ]
        
        if "stepping" in data and data["stepping"] != "Unknown":
            extra_sku = f"{data['stepping']} ({data.get('sku', 'LP')})"
            rows.append(("Stepping / SKU", extra_sku, extra_color, True))
        elif "tag" in data and data["tag"]:
            rows.append(("Partition Tag", f"{data['tag']} (Independent)", extra_color, False))
            
        rows.append(("Release Date", data.get("date", "Unknown"), date_color, True))
        
        all_lines.append(t_top)
        all_lines.append(t_mid)
        all_lines.append(t_sep)
        
        for k, v, v_c, is_b in rows:
            k_p = k.ljust(col1_w).replace(' ', '&nbsp;')
            v_p = str(v).ljust(col2_w).replace(' ', '&nbsp;')
            v_h = f"<b>{v_p}</b>" if is_b else v_p
            row_html = (
                f"<font color='{border_color}'>║&nbsp;</font>"
                f"<font color='{lbl_color}'><b>{k_p}</b></font>"
                f"<font color='{border_color}'>&nbsp;║&nbsp;</font>"
                f"<font color='{v_c}'>{v_h}</font>"
                f"<font color='{border_color}'>&nbsp;║</font>"
            )
            all_lines.append(row_html)
            
        all_lines.append(t_bot)
        all_lines.append("") # blank spacer
        
    return all_lines


def render_report(info: dict, opts: dict) -> str:
    """
    Renders modular report based on user selection.
    If no extra flags are selected, returns the DEFAULT clean 12-line summary.
    """
    sections = [format_default_summary(info)]

    if opts.get("spi_map") or opts.get("all"):
        sec = format_spi_regions(info)
        if sec: sections.append(sec)

    if opts.get("fpt") or opts.get("all"):
        sec = format_fpt_table(info)
        if sec: sections.append(sec)

    if opts.get("microcode") or opts.get("all"):
        sec = format_microcode_audit(info)
        if sec: sections.append(sec)

    if opts.get("pmc") or opts.get("subfw") or opts.get("all"):
        sec = format_sub_firmwares(info)
        if sec: sections.append(sec)

    if opts.get("warnings") or opts.get("all"):
        sec = format_warnings(info)
        if sec: sections.append(sec)

    return "\n".join(sections)


def parse_cli_args(args: list) -> tuple:
    """Parses paths and optional display flags."""
    opts = {
        "spi_map": False,
        "fpt": False,
        "microcode": False,
        "pmc": False,
        "warnings": False,
        "all": False
    }
    paths = []
    for a in args:
        al = a.lower()
        if al in ["--spi", "--spi-map", "-spi"]:
            opts["spi_map"] = True
        elif al in ["--fpt", "-fpt", "-dfpt"]:
            opts["fpt"] = True
        elif al in ["--microcode", "--mc", "-mc"]:
            opts["microcode"] = True
        elif al in ["--pmc", "--subfw", "--pchc", "--phy"]:
            opts["pmc"] = True
        elif al in ["--warn", "--warnings"]:
            opts["warnings"] = True
        elif al in ["--all", "-a"]:
            opts["all"] = True
        else:
            paths.append(a)
    return paths, opts


def process_path(target_path: str, opts: dict = None):
    if opts is None:
        opts = {}
    clean_path = target_path.strip().strip('"').strip("'")
    if not clean_path:
        return

    matched_files = glob.glob(clean_path)
    if not matched_files and os.path.exists(clean_path):
        matched_files = [clean_path]

    if not matched_files:
        print(f"[ERROR] File not found: {clean_path}\n")
        return

    for fp in matched_files:
        analyzer = R1CSMEAnalyzer(fp)
        res = analyzer.parse()
        print(render_report(res, opts))
        print()


def parse_input_paths(user_input: str):
    tokens = re.findall(r'"([^"]+)"|(\S+)', user_input)
    return [t[0] if t[0] else t[1] for t in tokens]


def interactive_cli():
    print("No file provided. Enter one or more BIOS file paths:")
    try:
        while True:
            try:
                user_input = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if not user_input:
                continue

            if user_input.lower() in ["exit", "quit", "q"]:
                break

            tokens = parse_input_paths(user_input)
            paths, opts = parse_cli_args(tokens)
            print()
            for p in paths:
                process_path(p, opts)

    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    if len(sys.argv) > 1:
        paths, opts = parse_cli_args(sys.argv[1:])
        if paths:
            for p in paths:
                process_path(p, opts)
        else:
            interactive_cli()
    else:
        interactive_cli()
