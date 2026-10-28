# -*- coding: utf-8 -*-
"""
R1 BIOS TOOL - BODY VIEWER (UEFI Structure Tree & Body Inspector)
Parses Intel Flash Descriptors, UEFI Firmware Volumes, FFS Files, and Sections.
Provides interactive Tree View with Extract Body, Extract As Is, and Hex Viewer inspection.
"""

import os
import sys
import struct
import uuid
import lzma
from pathlib import Path
from PySide6.QtCore import Qt, QThread, Signal, Slot, QPoint
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTreeWidget, QTreeWidgetItem, QHeaderView,
    QMenu, QFileDialog, QMessageBox, QFrame, QSplitter
)
from PySide6.QtGui import QIcon, QFont, QColor, QCursor, QAction

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS & DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────
INTEL_FD_SIG = b"\x5A\xA5\xF0\x0F"
UEFI_FV_SIG = b"_FVH"

# Known NVRAM VSS2 and FTW GUIDs (little-endian bytes)
VSS2_STORE_GUIDS = (
    b"\x78\x2c\xf3\xaa\x7b\x94\x9a\x43\xa1\x80\x2e\x14\x4e\xc3\x77\x92", # AAF32C78-947B-439A-A180-2E144EC37792
    b"\x17\x36\xcf\xdd\x75\x32\x64\x41\x98\xb6\xfe\x85\x70\x7f\xfe\x7d", # DDCF3617-3275-4164-98B6-FE85707FFE7D
    b"\x16\x36\xcf\xdd\x75\x32\x64\x41\x98\xb6\xfe\x85\x70\x7f\xfe\x7d", # DDCF3616-3275-4164-98B6-FE85707FFE7D
)
FTW_STORE_GUIDS = (
    b"\x2b\x29\x58\x9e\x68\x7c\x7d\x49\x0a\xce\x65\x00\xfd\x9f\x1b\x95", # 9E58292B-7C68-497D-0ACE-6500FD9F1B95
    b"\x2b\x29\x58\x9e\x68\x7c\x7d\x49\xa0\xce\x65\x00\xfd\x9f\x1b\x95", # 9E58292B-7C68-497D-A0CE-6500FD9F1B95
)

FFS_FILE_TYPES = {
    0x01: "Raw",
    0x02: "Freeform",
    0x03: "Security core",
    0x04: "PEI core",
    0x05: "DXE core",
    0x06: "PEIM",
    0x07: "Driver",
    0x08: "Combined PEIM/driver",
    0x09: "Application",
    0x0A: "SMM",
    0x0B: "Volume image",
    0x0C: "Combined SMM/driver",
    0x0D: "SMM core",
    0xF0: "Pad",
}

SECTION_TYPES = {
    0x01: "Compression",
    0x02: "GUID defined",
    0x10: "PE32 image",
    0x11: "PIC image",
    0x12: "TE image",
    0x13: "DXE depex",
    0x14: "Version",
    0x15: "UI",
    0x16: "16-bit image",
    0x17: "Volume image",
    0x18: "Freeform subtype GUID",
    0x19: "Raw",
    0x1B: "PEI depex",
    0x1C: "SMM depex",
}

def format_guid(raw_16_bytes):
    """Formats 16 bytes into standard little-endian GUID string."""
    if len(raw_16_bytes) < 16:
        return ""
    d1, d2, d3 = struct.unpack_from("<IHH", raw_16_bytes, 0)
    d4 = raw_16_bytes[8:10]
    d5 = raw_16_bytes[10:16]
    return f"{d1:08X}-{d2:04X}-{d3:04X}-{d4.hex().upper()}-{d5.hex().upper()}"

KNOWN_VOLUME_GUIDS = {
    "7A9354D9-0468-444A-81CE-0BF617D890DF": ("EfiFirmwareFileSystem2..", "FFSv2"),
    "8C8CE578-8A3D-4F1C-9935-896185C32DD3": ("EfiFirmwareFileSystem2..", "FFSv2"),
    "5473C07A-3DCB-4DCA-BD6F-1E9689E7349A": ("EfiFirmwareFileSystem3..", "FFSv3"),
    "6422D35F-014F-4CC5-A1B0-B761FF30C670": ("EfiFirmwareFileSystem3..", "FFSv3"),
    "CEF5B9A3-F05D-4CE8-BD4F-707B09888174": ("EfiSystemNvDataFvGuid", "NVRAM"),
    "00504624-8A59-4EEB-BD0F-6B3680ED69AD": ("EfiSystemNvDataFvGuid", "NVRAM"),
    "FFF12B8D-7696-4C8B-A985-2747075B4F50": ("EfiSystemNvDataFvGuid", "NVRAM"),
}

def classify_padding(data_slice: bytes) -> str:
    """Classifies padding bytes into Empty (0xFF), Empty (0x00), or Non-empty."""
    if not data_slice:
        return "Empty"
    first = data_slice[0:1]
    if first == b"\xFF" and data_slice == b"\xFF" * len(data_slice):
        return "Empty (0xFF)"
    if first == b"\x00" and data_slice == b"\x00" * len(data_slice):
        return "Empty (0x00)"
    return "Non-empty"


# ─────────────────────────────────────────────────────────────────────────────
# BACKGROUND PARSER THREAD
# ─────────────────────────────────────────────────────────────────────────────
class StructureParserWorker(QThread):
    structure_ready = Signal(dict)
    progress_update = Signal(str)

    def __init__(self, file_path: str, raw_data: bytes = None):
        super().__init__()
        self.file_path = file_path
        self.raw_data = raw_data

    def run(self):
        try:
            if not self.raw_data and self.file_path and os.path.exists(self.file_path):
                with open(self.file_path, "rb") as f:
                    self.raw_data = f.read()

            if not self.raw_data:
                return

            self.progress_update.emit("Parsing Flash Descriptor...")
            tree_data = self.parse_firmware(self.raw_data)
            self.structure_ready.emit(tree_data)
        except Exception as e:
            self.progress_update.emit(f"Error parsing structure: {e}")

    def parse_firmware(self, data: bytes) -> dict:
        file_size = len(data)
        root = {
            "name": "Intel image" if data[0x10:0x14] == INTEL_FD_SIG else "Firmware image",
            "action": "",
            "type": "Image",
            "subtype": "Intel" if data[0x10:0x14] == INTEL_FD_SIG else "Generic",
            "text": f"Size: {file_size / (1024*1024):.2f} MB ({file_size:,} bytes)",
            "offset": 0,
            "size": file_size,
            "body_offset": 0,
            "body_size": file_size,
            "children": []
        }

        # Check Intel Flash Descriptor
        if data[0x10:0x14] == INTEL_FD_SIG:
            self.parse_intel_fd(data, root)
        else:
            # Standalone BIOS/UEFI dump or capsule
            self.parse_uefi_volumes(data, 0, file_size, root)

        return root

    def parse_intel_fd(self, data: bytes, root: dict):
        flmap0 = struct.unpack_from("<I", data, 0x14)[0]
        frba_val = (flmap0 >> 16) & 0xFF
        frba_offset = frba_val << 4

        region_names = [
            ("Descriptor region", "Descriptor"),
            ("BIOS region", "BIOS"),
            ("ME region", "ME"),
            ("GbE region", "GbE"),
            ("Platform Data region", "PDR"),
            ("DevExp region", "DevExp"),
            ("BIOS2 region", "BIOS2"),
            ("Microcode region", "Microcode"),
            ("EC region", "EC"),
            ("GbE2 region", "GbE2"),
        ]

        regions_found = []
        for i in range(12):
            if frba_offset + (i * 4) + 4 > len(data):
                break
            reg_val = struct.unpack_from("<I", data, frba_offset + (i * 4))[0]
            base_raw = reg_val & 0x7FFF
            lim_raw = (reg_val >> 16) & 0x7FFF

            if base_raw == 0x7FFF or lim_raw < base_raw:
                continue

            base = base_raw << 12
            limit = (lim_raw << 12) | 0xFFF
            size = (limit - base) + 1

            if base >= len(data):
                continue
            actual_size = min(size, len(data) - base)

            name, subtype = region_names[i] if i < len(region_names) else (f"Region {i}", f"Reg{i}")
            reg_dict = {
                "name": name,
                "action": "",
                "type": "Region",
                "subtype": subtype,
                "text": f"0x{base:08X} - 0x{limit:08X} ({actual_size / 1024:.0f} KB)",
                "offset": base,
                "size": actual_size,
                "body_offset": base,
                "body_size": actual_size,
                "children": []
            }
            regions_found.append((base, reg_dict))

        # Sort regions by offset
        regions_found.sort(key=lambda x: x[0])

        last_reg_end = 0
        for base, reg_dict in regions_found:
            # Insert Padding gap if regions are non-contiguous
            if base > last_reg_end:
                gap = data[last_reg_end:base]
                root["children"].append({
                    "name": "Padding",
                    "action": "",
                    "type": "Padding",
                    "subtype": classify_padding(gap),
                    "text": "",
                    "offset": last_reg_end,
                    "size": len(gap),
                    "body_offset": last_reg_end,
                    "body_size": len(gap),
                    "children": []
                })

            # If this is BIOS region, parse its inner UEFI volumes!
            if reg_dict["subtype"] in ("BIOS", "BIOS2"):
                self.parse_uefi_volumes(data, reg_dict["offset"], reg_dict["size"], reg_dict)
            elif reg_dict["subtype"] == "ME":
                self.parse_me_region(data, reg_dict["offset"], reg_dict["size"], reg_dict)
            root["children"].append(reg_dict)
            last_reg_end = base + reg_dict["size"]

        if last_reg_end < len(data):
            gap = data[last_reg_end:]
            root["children"].append({
                "name": "Padding",
                "action": "",
                "type": "Padding",
                "subtype": classify_padding(gap),
                "text": "",
                "offset": last_reg_end,
                "size": len(gap),
                "body_offset": last_reg_end,
                "body_size": len(gap),
                "children": []
            })

    def parse_me_region(self, data: bytes, me_offset: int, me_size: int, parent_dict: dict):
        """Parses ME region into IFWI / BPDT partitions and inner CPD/FPT sub-structures."""
        me_data = data[me_offset : me_offset + me_size]
        if len(me_data) < 32:
            return

        # Check for BPDT / IFWI Header (0x000055AA or 0x00AA55AA)
        bpdt_pos = -1
        for sig in (b"\xaa\x55\x00\x00", b"\xaa\x55\xaa\x00", b"\xaa\x55\xaa\x55"):
            pos = me_data[:0x4000].find(sig)
            if pos != -1:
                bpdt_pos = pos
                break

        if bpdt_pos != -1:
            if bpdt_pos > 0:
                gap = me_data[:bpdt_pos]
                parent_dict["children"].append({
                    "name": "Padding", "action": "", "type": "Padding", "subtype": classify_padding(gap),
                    "text": "", "offset": me_offset, "size": len(gap), "body_offset": me_offset, "body_size": len(gap), "children": []
                })

            b_slice = me_data[bpdt_pos:]
            magic, desc_count, ver, flag = struct.unpack_from("<IHBB", b_slice, 0)
            hdr_size = 24 if ver >= 2 else 16
            hdr_name = "IFWI 1.7 header" if (ver == 2 or flag == 1) else "IFWI 1.6 header" if ver == 1 else f"IFWI {ver}.0 header"

            parent_dict["children"].append({
                "name": hdr_name, "action": "", "type": "IFWI header", "subtype": "",
                "text": "", "offset": me_offset + bpdt_pos, "size": hdr_size, "body_offset": me_offset + bpdt_pos, "body_size": hdr_size, "children": []
            })

            entries = []
            for i in range(min(desc_count, 32)):
                entry_off = bpdt_pos + hdr_size + i * 12
                if entry_off + 12 > len(me_data):
                    break
                flags, p_offset, p_size = struct.unpack_from("<III", me_data, entry_off)
                if p_size > 0 and (p_offset + p_size) <= len(me_data):
                    entries.append((i, flags, p_offset, p_size))

            entries.sort(key=lambda x: x[2])
            curr_pos = bpdt_pos + hdr_size + desc_count * 12

            for i, flags, p_offset, p_size in entries:
                part_rel = bpdt_pos + p_offset
                part_abs = me_offset + part_rel

                if part_rel > curr_pos:
                    gap = me_data[curr_pos:part_rel]
                    parent_dict["children"].append({
                        "name": "Padding", "action": "", "type": "Padding", "subtype": classify_padding(gap),
                        "text": "", "offset": me_offset + curr_pos, "size": len(gap), "body_offset": me_offset + curr_pos, "body_size": len(gap), "children": []
                    })

                p_subtype = "Boot" if (flags & 0x40000) or (flags & 0xFFFF in (1, 2, 4, 6, 7)) else "Data"
                p_name = f"{p_subtype} partition"
                p_node = {
                    "name": p_name, "action": "", "type": "IFWI partition", "subtype": p_subtype,
                    "text": "", "offset": part_abs, "size": p_size,
                    "body_offset": part_abs, "body_size": p_size, "children": []
                }

                # Parse inner CPD / FPT subpartitions inside this partition
                part_bytes = me_data[part_rel : part_rel + p_size]
                if part_bytes.startswith(b"$CPD"):
                    cpd_num = struct.unpack_from("<I", part_bytes, 4)[0] if len(part_bytes) >= 8 else 0
                    cpd_hdr_len = part_bytes[10] if len(part_bytes) > 10 and part_bytes[10] >= 16 else 20
                    cpd_name = part_bytes[12:16].decode("ascii", errors="ignore").strip("\x00")
                    if cpd_name:
                        p_node["text"] = f"{cpd_name} ({p_size/1024:.0f} KB)"
                    for ci in range(min(cpd_num, 32)):
                        c_ent = cpd_hdr_len + ci * 24
                        if c_ent + 24 <= len(part_bytes):
                            c_name = part_bytes[c_ent : c_ent + 12].decode("ascii", errors="ignore").strip("\x00")
                            c_flags = struct.unpack_from("<I", part_bytes, c_ent + 12)[0]
                            c_off = c_flags & 0x01FFFFFF
                            c_len = struct.unpack_from("<I", part_bytes, c_ent + 16)[0] if c_ent + 20 <= len(part_bytes) else 0
                            if c_name and c_len > 0:
                                p_node["children"].append({
                                    "name": c_name, "action": "", "type": "Subpartition", "subtype": "CPD",
                                    "text": f"Size: {c_len} B", "offset": part_abs + c_off, "size": c_len,
                                    "body_offset": part_abs + c_off, "body_size": c_len, "children": []
                                })
                elif b"$FPT" in part_bytes[:0x1000]:
                    f_off = part_bytes.find(b"$FPT")
                    self._parse_fpt_entries(part_bytes, part_abs, f_off, p_node)

                parent_dict["children"].append(p_node)
                curr_pos = part_rel + p_size

            if curr_pos < len(me_data):
                gap = me_data[curr_pos:]
                parent_dict["children"].append({
                    "name": "Padding", "action": "", "type": "Padding", "subtype": classify_padding(gap),
                    "text": "", "offset": me_offset + curr_pos, "size": len(gap), "body_offset": me_offset + curr_pos, "body_size": len(gap), "children": []
                })
            return

        # Direct $FPT Header check
        fpt_pos = me_data.find(b"$FPT")
        if fpt_pos != -1:
            self._parse_fpt_entries(me_data, me_offset, fpt_pos, parent_dict)

    def _parse_fpt_entries(self, data_block: bytes, base_abs_offset: int, fpt_pos: int, parent_node: dict):
        """Helper to parse FPT entries into parent node."""
        if fpt_pos > 0:
            gap = data_block[:fpt_pos]
            parent_node["children"].append({
                "name": "Padding", "action": "", "type": "Padding", "subtype": classify_padding(gap),
                "text": "", "offset": base_abs_offset, "size": len(gap), "body_offset": base_abs_offset, "body_size": len(gap), "children": []
            })

        parent_node["children"].append({
            "name": "Intel ME header", "action": "", "type": "ME header", "subtype": "",
            "text": "", "offset": base_abs_offset + fpt_pos, "size": 32, "body_offset": base_abs_offset + fpt_pos, "body_size": 32, "children": []
        })
        num_entries = struct.unpack_from("<I", data_block, fpt_pos + 4)[0] if fpt_pos + 8 <= len(data_block) else 0
        entry_size = 32
        last_end = fpt_pos + 32
        for i in range(min(num_entries, 16)):
            e_off = fpt_pos + 32 + i * entry_size
            if e_off + entry_size > len(data_block):
                break
            name_raw = data_block[e_off : e_off + 4].decode("ascii", errors="ignore").strip("\x00")
            part_offset = struct.unpack_from("<I", data_block, e_off + 8)[0]
            part_length = struct.unpack_from("<I", data_block, e_off + 12)[0]

            if part_offset > last_end:
                gap = data_block[last_end:part_offset]
                parent_node["children"].append({
                    "name": "Padding", "action": "", "type": "Padding", "subtype": classify_padding(gap),
                    "text": "", "offset": base_abs_offset + last_end, "size": len(gap), "body_offset": base_abs_offset + last_end, "body_size": len(gap), "children": []
                })

            parent_node["children"].append({
                "name": f"{name_raw} partition", "action": "", "type": "ME partition", "subtype": name_raw,
                "text": f"0x{base_abs_offset + part_offset:08X} ({part_length/1024:.0f} KB)",
                "offset": base_abs_offset + part_offset, "size": part_length,
                "body_offset": base_abs_offset + part_offset, "body_size": part_length, "children": []
            })
            last_end = part_offset + part_length

        if last_end < len(data_block):
            gap = data_block[last_end:]
            parent_node["children"].append({
                "name": "Padding", "action": "", "type": "Padding", "subtype": classify_padding(gap),
                "text": "", "offset": base_abs_offset + last_end, "size": len(gap), "body_offset": base_abs_offset + last_end, "body_size": len(gap), "children": []
            })

    def parse_uefi_volumes(self, data: bytes, region_offset: int, region_size: int, parent_dict: dict):
        """Scans for Firmware Volumes (_FVH), inserts Paddings, and names volumes exactly like UEFITool."""
        region_data = data[region_offset : region_offset + region_size]
        curr_pos = 0

        # Pass 1: Find all valid Firmware Volumes
        found_volumes = []
        while True:
            fvh_pos = region_data.find(UEFI_FV_SIG, curr_pos)
            if fvh_pos == -1:
                break

            header_offset = fvh_pos - 40
            if header_offset >= 0 and header_offset + 56 <= len(region_data):
                fs_guid_raw = region_data[header_offset + 16 : header_offset + 32]
                fv_len = struct.unpack_from("<Q", region_data, header_offset + 32)[0]
                hdr_len = struct.unpack_from("<H", region_data, header_offset + 48)[0]
                ext_hdr_off = struct.unpack_from("<H", region_data, header_offset + 0x34)[0]

                if 56 <= hdr_len <= fv_len and fv_len <= (len(region_data) - header_offset):
                    guid_str = format_guid(fs_guid_raw)

                    # Read FvName from Extended Header if present (UEFITool standard)
                    fv_name_guid = ""
                    if ext_hdr_off != 0 and header_offset + ext_hdr_off + 16 <= len(region_data):
                        ext_raw = region_data[header_offset + ext_hdr_off : header_offset + ext_hdr_off + 16]
                        if ext_raw not in (b"\x00" * 16, b"\xFF" * 16):
                            fv_name_guid = format_guid(ext_raw)

                    found_volumes.append((header_offset, fv_len, hdr_len, guid_str, fv_name_guid, ext_hdr_off))
                    curr_pos = header_offset + fv_len
                    continue

            curr_pos = fvh_pos + 4

        # Pass 2: Build tree with Paddings between volumes
        last_end = 0
        for v_off, v_len, h_len, v_guid, fv_name_guid, v_ext_off in found_volumes:
            # Check gap before this volume
            if v_off > last_end:
                gap_data = region_data[last_end:v_off]
                pad_subtype = classify_padding(gap_data)
                gap_abs = region_offset + last_end
                parent_dict["children"].append({
                    "name": "Padding",
                    "action": "",
                    "type": "Padding",
                    "subtype": pad_subtype,
                    "text": "",
                    "offset": gap_abs,
                    "size": len(gap_data),
                    "body_offset": gap_abs,
                    "body_size": len(gap_data),
                    "children": []
                })

            fv_abs_offset = region_offset + v_off

            # Determine distinct name and subtype matching UEFITool exactly
            if fv_name_guid:
                vol_name = f"{fv_name_guid[:23]}.."
                vol_subtype = "FFSv3" if "6422D35F" in v_guid else "FFSv2"
            elif v_guid in KNOWN_VOLUME_GUIDS:
                vol_name, vol_subtype = KNOWN_VOLUME_GUIDS[v_guid]
            else:
                vol_name = f"{v_guid[:23]}.." if len(v_guid) > 23 else v_guid
                vol_subtype = "Unknown" if v_guid == "00000000-0000-0000-0000-000000000000" else "FFSv2"

            fv_node = {
                "name": vol_name,
                "action": "",
                "type": "Volume",
                "subtype": vol_subtype,
                "text": "",
                "offset": fv_abs_offset,
                "size": v_len,
                "body_offset": fv_abs_offset + h_len,
                "body_size": v_len - h_len,
                "children": []
            }

            # If NVRAM volume, parse NVRAM stores (VSS2, FTW, Free space)
            if vol_subtype == "NVRAM":
                self.parse_nvram_stores(region_data, v_off, v_len, h_len, fv_abs_offset, fv_node)
            else:
                # Parse FFS files inside this Volume with accurate ext_hdr_off alignment
                self.parse_ffs_files(region_data, v_off, v_len, h_len, fv_abs_offset, fv_node, v_ext_off)

            parent_dict["children"].append(fv_node)
            last_end = v_off + v_len

        # Check trailing gap after last volume
        if last_end < len(region_data):
            gap_data = region_data[last_end:]
            pad_subtype = classify_padding(gap_data)
            gap_abs = region_offset + last_end
            parent_dict["children"].append({
                "name": "Padding",
                "action": "",
                "type": "Padding",
                "subtype": pad_subtype,
                "text": "",
                "offset": gap_abs,
                "size": len(gap_data),
                "body_offset": gap_abs,
                "body_size": len(gap_data),
                "children": []
            })

    def parse_nvram_stores(self, region_data: bytes, v_start: int, v_len: int, hdr_len: int, fv_abs: int, fv_node: dict):
        """Parses VSS/VSS2 stores with inner NVRAM variables, FTW store, and Free space."""
        nv_data = region_data[v_start + hdr_len : v_start + v_len]

        vss_found = False
        # 1. Search for VSS2 Store by GUID
        for g in VSS2_STORE_GUIDS:
            pos = nv_data.find(g)
            if pos != -1:
                vss_abs = fv_abs + hdr_len + pos
                v_sz = struct.unpack_from("<I", nv_data, pos + 16)[0] if pos + 20 <= len(nv_data) else 0x10000
                v_sz = min(v_sz, len(nv_data) - pos)
                vss_node = {
                    "name": "VSS2 store", "action": "", "type": "VSS2 store", "subtype": "",
                    "text": f"Size: {v_sz:,} bytes", "offset": vss_abs, "size": v_sz,
                    "body_offset": vss_abs + 28, "body_size": max(0, v_sz - 28), "children": []
                }

                # Parse inner variables inside VSS2 store
                store_bytes = nv_data[pos : pos + v_sz]
                curr_var = 28
                while curr_var + 64 <= len(store_bytes):
                    start_id = struct.unpack_from("<H", store_bytes, curr_var)[0]
                    if start_id != 0x55AA:
                        if store_bytes[curr_var : curr_var + 8] == b"\xFF" * 8:
                            break
                        curr_var = (curr_var + 4) & ~3
                        continue

                    name_sz = struct.unpack_from("<I", store_bytes, curr_var + 36)[0]
                    data_sz = struct.unpack_from("<I", store_bytes, curr_var + 40)[0]
                    if 2 <= name_sz <= 512 and data_sz <= len(store_bytes):
                        try:
                            v_name = store_bytes[curr_var + 60 : curr_var + 60 + name_sz].decode("utf-16le", errors="ignore").rstrip("\x00")
                            if v_name.isprintable() and len(v_name) > 0:
                                tot_len = 60 + name_sz + data_sz
                                vss_node["children"].append({
                                    "name": v_name, "action": "", "type": "Variable", "subtype": "VSS2",
                                    "text": f"Size: {data_sz:,} bytes", "offset": vss_abs + curr_var, "size": tot_len,
                                    "body_offset": vss_abs + curr_var + 60 + name_sz, "body_size": data_sz, "children": []
                                })
                                curr_var = (curr_var + tot_len + 3) & ~3
                                continue
                        except Exception:
                            pass
                    curr_var = (curr_var + 4) & ~3

                fv_node["children"].append(vss_node)
                vss_found = True
                break

        if not vss_found:
            for sig in (b"$VSS2", b"$VSS", b"NVAR"):
                pos = nv_data.find(sig)
                if pos != -1:
                    store_name = "VSS2 store" if sig == b"$VSS2" else "VSS store" if sig == b"$VSS" else "NVAR store"
                    fv_node["children"].append({
                        "name": store_name, "action": "", "type": store_name, "subtype": "",
                        "text": "", "offset": fv_abs + hdr_len + pos, "size": 0x10000,
                        "body_offset": fv_abs + hdr_len + pos, "body_size": 0x10000, "children": []
                    })
                    break

        # 2. Search for FTW store by GUID
        ftw_found = False
        for g in FTW_STORE_GUIDS:
            ftw_pos = nv_data.find(g)
            if ftw_pos != -1:
                ftw_abs = fv_abs + hdr_len + ftw_pos
                fv_node["children"].append({
                    "name": "FTW store", "action": "", "type": "FTW store", "subtype": "",
                    "text": "", "offset": ftw_abs, "size": 0x2000,
                    "body_offset": ftw_abs, "body_size": 0x2000, "children": []
                })
                ftw_found = True
                break

        if not ftw_found:
            ftw_pos = nv_data.find(b"$FTW")
            if ftw_pos == -1:
                ftw_pos = nv_data.find(b"\x46\x54\x57\x20")
            if ftw_pos != -1:
                fv_node["children"].append({
                    "name": "FTW store", "action": "", "type": "FTW store", "subtype": "",
                    "text": "", "offset": fv_abs + hdr_len + ftw_pos, "size": 0x1000,
                    "body_offset": fv_abs + hdr_len + ftw_pos, "body_size": 0x1000, "children": []
                })

        # 3. Add Free space
        if fv_node["children"]:
            last_used = max(c["offset"] + c["size"] - fv_abs for c in fv_node["children"])
            if last_used < v_len:
                free_len = v_len - last_used
                fv_node["children"].append({
                    "name": "Free space", "action": "", "type": "Free space", "subtype": "",
                    "text": f"Size: {free_len:,} bytes", "offset": fv_abs + last_used, "size": free_len,
                    "body_offset": fv_abs + last_used, "body_size": free_len, "children": []
                })
        else:
            fv_node["children"].append({
                "name": "Free space", "action": "", "type": "Free space", "subtype": "",
                "text": f"Size: {v_len:,} bytes", "offset": fv_abs + hdr_len, "size": v_len - hdr_len,
                "body_offset": fv_abs + hdr_len, "body_size": v_len - hdr_len, "children": []
            })

    def parse_ffs_files(self, region_data: bytes, fv_start: int, fv_len: int, hdr_len: int, fv_abs: int, fv_node: dict, ext_hdr_off: int = 0):
        """Iterates through FFS files inside a Firmware Volume."""
        f_end = fv_start + fv_len

        # Account for Extended Header offset & size
        if ext_hdr_off != 0 and fv_start + ext_hdr_off + 20 <= f_end:
            ext_hdr_size = struct.unpack_from("<I", region_data, fv_start + ext_hdr_off + 16)[0]
            first_file = (ext_hdr_off + ext_hdr_size + 7) & ~7
        else:
            first_file = (hdr_len + 7) & ~7

        f_pos = fv_start + first_file

        while f_pos + 24 <= f_end:
            # Check for volume free space / erase polarity (all 0xFF or 0x00)
            if region_data[f_pos : f_pos + 8] in (b"\xFF" * 8, b"\x00" * 8):
                break

            f_guid_raw = region_data[f_pos : f_pos + 16]
            f_type = region_data[f_pos + 18]
            f_size = struct.unpack("<I", region_data[f_pos + 20 : f_pos + 23] + b"\x00")[0]

            if f_size <= 24 or (f_pos + f_size) > f_end:
                # Corrupt or unaligned, step forward 8 bytes
                f_pos = (f_pos + 8) & ~7
                continue

            file_abs = fv_abs + (f_pos - fv_start)
            guid_str = format_guid(f_guid_raw)
            type_name = FFS_FILE_TYPES.get(f_type, f"Type 0x{f_type:02X}")

            file_node = {
                "name": guid_str if f_type != 0xF0 else "Padding",
                "action": "",
                "type": "File",
                "subtype": type_name,
                "text": f"Size: {f_size} bytes",
                "offset": file_abs,
                "size": f_size,
                "body_offset": file_abs + 24,
                "body_size": f_size - 24,
                "children": []
            }

            # Parse inner Sections inside the FFS File
            ui_name = self.parse_sections(region_data, f_pos + 24, f_size - 24, file_abs + 24, file_node)
            if ui_name:
                file_node["text"] = f"{ui_name} ({f_size} B)"

            fv_node["children"].append(file_node)
            # FFS files are 8-byte aligned
            f_pos = (f_pos + f_size + 7) & ~7

        # Add Free space or Padding for remaining space in volume
        if f_pos < f_end:
            free_len = f_end - f_pos
            free_abs = fv_abs + (f_pos - fv_start)
            free_data = region_data[f_pos : f_end]
            sub_pad = classify_padding(free_data)
            fv_node["children"].append({
                "name": "Free space" if sub_pad.startswith("Empty") else "Padding",
                "action": "",
                "type": "Free space" if sub_pad.startswith("Empty") else "Padding",
                "subtype": sub_pad if not sub_pad.startswith("Empty") else "",
                "text": f"Size: {free_len:,} bytes",
                "offset": free_abs,
                "size": free_len,
                "body_offset": free_abs,
                "body_size": free_len,
                "children": []
            })

    def parse_sections(self, region_data: bytes, s_start: int, s_total: int, sec_abs: int, file_node: dict) -> str:
        """Parses EFI sections inside an FFS file, decompresses inner volume images, and extracts the UI Name."""
        s_pos = s_start
        s_end = s_start + s_total
        found_ui_name = ""

        while s_pos + 4 <= s_end:
            s_size = struct.unpack("<I", region_data[s_pos : s_pos + 3] + b"\x00")[0]
            s_type = region_data[s_pos + 3]

            if s_size < 4 or (s_pos + s_size) > s_end:
                break

            current_abs = sec_abs + (s_pos - s_start)
            sec_type_name = SECTION_TYPES.get(s_type, f"Section 0x{s_type:02X}")
            sec_text = ""

            # Check for UI section (UTF-16 human name)
            if s_type == 0x15: # EFI_SECTION_USER_INTERFACE
                ui_bytes = region_data[s_pos + 4 : s_pos + s_size]
                try:
                    found_ui_name = ui_bytes.decode("utf-16le", errors="ignore").rstrip("\x00")
                    sec_text = found_ui_name
                except Exception:
                    pass

            sec_node = {
                "name": f"{sec_type_name} section",
                "action": "",
                "type": "Section",
                "subtype": sec_type_name,
                "text": sec_text or f"Size: {s_size:,} bytes",
                "offset": current_abs,
                "size": s_size,
                "body_offset": current_abs + 4,
                "body_size": s_size - 4,
                "children": []
            }

            # Decompress nested volume images inside GUID_DEFINED or COMPRESSION sections
            if s_type == 0x02 and s_size > 24: # EFI_SECTION_GUID_DEFINED
                data_off = struct.unpack_from("<H", region_data, s_pos + 20)[0]
                if data_off < s_size:
                    comp_data = region_data[s_pos + data_off : s_pos + s_size]
                    decomp = None
                    try:
                        decomp = lzma.decompress(comp_data)
                    except Exception:
                        for skip in (4, 8, 12):
                            if skip < len(comp_data):
                                try:
                                    decomp = lzma.decompress(comp_data[skip:])
                                    break
                                except Exception:
                                    pass
                    if decomp and b"_FVH" in decomp:
                        self.parse_uefi_volumes(decomp, 0, len(decomp), sec_node)

            elif s_type == 0x01 and s_size > 8: # EFI_SECTION_COMPRESSION
                comp_data = region_data[s_pos + 8 : s_pos + s_size]
                decomp = None
                try:
                    decomp = lzma.decompress(comp_data)
                except Exception:
                    pass
                if decomp and b"_FVH" in decomp:
                    self.parse_uefi_volumes(decomp, 0, len(decomp), sec_node)

            elif s_type == 0x17 and s_size > 4: # EFI_SECTION_FIRMWARE_VOLUME_IMAGE
                fv_img_data = region_data[s_pos + 4 : s_pos + s_size]
                if b"_FVH" in fv_img_data:
                    self.parse_uefi_volumes(fv_img_data, 0, len(fv_img_data), sec_node)

            file_node["children"].append(sec_node)
            # Sections are 4-byte aligned
            s_pos = (s_pos + s_size + 3) & ~3

        return found_ui_name


# ─────────────────────────────────────────────────────────────────────────────
# MAIN BODY VIEWER WIDGET (UI)
# ─────────────────────────────────────────────────────────────────────────────
class BodyViewerWidget(QWidget):
    """
    UEFI Structure & Body Viewer Tree Widget.
    Provides identical tree hierarchy, inspection, search, and body extraction as UEFITool.
    """
    request_hex_view = Signal(int, int) # Emits (offset, size) to jump and highlight in Hex Viewer

    def __init__(self, parent=None):
        super().__init__(parent)
        self.raw_data = None
        self.file_path = ""
        self.parser_worker = None
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        # ── 1. Top Control & Search Bar ──
        ctrl_bar = QWidget()
        ctrl_bar.setStyleSheet("""
            QWidget {
                background: #11141a;
                border: 1px solid #1f252e;
                border-radius: 6px;
            }
        """)
        ctrl_layout = QHBoxLayout(ctrl_bar)
        ctrl_layout.setContentsMargins(6, 4, 6, 4)
        ctrl_layout.setSpacing(6)

        lbl_title = QLabel("STRUCTURE EXPLORER")
        lbl_title.setStyleSheet("color: #4cd3e3; font-weight: bold; font-size: 11px; letter-spacing: 0.5px; border: none; background: transparent;")
        ctrl_layout.addWidget(lbl_title)

        ctrl_layout.addStretch()

        # Search Input
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Filter (e.g. Setup, ME)...")
        self.txt_search.setMinimumWidth(110)
        self.txt_search.setMaximumWidth(180)
        self.txt_search.setStyleSheet("""
            QLineEdit {
                background-color: #0b0d12;
                color: #e2e8f0;
                border: 1px solid #28303d;
                border-radius: 4px;
                padding: 3px 8px;
                font-size: 11px;
                font-family: 'Segoe UI', sans-serif;
            }
            QLineEdit:focus {
                border-color: #0ef6fd;
            }
        """)
        self.txt_search.textChanged.connect(self.filter_tree)
        ctrl_layout.addWidget(self.txt_search)

        # Expand / Collapse Buttons
        btn_style = """
            QPushButton {
                background: #1c222b;
                color: #94a3b8;
                border: 1px solid #2d3748;
                border-radius: 4px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #2a3442;
                color: #4cd3e3;
                border-color: #4cd3e3;
            }
        """
        self.btn_expand = QPushButton("➕ Expand")
        self.btn_expand.setStyleSheet(btn_style)
        self.btn_expand.setCursor(Qt.PointingHandCursor)
        self.btn_expand.clicked.connect(self.tree_expand_all)
        ctrl_layout.addWidget(self.btn_expand)

        self.btn_collapse = QPushButton("➖ Collapse")
        self.btn_collapse.setStyleSheet(btn_style)
        self.btn_collapse.setCursor(Qt.PointingHandCursor)
        self.btn_collapse.clicked.connect(self.tree_collapse_all)
        ctrl_layout.addWidget(self.btn_collapse)

        # Extract Body Button
        self.btn_extract_body = QPushButton("💾 Extract Body")
        self.btn_extract_body.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10707f, stop:1 #0c5663);
                color: #e6ffff;
                border: 1px solid #0ef6fd;
                border-radius: 4px;
                padding: 3px 10px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #0ef6fd;
                color: #0b151a;
            }
        """)
        self.btn_extract_body.setCursor(Qt.PointingHandCursor)
        self.btn_extract_body.clicked.connect(self.extract_selected_body)
        ctrl_layout.addWidget(self.btn_extract_body)

        main_layout.addWidget(ctrl_bar)

        # ── 2. Structure Tree Widget ──
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Name", "Action", "Type", "Subtype", "Text"])
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        self.tree.itemSelectionChanged.connect(self.on_item_selected)
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)

        # Resolve White Tree Arrow indicators
        from path_utils import get_app_root
        assets_dir = (Path(get_app_root()) / "assets").as_posix()
        arr_closed = f"{assets_dir}/tree_arrow_closed.svg"
        arr_open = f"{assets_dir}/tree_arrow_open.svg"
        arr_closed_hover = f"{assets_dir}/tree_arrow_closed_hover.svg"
        arr_open_hover = f"{assets_dir}/tree_arrow_open_hover.svg"

        # Modern Dark Cyberpunk QTreeWidget Stylesheet with Glowing White Expanders
        self.tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: #0b0d13;
                color: #cbd5e1;
                border: 1px solid #1a202c;
                border-radius: 6px;
                font-family: 'Segoe UI', Consolas, monospace;
                font-size: 11px;
                padding: 4px;
            }}
            QTreeWidget::item {{
                height: 24px;
                padding: 2px 4px;
                border-radius: 3px;
            }}
            QTreeWidget::item:hover {{
                background-color: #1a2230;
                color: #ffffff;
            }}
            QTreeWidget::item:selected {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1a3a47, stop:1 #132733);
                color: #0ef6fd;
                border-left: 2px solid #0ef6fd;
            }}
            QHeaderView::section {{
                background-color: #131720;
                color: #94a3b8;
                padding: 5px 8px;
                font-weight: bold;
                font-size: 11px;
                border: 1px solid #1e2633;
                border-bottom: 2px solid #2d3748;
            }}
            /* Crisp White Tree Branch Expander Arrows */
            QTreeWidget::branch:has-children:!has-siblings:closed,
            QTreeWidget::branch:closed:has-children:has-siblings {{
                border-image: none;
                image: url("{arr_closed}");
            }}
            QTreeWidget::branch:open:has-children:!has-siblings,
            QTreeWidget::branch:open:has-children:has-siblings {{
                border-image: none;
                image: url("{arr_open}");
            }}
            QTreeWidget::branch:has-children:!has-siblings:closed:hover,
            QTreeWidget::branch:closed:has-children:has-siblings:hover {{
                border-image: none;
                image: url("{arr_closed_hover}");
            }}
            QTreeWidget::branch:open:has-children:!has-siblings:hover,
            QTreeWidget::branch:open:has-children:has-siblings:hover {{
                border-image: none;
                image: url("{arr_open_hover}");
            }}
            QScrollBar:vertical {{
                background: #0b0d13;
                width: 10px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: #232c3d;
                border-radius: 5px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: #0ef6fd;
            }}
        """)

        # Set Column Resizing
        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.resizeSection(0, 220)
        header.resizeSection(1, 60)
        header.resizeSection(2, 75)
        header.resizeSection(3, 95)

        main_layout.addWidget(self.tree)

        # ── 3. Bottom Status / Detail Bar ──
        self.status_bar = QWidget()
        self.status_bar.setStyleSheet("""
            QWidget {
                background: #0d1017;
                border: 1px solid #1a202c;
                border-radius: 4px;
            }
        """)
        sb_layout = QHBoxLayout(self.status_bar)
        sb_layout.setContentsMargins(10, 4, 10, 4)
        sb_layout.setSpacing(16)

        self.lbl_selected_info = QLabel("No item selected")
        self.lbl_selected_info.setStyleSheet("color: #64748b; font-size: 11px; font-family: Consolas, monospace; border: none; background: transparent;")
        sb_layout.addWidget(self.lbl_selected_info)

        sb_layout.addStretch()

        self.lbl_tree_stats = QLabel("Tree: 0 items")
        self.lbl_tree_stats.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: bold; border: none; background: transparent;")
        sb_layout.addWidget(self.lbl_tree_stats)

        main_layout.addWidget(self.status_bar)

    # ─────────────────────────────────────────────────────────────────────────
    # PUBLIC SLOTS / METHODS
    # ─────────────────────────────────────────────────────────────────────────
    def clear(self):
        """Reset and clear tree, search input, and status labels."""
        if hasattr(self, 'parser_worker') and self.parser_worker and self.parser_worker.isRunning():
            try:
                self.parser_worker.terminate()
                self.parser_worker.wait(200)
            except Exception:
                pass
        self.parser_worker = None
        self.file_path = ""
        self.raw_data = None
        if hasattr(self, 'tree'):
            self.tree.clear()
        if hasattr(self, 'txt_search'):
            self.txt_search.blockSignals(True)
            self.txt_search.clear()
            self.txt_search.blockSignals(False)
        if hasattr(self, 'lbl_selected_info'):
            self.lbl_selected_info.setText("No item selected")
        if hasattr(self, 'lbl_tree_stats'):
            self.lbl_tree_stats.setText("Tree: 0 items")

    def load_bios_file(self, file_path: str, raw_data: bytes = None):
        """Called automatically when a BIOS file is dragged & dropped or opened."""
        self.file_path = file_path
        self.raw_data = raw_data
        self.tree.clear()
        self.lbl_selected_info.setText(f"Loading structure: {os.path.basename(file_path)}...")

        # Run parsing in background thread to guarantee ZERO latency
        self.parser_worker = StructureParserWorker(file_path, raw_data)
        self.parser_worker.structure_ready.connect(self.populate_tree)
        self.parser_worker.progress_update.connect(lambda msg: self.lbl_selected_info.setText(msg))
        self.parser_worker.start()

    @Slot(dict)
    def populate_tree(self, tree_data: dict):
        self.tree.clear()
        if not tree_data:
            self.lbl_selected_info.setText("Failed to parse structure")
            return

        total_items = [0]
        root_item = self._create_tree_item(tree_data, total_items)
        self.tree.addTopLevelItem(root_item)
        root_item.setExpanded(True)
        # Keep region children collapsed by default so the tree is clean and organized,
        # exactly like UEFITool. The user can expand BIOS/ME regions with the arrow when desired.

        self.lbl_selected_info.setText(f"Structure ready: {os.path.basename(self.file_path)}")
        self.lbl_tree_stats.setText(f"Nodes: {total_items[0]:,} items")

    def _create_tree_item(self, node_dict: dict, total_counter: list) -> QTreeWidgetItem:
        total_counter[0] += 1
        item = QTreeWidgetItem([
            node_dict.get("name", ""),
            node_dict.get("action", ""),
            node_dict.get("type", ""),
            node_dict.get("subtype", ""),
            node_dict.get("text", "")
        ])

        # Attach raw metadata dictionary for extraction & inspector
        item.setData(0, Qt.UserRole, node_dict)

        # Type-based visual styling
        node_type = node_dict.get("type", "")
        subtype = node_dict.get("subtype", "")
        if node_type == "Image":
            item.setForeground(0, QColor("#0ef6fd"))
            item.setFont(0, QFont("Segoe UI", 10, QFont.Bold))
        elif node_type == "Region":
            sub_lower = subtype.lower()
            if "descriptor" in sub_lower:
                item.setForeground(0, QColor("#4ade80"))  # Emerald Green
            elif "me" in sub_lower:
                item.setForeground(0, QColor("#ff5252"))  # Coral Red
            elif "bios" in sub_lower:
                item.setForeground(0, QColor("#00e5ff"))  # Electric Cyan
            elif "ec" in sub_lower:
                item.setForeground(0, QColor("#c084fc"))  # Purple / Violet (distinct from GbE!)
            elif "gbe" in sub_lower:
                item.setForeground(0, QColor("#fbbf24"))  # Amber / Gold
            elif "platform" in sub_lower:
                item.setForeground(0, QColor("#fb923c"))  # Tangerine Orange
            elif "microcode" in sub_lower:
                item.setForeground(0, QColor("#818cf8"))  # Indigo
            elif "devexp" in sub_lower:
                item.setForeground(0, QColor("#f472b6"))  # Pink
            elif "pmc" in sub_lower:
                item.setForeground(0, QColor("#a3e635"))  # Lime
            elif "pchc" in sub_lower:
                item.setForeground(0, QColor("#34d399"))  # Mint
            elif "phy" in sub_lower:
                item.setForeground(0, QColor("#60a5fa"))  # Sky Blue
            elif "ptt" in sub_lower:
                item.setForeground(0, QColor("#ff7043"))  # Deep Orange
            else:
                item.setForeground(0, QColor("#e2e8f0"))
            item.setFont(0, QFont("Segoe UI", 9, QFont.Bold))
        elif node_type == "Padding":
            item.setForeground(0, QColor("#64748b"))
            item.setForeground(3, QColor("#64748b"))
        elif node_type == "Volume":
            item.setForeground(0, QColor("#38bdf8"))
        elif "IFWI" in node_type or "ME" in node_type:
            item.setForeground(0, QColor("#f87171"))
        elif "store" in node_type or "Free space" in node_type or subtype == "NVRAM":
            item.setForeground(0, QColor("#fbbf24"))
        elif node_type == "File":
            if subtype == "Driver":
                item.setForeground(0, QColor("#a78bfa"))
            elif subtype == "Pad":
                item.setForeground(0, QColor("#64748b"))
            else:
                item.setForeground(0, QColor("#e2e8f0"))

        for child_dict in node_dict.get("children", []):
            child_item = self._create_tree_item(child_dict, total_counter)
            item.addChild(child_item)

        return item

    # ─────────────────────────────────────────────────────────────────────────
    # SELECTION & ACTIONS
    # ─────────────────────────────────────────────────────────────────────────
    def on_item_selected(self):
        items = self.tree.selectedItems()
        if not items:
            self.lbl_selected_info.setText("No item selected")
            return
        node = items[0].data(0, Qt.UserRole)
        if node:
            offset = node.get("offset", 0)
            size = node.get("size", 0)
            node_type = node.get("type", "")
            subtype = node.get("subtype", "")
            name = node.get("name", "")
            self.lbl_selected_info.setText(
                f"Selected: {name} | Type: {node_type} [{subtype}] | Offset: 0x{offset:08X} ({offset:,}) | Size: {size:,} bytes ({size/1024:.1f} KB)"
            )

    def on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        node = item.data(0, Qt.UserRole)
        if node:
            offset = node.get("body_offset", node.get("offset", 0))
            size = node.get("body_size", node.get("size", 1))
            self.request_hex_view.emit(offset, size)

    def show_context_menu(self, pos: QPoint):
        item = self.tree.itemAt(pos)
        if not item:
            return
        node = item.data(0, Qt.UserRole)
        if not node:
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #171a1d;
                color: #e2e8f0;
                border: 1px solid #2d3748;
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 3px;
            }
            QMenu::item:selected {
                background-color: #0ef6fd;
                color: #0b151a;
                font-weight: bold;
            }
        """)

        act_body = menu.addAction("💾 Extract body...")
        act_asis = menu.addAction("💾 Extract as is...")
        menu.addSeparator()
        act_hex = menu.addAction("🔍 Inspect in Hex Viewer")
        act_copy_guid = menu.addAction("📋 Copy Name / GUID")

        action = menu.exec(self.tree.viewport().mapToGlobal(pos))
        if action == act_body:
            self.extract_item_body(node, as_is=False)
        elif action == act_asis:
            self.extract_item_body(node, as_is=True)
        elif action == act_hex:
            offset = node.get("offset", 0)
            size = node.get("size", 1)
            self.request_hex_view.emit(offset, size)
        elif action == act_copy_guid:
            from PySide6.QtWidgets import QApplication
            QApplication.clipboard().setText(node.get("name", ""))

    def extract_selected_body(self):
        items = self.tree.selectedItems()
        if not items:
            QMessageBox.information(self, "Extract Body", "Please select an item from the Structure tree first.")
            return
        node = items[0].data(0, Qt.UserRole)
        if node:
            self.extract_item_body(node, as_is=False)

    def extract_item_body(self, node: dict, as_is: bool = False):
        if not self.raw_data and self.file_path and os.path.exists(self.file_path):
            with open(self.file_path, "rb") as f:
                self.raw_data = f.read()

        if not self.raw_data:
            QMessageBox.warning(self, "Error", "No firmware binary data is loaded.")
            return

        offset = node.get("offset", 0) if as_is else node.get("body_offset", node.get("offset", 0))
        size = node.get("size", 0) if as_is else node.get("body_size", node.get("size", 0))

        if offset + size > len(self.raw_data):
            size = max(0, len(self.raw_data) - offset)

        payload = self.raw_data[offset : offset + size]
        safe_name = "".join(c for c in node.get("name", "extracted_body") if c.isalnum() or c in ("_", "-")).strip() or "body"
        default_file = f"{safe_name}{'_asis' if as_is else '_body'}.bin"

        out_path, _ = QFileDialog.getSaveFileName(self, "Save Extracted Body", default_file, "Binary Files (*.bin);;All Files (*)")
        if out_path:
            with open(out_path, "wb") as f:
                f.write(payload)
            QMessageBox.information(
                self,
                "Extraction Success",
                f"Successfully extracted {'object' if as_is else 'body'} ({len(payload):,} bytes) to:\n{out_path}"
            )

    # ─────────────────────────────────────────────────────────────────────────
    # SEARCH & EXPANSION HELPERS
    # ─────────────────────────────────────────────────────────────────────────
    def filter_tree(self, text: str):
        query = text.strip().lower()
        def check_item(item: QTreeWidgetItem) -> bool:
            match = False
            for col in range(5):
                if query in item.text(col).lower():
                    match = True
                    break
            child_match = False
            for i in range(item.childCount()):
                if check_item(item.child(i)):
                    child_match = True
            is_visible = match or child_match or (not query)
            item.setHidden(not is_visible)
            if query and child_match:
                item.setExpanded(True)
            return is_visible

        for i in range(self.tree.topLevelItemCount()):
            check_item(self.tree.topLevelItem(i))

    def tree_expand_all(self):
        self.tree.expandAll()

    def tree_collapse_all(self):
        self.tree.collapseAll()
        # Keep top level expanded
        for i in range(self.tree.topLevelItemCount()):
            self.tree.topLevelItem(i).setExpanded(True)
