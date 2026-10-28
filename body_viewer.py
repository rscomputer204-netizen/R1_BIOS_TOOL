# -*- coding: utf-8 -*-
"""
R1 BIOS TOOL - BODY VIEWER (UEFI Structure Tree & Body Inspector)
Parses Intel Flash Descriptors, UEFI Firmware Volumes, FFS Files, and Sections.
Provides interactive Tree View with Extract Body, Extract As Is, and Hex Viewer inspection.
"""

import os
import sys
import struct
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

        for base, reg_dict in regions_found:
            # If this is BIOS region, parse its inner UEFI volumes!
            if reg_dict["subtype"] in ("BIOS", "BIOS2"):
                self.parse_uefi_volumes(data, reg_dict["offset"], reg_dict["size"], reg_dict)
            root["children"].append(reg_dict)

    def parse_uefi_volumes(self, data: bytes, region_offset: int, region_size: int, parent_dict: dict):
        """Scans for Firmware Volumes (_FVH) within the region and parses them."""
        region_data = data[region_offset : region_offset + region_size]
        curr_pos = 0
        fv_idx = 0

        while True:
            fvh_pos = region_data.find(UEFI_FV_SIG, curr_pos)
            if fvh_pos == -1:
                break

            header_offset = fvh_pos - 40
            if header_offset >= 0 and header_offset + 56 <= len(region_data):
                fv_abs_offset = region_offset + header_offset
                fs_guid_raw = region_data[header_offset + 16 : header_offset + 32]
                fv_len = struct.unpack_from("<Q", region_data, header_offset + 32)[0]
                hdr_len = struct.unpack_from("<H", region_data, header_offset + 48)[0]

                if 56 <= hdr_len <= fv_len and fv_len <= (len(region_data) - header_offset):
                    guid_str = format_guid(fs_guid_raw)
                    subtype_name = "Volume (FFS v2)" if "7A9354D9" in guid_str else "Volume (FFS v3)" if "6422D35F" in guid_str else "Volume"

                    fv_node = {
                        "name": f"Volume #{fv_idx}",
                        "action": "",
                        "type": "Volume",
                        "subtype": subtype_name,
                        "text": f"Offset: 0x{fv_abs_offset:08X}, Size: {fv_len/1024:.1f} KB",
                        "offset": fv_abs_offset,
                        "size": fv_len,
                        "body_offset": fv_abs_offset + hdr_len,
                        "body_size": fv_len - hdr_len,
                        "children": []
                    }

                    # Parse FFS files inside this Volume
                    self.parse_ffs_files(region_data, header_offset, fv_len, hdr_len, fv_abs_offset, fv_node)
                    parent_dict["children"].append(fv_node)
                    fv_idx += 1
                    curr_pos = header_offset + fv_len
                    continue

            curr_pos = fvh_pos + 4

    def parse_ffs_files(self, region_data: bytes, fv_start: int, fv_len: int, hdr_len: int, fv_abs: int, fv_node: dict):
        """Iterates through FFS files inside a Firmware Volume."""
        f_pos = fv_start + hdr_len
        f_end = fv_start + fv_len

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

    def parse_sections(self, region_data: bytes, s_start: int, s_total: int, sec_abs: int, file_node: dict) -> str:
        """Parses EFI sections inside an FFS file and extracts the UI Name if present."""
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
                "text": sec_text or f"Size: {s_size} B",
                "offset": current_abs,
                "size": s_size,
                "body_offset": current_abs + 4,
                "body_size": s_size - 4,
                "children": []
            }
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
    request_hex_view = Signal(int) # Emits offset to jump in Hex Viewer

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

        # Modern Dark Cyberpunk QTreeWidget Stylesheet
        self.tree.setStyleSheet("""
            QTreeWidget {
                background-color: #0b0d13;
                color: #cbd5e1;
                border: 1px solid #1a202c;
                border-radius: 6px;
                font-family: 'Segoe UI', Consolas, monospace;
                font-size: 11px;
                padding: 4px;
            }
            QTreeWidget::item {
                height: 24px;
                padding: 2px 4px;
                border-radius: 3px;
            }
            QTreeWidget::item:hover {
                background-color: #1a2230;
                color: #ffffff;
            }
            QTreeWidget::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1a3a47, stop:1 #132733);
                color: #0ef6fd;
                border-left: 2px solid #0ef6fd;
            }
            QHeaderView::section {
                background-color: #131720;
                color: #94a3b8;
                padding: 5px 8px;
                font-weight: bold;
                font-size: 11px;
                border: 1px solid #1e2633;
                border-bottom: 2px solid #2d3748;
            }
            QTreeWidget::branch:has-children:!has-siblings:closed,
            QTreeWidget::branch:closed:has-children:has-siblings {
                border-image: none;
                image: none;
            }
            QScrollBar:vertical {
                background: #0b0d13;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #232c3d;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #0ef6fd;
            }
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

        # Expand first 2 levels for immediate preview
        for i in range(root_item.childCount()):
            child = root_item.child(i)
            child.setExpanded(True)

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
            if subtype == "BIOS":
                item.setForeground(0, QColor("#4cd3e3"))
            elif subtype == "ME":
                item.setForeground(0, QColor("#ff5252"))
            elif subtype == "Descriptor":
                item.setForeground(0, QColor("#4ade80"))
            else:
                item.setForeground(0, QColor("#fbbf24"))
            item.setFont(0, QFont("Segoe UI", 9, QFont.Bold))
        elif node_type == "Volume":
            item.setForeground(0, QColor("#38bdf8"))
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
            self.request_hex_view.emit(offset)

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
            self.request_hex_view.emit(node.get("offset", 0))
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
