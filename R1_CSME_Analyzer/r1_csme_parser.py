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
from pathlib import Path

# Common Signatures
SIG_FPT = b"$FPT"
SIG_MN2 = b"$MN2"
SIG_MAN = b"$MAN"
SIG_CPD = b"$CPD"
SIG_FIT = b"_FIT_   "
SIG_FD  = b"\x5A\xA5\xF0\x0F"

# CPU Architecture Mapping by CPUID
CPUID_MAP = {
    # 11th Gen Tiger Lake
    "000806C0": ("Tiger Lake (11th Gen)", "TGP-LP B"),
    "000806C1": ("Tiger Lake (11th Gen)", "TGP-LP B"),
    "000806C2": ("Tiger Lake (11th Gen)", "TGP-H A"),
    # 12th Gen Alder Lake
    "00090672": ("Alder Lake (12th Gen)", "ADP-P/M B"),
    "00090675": ("Alder Lake (12th Gen)", "ADP-S A"),
    "00090670": ("Alder Lake (12th Gen)", "ADP-M A"),
    # 13th / 14th Gen Raptor Lake
    "000B0671": ("Raptor Lake (13th/14th Gen)", "RPL-S B"),
    "000B06A0": ("Raptor Lake (13th/14th Gen)", "RPL-HX B"),
    "000B06F2": ("Raptor Lake (13th/14th Gen)", "RPL-P B"),
    # Core Ultra 1st Gen (Meteor Lake)
    "000706E5": ("Meteor Lake (Core Ultra)", "MTL-M/P A"),
    "000A06A0": ("Meteor Lake (Core Ultra)", "MTL-S A"),
    "000A06A1": ("Meteor Lake (Core Ultra)", "MTL-M/P A"),
    "000A06A2": ("Meteor Lake (Core Ultra)", "MTL-M/P A"),
    "000A06A4": ("Meteor Lake (Core Ultra)", "MTL-M/P A"),
    # Core Ultra 2nd Gen (Lunar Lake / Arrow Lake)
    "000B06D0": ("Lunar Lake (Core Ultra 2)", "LNL-M A"),
    "000C0650": ("Arrow Lake (Core Ultra 2)", "ARL-S A"),
    "000C0660": ("Arrow Lake (Core Ultra 2)", "ARL-H A"),
    # Panther Lake (Next-Gen)
    "000D0600": ("Panther Lake (Core Ultra 3)", "PTL A"),
    # 10th Gen Comet Lake / Ice Lake
    "000A0652": ("Comet Lake (10th Gen)", "CMP-H A"),
    "000A0651": ("Comet Lake (10th Gen)", "CMP-U A"),
    "000706E5": ("Ice Lake (10th Gen)", "ICL-U A"),
    # 8th / 9th Gen Coffee Lake / Whiskey Lake
    "000906EA": ("Coffee Lake (8th/9th Gen)", "CNP-H B"),
    "000906EB": ("Coffee Lake (8th/9th Gen)", "CNP-H B"),
    "000906EC": ("Coffee Lake (8th/9th Gen)", "CNP B"),
    "000906ED": ("Coffee Lake (8th/9th Gen)", "CNP B"),
    "000806EA": ("Whiskey Lake / Kaby Lake-R (8th Gen)", "CNP-LP B"),
    "000806EB": ("Whiskey Lake (8th Gen)", "CNP-LP B"),
    # 6th / 7th Gen Skylake / Kaby Lake
    "000406E3": ("Skylake (6th Gen)", "SPT-LP B"),
    "000506E3": ("Skylake (6th Gen)", "SPT-H B"),
    "000906E9": ("Kaby Lake (7th Gen)", "KBP-LP B"),
    # 4th / 5th Gen Haswell / Broadwell
    "000306C3": ("Haswell (4th Gen)", "LPT"),
    "00040651": ("Broadwell (5th Gen)", "WPT"),
}

GEN_FAMILY_MAP = {
    11: ("Skylake / Kaby Lake (6th/7th Gen)", "SPT-LP B"),
    12: ("Coffee Lake / Cannon Lake (8th/9th Gen)", "CNP-LP B"),
    13: ("Ice Lake (10th Gen)", "ICL-LP A"),
    14: ("Comet Lake (10th Gen)", "CMP-LP A"),
    15: ("Tiger Lake (11th Gen)", "TGP-LP B"),
    16: ("Alder Lake / Raptor Lake (12th/13th Gen)", "ADP-P/M B"),
    17: ("Meteor Lake (Core Ultra)", "MTL-M/P A"),
    18: ("Lunar Lake (Core Ultra 2nd Gen)", "LNL-M A"),
    19: ("Arrow Lake / Panther Lake", "PTL A"),
    20: ("Nova Lake (Next-Gen)", "NVL A"),
    21: ("Next-Gen Ultra CSME 21+", "GEN21 A"),
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
            "sku": "Corporate LP",
            "sku_code": "COR_LP",
            "chipset": "TGP-LP B",
            "stepping": "B",
            "oem_config": "No",
            "date": "Unknown",
            "size_hex": "0x0",
            "fs_stage": "Unconfigured",
            "fs_state": "Unconfigured",
            "fitc_ver": "N/A",
            "full_tag": "Unknown",
            "is_valid_me": False,
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
                    for cid in unique_cpuids:
                        if cid in CPUID_MAP:
                            gen_str, chipset_val = CPUID_MAP[cid]
                            self.info["cpu_gen"] = f"Intel | {gen_str} | {', '.join(unique_cpuids)}"
                            self.info["chipset"] = chipset_val
                            return
                    self.info["cpu_gen"] = f"Intel | Generic Intel x86 | {', '.join(unique_cpuids)}"

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
                # Some dumps start within first 4KB
                p = data.find(SIG_FD, 0, min(0x1000, len(data)))
                if p != -1 and p + 0x50 <= len(data):
                    fd_pos = p

        if fd_pos != -1:
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

                        if reg_name == "ME / CSME":
                            self.info["me_fd_start"] = b_addr
                            self.info["me_fd_end"] = (limit + 1) * 0x1000

    def _parse_manifest(self):
        data = self.raw_data
        pos = 0
        mn2_entries = []

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

                if 6 <= major <= 35 and build > 0:
                    date_str = f"{year:04X}-{month:02X}-{day:02X}"
                    mn2_entries.append({
                        "major": major,
                        "minor": minor,
                        "hotfix": hotfix,
                        "build": build,
                        "date": date_str,
                        "hdr_start": hdr_start,
                        "pos": pos
                    })
            pos += 4

        if mn2_entries:
            primary = mn2_entries[0]
            for ent in mn2_entries:
                ctx = data[max(0, ent["hdr_start"] - 64) : min(len(data), ent["hdr_start"] + 64)]
                if b"FTPR" in ctx:
                    primary = ent
                    break

            self.info["is_valid_me"] = True
            self.info["major"] = primary["major"]
            self.info["minor"] = primary["minor"]
            self.info["hotfix"] = primary["hotfix"]
            self.info["build"] = primary["build"]
            self.info["version"] = f"{primary['major']}.{primary['minor']}.{primary['hotfix']}.{primary['build']}"
            self.info["date"] = primary["date"]
            self.info["family"] = "CSE ME" if primary["major"] >= 11 else "Intel ME"
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
            self.info["fs_stage"] = "N/A"
            self.info["warnings"].append("No Flash Partition Table ($FPT) detected!")
            return

        has_oem_config = False
        fitc_part_found = False
        oemp_part_found = False
        cdmd_part_found = False
        mfsb_part_found = False
        mfs_buf = None

        primary_fpt = found_fpts[0]
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
                    elif pname == "MFSB" and p_valid:
                        mfsb_part_found = True
                    elif pname in ["UTOK", "STKN"] and p_valid:
                        has_oem_config = True

                    if pname in ["MFS", "MFSB"]:
                        if abs_p + psize <= len(data):
                            mfs_buf = data[abs_p : abs_p + psize]

        # Calculate exact 4KB-aligned payload size of ME Region
        me_start = self.info["me_fd_start"]
        me_end = self.info["me_fd_end"]
        if me_end > me_start and me_start > 0:
            scan_end = min(len(data), me_end)
            me_chunk = data[me_start:scan_end]
            non_ff_len = len(me_chunk.rstrip(b"\xFF"))
            if non_ff_len > 0:
                payload_size = (non_ff_len + 0xFFF) & ~0xFFF
                self.info["size_hex"] = f"0x{payload_size:X}"
            else:
                self.info["size_hex"] = f"0x{me_end - me_start:X}"
        else:
            self.info["size_hex"] = f"0x{self.file_size:X}"

        fs_state, mfs_has_oem_file = self._determine_mfs_state(
            mfs_buf,
            has_oem_config=(has_oem_config or oemp_part_found or fitc_part_found or cdmd_part_found or mfsb_part_found)
        )

        if mfs_has_oem_file or oemp_part_found or fitc_part_found:
            has_oem_config = True

        self.info["oem_config"] = "Yes" if has_oem_config else "No"
        self.info["fs_stage"] = fs_state
        self.info["fs_state"] = fs_state

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
            return ("Configured" if has_oem_config else "Unconfigured"), False

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
            return ("Configured" if has_oem_config else "Unconfigured"), False

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
            return ("Configured" if has_oem_config else "Unconfigured"), False

        c0 = all_chunks_dict[0]
        vol_sig, ftbl_dict, ftbl_plat, ftbl_res, vol_size, vol_file_rec = struct.unpack("<IBBHIH", c0[:14])
        if vol_sig != 0x724F6201:
            return ("Configured" if has_oem_config else "Unconfigured"), False

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

        if is_initialized:
            return "Initialized", True

        has_cfg_files = False
        for idx in (7, 9):
            if idx < len(fat_values) and fat_values[idx] not in (0x0000, 0xFFFE, 0xFFFF):
                has_cfg_files = True
                break

        if has_cfg_files or has_oem_config:
            return "Configured", has_cfg_files

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
        major = self.info["major"]

        if "Unknown" in self.info["cpu_gen"] and major in GEN_FAMILY_MAP:
            gen_str, pch_code = GEN_FAMILY_MAP[major]
            self.info["cpu_gen"] = f"Intel | {gen_str}"
            if self.info["chipset"] == "Unknown":
                self.info["chipset"] = pch_code

        chipset = self.info["chipset"]
        if " " in chipset:
            parts = chipset.split()
            stepping = parts[-1]
        else:
            stepping = "B"

        release = "PRD"
        me_type = "EXTR-N" if self.info["fs_stage"] != "Configured" else "EXTR-Y"

        ver = self.info["version"]
        sku_code = self.info["sku_code"]
        self.info["full_tag"] = f"{ver}_{sku_code}_{stepping}_{release}_{me_type}"


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
        f"File System State: {info['fs_stage']}",
        f"FITC: {info['fitc_ver']}",
        f"CSME Full Version: {info['full_tag']}"
    ]
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
        ("File System State",     info["fs_stage"],                                              "#34d399", True),  # Mint Green
        ("FITC Version",          info["fitc_ver"],                                              "#facc15", True),  # Yellow
        ("CSME Full Version",     info["full_tag"],                                              "#38bdf8", True),  # Sky Blue
    ]
    
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
