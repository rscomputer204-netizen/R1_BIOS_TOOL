"""
report_settings_ui.py
======================
Professional Cyber Blue UI for Report Display Settings.
Controls which analysis sections are displayed in the terminal.
"""

import os
import json
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QCheckBox, QFrame, QScrollArea, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QCursor


class ReportSettingsManager:
    """Manages persistent report display preferences."""

    def __init__(self, root_dir):
        self.config_path = os.path.join(root_dir, 'config', 'report_settings.json')
        self.default_settings = {
            "show_spi_region_map":  True,   # SPI Region Map (Descriptor, BIOS, ME, GbE...) - ON by default
            "show_flash_partition": False,  # Flash Partition Table (FPT)
            "show_bpdt":            False,  # Boot Partition Descriptor Table (BPDT/IFWI)
            "show_cse_layout":      False,  # CSE Layout Table (Code/Data partitions)
            "show_normal_analysis": True,   # Normal Analyze (Basic MEAnalyzer run) - ON by default
            "show_bios_analysis":   False,  # BIOS Analysis Report (ME Family/Version/SKU...)
            "show_pmc_pchc_phy":    True,   # PMC / PCHC / PHY Independent firmware info
            "show_me_warnings":     False,  # ME Firmware Notes / Warnings / Errors
            "show_microcode":       False,  # Intel Microcode Audit (via MCExtractor)
        }
        self.settings = self.load_settings()

    def load_settings(self):
        if not os.path.exists(os.path.dirname(self.config_path)):
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                merged = self.default_settings.copy()
                merged.update(data)
                return merged
            except Exception:
                pass

        self.save_settings(self.default_settings)
        return self.default_settings.copy()

    def save_settings(self, settings_dict):
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(settings_dict, f, indent=4)
            self.settings = settings_dict
            return True
        except Exception:
            return False

    def get(self, key, default=True):
        return self.settings.get(key, default)


# ─────────────────────────────────────────────────────────────────────────────
# STYLESHEET
# ─────────────────────────────────────────────────────────────────────────────

_DIALOG_STYLE = """
QDialog {
    background-color: #0b0f15;
    color: #e2e8f0;
    font-family: 'Segoe UI', -apple-system, sans-serif;
}
QScrollArea {
    background: transparent;
    border: none;
}
QScrollArea > QWidget > QWidget {
    background: transparent;
}
QScrollBar:vertical {
    background: #090d13;
    width: 8px;
    margin: 0;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #1e293b;
    min-height: 25px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #0284c7;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""

_CARD_STYLE = """
QFrame#ReportCard {
    background: #0e1520;
    border: 1px solid #1a2536;
    border-radius: 8px;
}
QFrame#ReportItem {
    background: transparent;
    border: none;
    border-radius: 6px;
    padding: 2px 4px;
}
QFrame#ReportItem:hover {
    background: #131d2b;
}
"""

_CHECKBOX_STYLE = """
QCheckBox {
    color: #e2e8f0;
    font-size: 13px;
    font-weight: 700;
    spacing: 10px;
}
QCheckBox::indicator {
    width: 17px;
    height: 17px;
    border-radius: 4px;
    border: 1px solid #1e293b;
    background: #090e15;
}
QCheckBox::indicator:hover {
    border: 1px solid #00f3ff;
    background: #0e1724;
}
QCheckBox::indicator:checked {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0052cc, stop:1 #00f3ff);
    border: 1px solid #00f3ff;
}
"""

_BUTTON_STYLE = """
QPushButton {
    font-family: 'Segoe UI', sans-serif;
    font-weight: 700;
    border-radius: 5px;
    padding: 7px 16px;
    font-size: 11px;
    letter-spacing: 0.5px;
}
QPushButton#btnSelectAction {
    background: #0f1824;
    color: #38bdf8;
    border: 1px solid #0284c7;
}
QPushButton#btnSelectAction:hover {
    background: #162438;
    border: 1px solid #00f3ff;
    color: #ffffff;
}
QPushButton#btnCancel {
    background: #111824;
    border: 1px solid #1e293b;
    color: #94a3b8;
}
QPushButton#btnCancel:hover {
    background: #182232;
    color: #ffffff;
    border: 1px solid #334155;
}
QPushButton#btnSave {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0052cc, stop:1 #00f3ff);
    color: #05131e;
    border: none;
    font-weight: 800;
    font-size: 12px;
    padding: 9px 24px;
}
QPushButton#btnSave:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0066ff, stop:1 #38bdf8);
    color: #ffffff;
}
"""


# ─────────────────────────────────────────────────────────────────────────────
# DIALOG IMPLEMENTATION
# ─────────────────────────────────────────────────────────────────────────────

class ReportSettingsDialog(QDialog):
    """Modern, professional settings dialog for selecting terminal report sections."""

    def __init__(self, manager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self._build_ui()
        self._load_states()

    def _build_ui(self):
        self.setWindowTitle("Report Display Settings")
        self.setMinimumWidth(560)
        self.setMinimumHeight(660)
        self.resize(580, 700)
        self.setStyleSheet(_DIALOG_STYLE + _CARD_STYLE + _CHECKBOX_STYLE + _BUTTON_STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 18)
        root.setSpacing(12)

        # 1. Header Section
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)

        title = QLabel("REPORT DISPLAY SETTINGS", self)
        title.setStyleSheet("font-size: 16px; font-weight: 900; color: #00f3ff; letter-spacing: 1.5px;")

        desc = QLabel(
            "Select which analysis modules to display in the terminal log after loading a BIOS image.\n"
            "Each option controls an independent report section.",
            self
        )
        desc.setStyleSheet("color: #7dd3fc; font-size: 11px; line-height: 1.4;")
        desc.setWordWrap(True)

        header_layout.addWidget(title)
        header_layout.addWidget(desc)
        root.addLayout(header_layout)

        # 2. Quick Selection Bar
        quick_row = QHBoxLayout()
        btn_all = QPushButton("SELECT ALL", self)
        btn_all.setObjectName("btnSelectAction")
        btn_all.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_all.clicked.connect(self._select_all)

        btn_none = QPushButton("DESELECT ALL", self)
        btn_none.setObjectName("btnSelectAction")
        btn_none.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_none.clicked.connect(self._select_none)

        quick_row.addWidget(btn_all)
        quick_row.addWidget(btn_none)
        quick_row.addStretch()
        root.addLayout(quick_row)

        # Divider
        divider = QFrame(self)
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("background-color: #1a2536; max-height: 1px; border: none;")
        root.addWidget(divider)

        # 3. Scrollable Area for Report Groups
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 4, 0)
        scroll_layout.setSpacing(12)
        scroll.setWidget(scroll_content)

        # ── Group 1: Flash Memory Map ──
        c1, l1 = self._create_card("FLASH MEMORY MAP")
        self.cb_region = self._add_option(
            l1,
            "SPI Region Map",
            "Flash memory layout - Intel Flash Descriptor, BIOS Region, ME/CSME, GbE, EC & Platform Data",
            is_accent=True
        )
        scroll_layout.addWidget(c1)

        # ── Group 2: Partition Tables ──
        c2, l2 = self._create_card("PARTITION TABLES", hint="Requires ME Analyzer -dfpt")
        self.cb_fpt = self._add_option(
            l2,
            "Flash Partition Table (FPT)",
            "Detailed ME partition entries - Name, Offset, Size, Flags & End physical address"
        )
        self.cb_bpdt = self._add_option(
            l2,
            "Boot Partition Descriptor Table (BPDT / IFWI)",
            "IFWI boot partition structures - SMIP, RBEP, FTPR, NFTP, DLMP, OBBP"
        )
        self.cb_cse = self._add_option(
            l2,
            "CSE Layout Table (LT)",
            "Code and Data partition layout - RoM, Data, Boot, Config offsets and boundaries"
        )
        scroll_layout.addWidget(c2)

        # ── Group 3: Firmware Analysis ──
        c3, l3 = self._create_card("FIRMWARE ANALYSIS", hint="Powered by R1 CSME Analyzer")
        self.cb_normal = self._add_option(
            l3,
            "Normal Raw Analysis",
            "Direct analyzer stream - Full comprehensive technical log",
            is_accent=True
        )
        self.cb_mea = self._add_option(
            l3,
            "BIOS & ME Analysis Summary",
            "Core identification - Family, Version, SKU, Release, Platform, Production Date, SVN, VCN"
        )
        self.cb_pmc = self._add_option(
            l3,
            "PMC / PCHC / PHY Independent Firmware",
            "Power Management Controller, PCH Configuration & USB Type-C PHY firmware states",
            is_accent=True
        )
        self.cb_warnings = self._add_option(
            l3,
            "Firmware Health & Security Warnings",
            "Integrity checks, advisory notes, mismatch warnings and error flags"
        )
        scroll_layout.addWidget(c3)

        # ── Group 4: CPU Microcode ──
        c4, l4 = self._create_card("CPU MICROCODE AUDIT", hint="Powered by MCExtractor Engine")
        self.cb_micro = self._add_option(
            l4,
            "Intel / AMD Microcode Audit",
            "Embedded processor microcode entries - CPUID, Platform, Revision, Date & Checksum"
        )
        scroll_layout.addWidget(c4)

        scroll_layout.addStretch()
        root.addWidget(scroll, 1)

        # 4. Bottom Footer & Action Buttons
        footer_divider = QFrame(self)
        footer_divider.setFrameShape(QFrame.Shape.HLine)
        footer_divider.setStyleSheet("background-color: #1a2536; max-height: 1px; border: none;")
        root.addWidget(footer_divider)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("CANCEL", self)
        btn_cancel.setObjectName("btnCancel")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton("SAVE SETTINGS", self)
        btn_save.setObjectName("btnSave")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.clicked.connect(self._save_and_close)

        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        root.addLayout(btn_row)

    def _create_card(self, title_text: str, hint: str = ""):
        """Creates a modern styled card frame with a clean header."""
        card = QFrame(self)
        card.setObjectName("ReportCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        hdr_row = QHBoxLayout()
        title_lbl = QLabel(title_text, card)
        title_lbl.setStyleSheet("color: #00f3ff; font-weight: 800; font-size: 11px; letter-spacing: 1px;")
        hdr_row.addWidget(title_lbl)

        if hint:
            hint_lbl = QLabel(hint, card)
            hint_lbl.setStyleSheet("color: #475569; font-size: 10px; font-weight: 600;")
            hdr_row.addStretch()
            hdr_row.addWidget(hint_lbl)
        else:
            hdr_row.addStretch()

        layout.addLayout(hdr_row)

        card_div = QFrame(card)
        card_div.setFrameShape(QFrame.Shape.HLine)
        card_div.setStyleSheet("background-color: #16202c; max-height: 1px; border: none;")
        layout.addWidget(card_div)

        return card, layout

    def _add_option(self, parent_layout: QVBoxLayout, title: str, subtitle: str, is_accent: bool = False) -> QCheckBox:
        """Adds a unified, cleanly aligned checkbox item row."""
        item_frame = QFrame(self)
        item_frame.setObjectName("ReportItem")

        item_layout = QVBoxLayout(item_frame)
        item_layout.setContentsMargins(4, 4, 4, 4)
        item_layout.setSpacing(2)

        cb = QCheckBox(title, item_frame)
        cb.setCursor(Qt.CursorShape.PointingHandCursor)
        if is_accent:
            cb.setStyleSheet("color: #00f3ff; font-size: 12px; font-weight: 700; spacing: 10px;")
        else:
            cb.setStyleSheet("color: #e2e8f0; font-size: 12px; font-weight: 600; spacing: 10px;")

        hint = QLabel(subtitle, item_frame)
        hint.setStyleSheet("color: #7e8f9f; font-size: 11px; padding-left: 27px; line-height: 1.3;")
        hint.setWordWrap(True)

        item_layout.addWidget(cb)
        item_layout.addWidget(hint)

        parent_layout.addWidget(item_frame)
        return cb

    def _all_checkboxes(self):
        return [
            self.cb_region, self.cb_fpt, self.cb_bpdt, self.cb_cse,
            self.cb_normal, self.cb_mea, self.cb_pmc, self.cb_warnings, self.cb_micro
        ]

    def _select_all(self):
        for cb in self._all_checkboxes():
            cb.setChecked(True)

    def _select_none(self):
        for cb in self._all_checkboxes():
            cb.setChecked(False)

    def _load_states(self):
        s = self.manager.settings if self.manager else {}
        self.cb_region.setChecked(s.get("show_spi_region_map", True))
        self.cb_fpt.setChecked(s.get("show_flash_partition", False))
        self.cb_bpdt.setChecked(s.get("show_bpdt", False))
        self.cb_cse.setChecked(s.get("show_cse_layout", False))
        self.cb_normal.setChecked(s.get("show_normal_analysis", True))
        self.cb_mea.setChecked(s.get("show_bios_analysis", False))
        self.cb_pmc.setChecked(s.get("show_pmc_pchc_phy", True))
        self.cb_warnings.setChecked(s.get("show_me_warnings", False))
        self.cb_micro.setChecked(s.get("show_microcode", False))

    def _save_and_close(self):
        new_settings = {
            "show_spi_region_map":  self.cb_region.isChecked(),
            "show_flash_partition": self.cb_fpt.isChecked(),
            "show_bpdt":            self.cb_bpdt.isChecked(),
            "show_cse_layout":      self.cb_cse.isChecked(),
            "show_normal_analysis": self.cb_normal.isChecked(),
            "show_bios_analysis":   self.cb_mea.isChecked(),
            "show_pmc_pchc_phy":    self.cb_pmc.isChecked(),
            "show_me_warnings":     self.cb_warnings.isChecked(),
            "show_microcode":       self.cb_micro.isChecked(),
        }
        self.manager.save_settings(new_settings)
        self.accept()
