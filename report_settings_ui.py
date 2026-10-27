import os
import json
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QCheckBox, QFrame, QGroupBox,
                               QScrollArea, QWidget)
from PySide6.QtCore import Qt


class ReportSettingsManager:
    def __init__(self, root_dir):
        self.config_path = os.path.join(root_dir, 'config', 'report_settings.json')
        self.default_settings = {
            "show_spi_region_map":  True,   # SPI Region Map (Descriptor, BIOS, ME, GbE...) — ON by default
            "show_flash_partition": False,  # Flash Partition Table (FPT)
            "show_bpdt":            False,  # Boot Partition Descriptor Table (BPDT/IFWI)
            "show_cse_layout":      False,  # CSE Layout Table (Code/Data partitions)
            "show_normal_analysis": True,   # Normal Analyze (Basic MEAnalyzer run) — ON by default
            "show_bios_analysis":   False,  # BIOS Analysis Report (ME Family/Version/SKU...)
            "show_pmc_pchc_phy":    False,  # PMC / PCHC / PHY Independent firmware info
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

_STYLE = """
QDialog {
    background-color: #171a1d;
    color: #e2e8f0;
    font-family: 'Segoe UI', sans-serif;
}
QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }
QLabel  { color: #e2e8f0; }
QGroupBox {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #252a2e, stop:1 #1c2024);
    color: #4cd3e3;
    font-weight: bold;
    font-size: 13px;
    border: 1px solid #2d363f;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 16px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
}
QCheckBox {
    color: #e2e8f0;
    font-size: 13px;
    padding: 6px 4px;
    spacing: 10px;
    font-weight: 500;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #333d47;
    background: #14171a;
}
QCheckBox::indicator:checked {
    background: #2ac4db;
    border: 1px solid #0ef6fd;
    image: none;
}
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3c444a, stop:1 #2d3338);
    color: #c8d6e0;
    border: 1px solid #4a545c;
    border-radius: 6px;
    padding: 8px 20px;
    font-weight: bold;
    font-size: 12px;
}
QPushButton:hover { background-color: #47525a; color: #ffffff; }
QPushButton#btnSave {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8fe3ea, stop:0.4 #3598a6, stop:1 #247d8a);
    color: #0d171c;
    border: 1px solid #0ef6fd;
    font-weight: 800;
}
QPushButton#btnSave:hover { background: #0ef6fd; color: #000000; }
QPushButton#btnAll {
    background-color: #172522;
    color: #00ff88;
    border: 1px solid #1f4a3c;
    border-radius: 4px;
    padding: 6px 14px;
    font-size: 11px;
    font-weight: bold;
}
QPushButton#btnAll:hover { background-color: #1f4a3c; color: #ffffff; }
QPushButton#btnNone {
    background-color: #2a1c1d;
    color: #ff5252;
    border: 1px solid #4a2123;
    border-radius: 4px;
    padding: 6px 14px;
    font-size: 11px;
    font-weight: bold;
}
QPushButton#btnNone:hover { background-color: #4a2123; color: #ffffff; }
"""

# ─────────────────────────────────────────────────────────────────────────────

class ReportSettingsDialog(QDialog):
    def __init__(self, manager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self._build_ui()
        self._load_states()

    # ── Build UI ─────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.setWindowTitle("Report Display Settings")
        self.setMinimumWidth(540)
        self.setMinimumHeight(620)
        self.setStyleSheet(_STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(26, 22, 26, 18)
        root.setSpacing(8)

        # ── Header ───────────────────────────────────────────────────────────
        title = QLabel("Report Display Settings")
        title.setStyleSheet("font-size: 18px; font-weight: 800; color: #4cd3e3; font-family: 'Segoe UI', sans-serif; letter-spacing: 1px;")
        root.addWidget(title)

        desc = QLabel(
            "Choose which reports to display in the terminal after a scan.\n"
            "Each checkbox controls exactly one independent report — no mixing."
        )
        desc.setStyleSheet("color: #94a3b8; font-size: 11px;")
        desc.setWordWrap(True)
        root.addWidget(desc)

        # ── Select All / None buttons ─────────────────────────────────────────
        quick_row = QHBoxLayout()
        btn_all  = QPushButton("✔ Select All")
        btn_none = QPushButton("✘ Deselect All")
        btn_all.setObjectName("btnAll")
        btn_none.setObjectName("btnNone")
        btn_all.clicked.connect(self._select_all)
        btn_none.clicked.connect(self._select_none)
        quick_row.addWidget(btn_all)
        quick_row.addWidget(btn_none)
        quick_row.addStretch()
        root.addLayout(quick_row)

        div = QFrame(); div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet("color: #2d363f; max-height: 1px; border: none; background-color: #2d363f;"); root.addWidget(div)

        # ── Scrollable area for checkboxes ───────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(6)
        scroll.setWidget(scroll_content)

        # ── Group 1: Flash Map ────────────────────────────────────────────────
        g1 = QGroupBox("🗺  Flash Memory Map")
        l1 = QVBoxLayout(g1); l1.setSpacing(2); l1.setContentsMargins(14, 14, 14, 10)

        self.cb_region = self._cb(
            "SPI Region Map",
            "Flash memory layout — Descriptor, BIOS, ME/CsME, GbE, Platform Data, EC...",
            "#00c8ff", l1
        )
        scroll_layout.addWidget(g1)

        # ── Group 2: Partition Tables ─────────────────────────────────────────
        g2 = QGroupBox("📋  Partition Tables  (requires ME Analyzer -dfpt)")
        l2 = QVBoxLayout(g2); l2.setSpacing(2); l2.setContentsMargins(14, 14, 14, 10)

        self.cb_fpt = self._cb(
            "Flash Partition Table  (FPT)",
            "ME firmware partition entries — Name, Offset, Size, End address",
            "#FFA500", l2
        )
        l2.addSpacing(6)
        self.cb_bpdt = self._cb(
            "Boot Partition Descriptor Table  (BPDT / IFWI)",
            "BPDT sub-partitions — SMIP, RBEP, FTPR, NFTP, DLMP, OBBP...",
            "#FF6B35", l2
        )
        l2.addSpacing(6)
        self.cb_cse = self._cb(
            "CSE Layout Table  (LT)",
            "Code & Data partition layout — RoM, Data, Boot, Config offsets & sizes",
            "#FFD700", l2
        )
        scroll_layout.addWidget(g2)

        # ── Group 3: Firmware Analysis ────────────────────────────────────────
        g3 = QGroupBox("🔍  Firmware Analysis  (requires ME Analyzer)")
        l3 = QVBoxLayout(g3); l3.setSpacing(2); l3.setContentsMargins(14, 14, 14, 10)

        self.cb_normal = self._cb(
            "Normal Analyze",
            "Basic scan without command-line arguments — only passes the file path",
            "#A855F7", l3
        )
        l3.addSpacing(6)
        self.cb_mea = self._cb(
            "BIOS / ME Analysis Report",
            "Family, Version, SKU, Release, Type, Platform, Date, SVN, VCN, LBG...",
            "#00ff88", l3
        )
        l3.addSpacing(6)
        self.cb_pmc = self._cb(
            "PMC / PCHC / PHY  Independent Firmware",
            "Power Mgmt Controller, PCH Config, USB Type-C PHY firmware details",
            "#00f3ff", l3
        )
        l3.addSpacing(6)
        self.cb_warnings = self._cb(
            "ME Firmware Notes & Warnings",
            "All Note/Warning/Error/Advisory messages detected by ME Analyzer",
            "#FF4444", l3
        )
        scroll_layout.addWidget(g3)

        # ── Group 4: CPU Microcode ────────────────────────────────────────────
        g4 = QGroupBox("🧮  CPU Microcode  (requires MCExtractor)")
        l4 = QVBoxLayout(g4); l4.setSpacing(2); l4.setContentsMargins(14, 14, 14, 10)

        self.cb_micro = self._cb(
            "Intel Microcode Audit",
            "Embedded CPU microcode entries — CPUID, Platform, Revision, Date, Checksum",
            "#ff88ff", l4
        )
        scroll_layout.addWidget(g4)

        scroll_layout.addStretch()
        root.addWidget(scroll, 1)

        # ── Buttons ───────────────────────────────────────────────────────────
        div2 = QFrame(); div2.setFrameShape(QFrame.Shape.HLine)
        div2.setStyleSheet("color: #1f2233;"); root.addWidget(div2)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Save Settings")
        btn_save.setObjectName("btnSave")
        btn_save.clicked.connect(self._save_and_close)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        root.addLayout(btn_row)

    @staticmethod
    def _cb(title_text, sub_text, color, layout):
        """Create a checkbox with a coloured title and descriptive subtitle."""
        row = QVBoxLayout()
        row.setSpacing(1)

        cb = QCheckBox(title_text)
        cb.setStyleSheet(f"color: {color}; font-weight: bold;")
        cb.setCursor(Qt.CursorShape.PointingHandCursor)

        hint = QLabel(f"    {sub_text}")
        hint.setStyleSheet("color: #555; font-size: 11px;")
        hint.setWordWrap(True)

        row.addWidget(cb)
        row.addWidget(hint)
        layout.addLayout(row)
        return cb

    def _all_checkboxes(self):
        return [self.cb_region, self.cb_fpt, self.cb_bpdt, self.cb_cse,
                self.cb_normal, self.cb_mea, self.cb_pmc, self.cb_warnings, self.cb_micro]

    def _select_all(self):
        for cb in self._all_checkboxes():
            cb.setChecked(True)

    def _select_none(self):
        for cb in self._all_checkboxes():
            cb.setChecked(False)

    # ── Load / Save ───────────────────────────────────────────────────────────
    def _load_states(self):
        s = self.manager.settings if self.manager else {}
        self.cb_region.setChecked(s.get("show_spi_region_map",  True))
        self.cb_fpt.setChecked(   s.get("show_flash_partition", False))
        self.cb_bpdt.setChecked(  s.get("show_bpdt",            False))
        self.cb_cse.setChecked(   s.get("show_cse_layout",      False))
        self.cb_normal.setChecked(s.get("show_normal_analysis",  False))
        self.cb_mea.setChecked(   s.get("show_bios_analysis",   True))
        self.cb_pmc.setChecked(   s.get("show_pmc_pchc_phy",    False))
        self.cb_warnings.setChecked(s.get("show_me_warnings",   True))
        self.cb_micro.setChecked( s.get("show_microcode",       False))

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
