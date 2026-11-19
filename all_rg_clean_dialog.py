"""
all_rg_clean_dialog.py
======================
Ultra-clean, modern, professional region replacement dialog for ALL RG CLEAN.
Presents clean component targets, verified donor components, and surgical actions
without clutter, excessive labels, or unwieldy raw paths.
"""

import os
import re
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QWidget, QCheckBox, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QCursor


def clean_component_name(filename: str) -> str:
    """Extracts a clean, human-readable component name from official package filenames."""
    name = filename or ""
    if "--" in name:
        name = name.split("--", 1)[1].strip()
    name = re.sub(r"^\d+\s+", "", name)
    if name.lower().endswith(".bin"):
        name = name[:-4]
    return name.strip() or filename


def format_size(size_bytes: int) -> str:
    if size_bytes >= 1024 * 1024:
        mb = size_bytes / (1024 * 1024)
        return f"{mb:.1f} MB" if mb != int(mb) else f"{int(mb)} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes // 1024} KB"
    return f"{size_bytes} B"


class AllRgCleanDialog(QDialog):
    def __init__(self, matches: dict, parent=None):
        super().__init__(parent)
        self.matches = matches
        self.confirmed = False
        self.checkboxes = {}

        self.setWindowTitle("ALL RG CLEAN - REGION REPLACEMENT")
        self.setFixedSize(580, 440)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self.setStyleSheet("""
            QDialog {
                background-color: #070d19;
                border: 1px solid #1e293b;
                border-radius: 8px;
            }
            QLabel {
                font-family: 'Segoe UI', -apple-system, sans-serif;
            }
            QCheckBox {
                color: #f8fafc;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                font-weight: 700;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 17px;
                height: 17px;
                border: 1px solid #38bdf8;
                border-radius: 4px;
                background-color: #0f172a;
            }
            QCheckBox::indicator:checked {
                background-color: #00f2ff;
                border: 1px solid #00f2ff;
                image: none;
            }
        """)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        # Header Title
        title_lbl = QLabel("ALL RG CLEAN")
        title_lbl.setStyleSheet("color: #00f2ff; font-size: 16px; font-weight: 900; letter-spacing: 2px;")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_lbl)

        # Subtitle
        match_count = len(self.matches)
        sub_lbl = QLabel(f"Detected {match_count} verified component(s) ready for clean replacement:")
        sub_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sub_lbl)

        # Top Bar: Select / Deselect All
        top_bar = QHBoxLayout()
        hint_lbl = QLabel("Select regions you want to replace from the Official Update:")
        hint_lbl.setStyleSheet("color: #64748b; font-size: 10px; font-style: italic;")
        top_bar.addWidget(hint_lbl)
        top_bar.addStretch()

        btn_select_all = QPushButton("Select All")
        btn_select_all.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_select_all.setStyleSheet("QPushButton { background: transparent; color: #38bdf8; font-size: 10px; border: none; font-weight: 600; } QPushButton:hover { text-decoration: underline; color: #7dd3fc; }")
        btn_select_all.clicked.connect(lambda: self._set_all_checked(True))
        top_bar.addWidget(btn_select_all)

        lbl_slash = QLabel("•")
        lbl_slash.setStyleSheet("color: #334155; font-size: 10px;")
        top_bar.addWidget(lbl_slash)

        btn_desel_all = QPushButton("Deselect All")
        btn_desel_all.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_desel_all.setStyleSheet("QPushButton { background: transparent; color: #94a3b8; font-size: 10px; border: none; font-weight: 600; } QPushButton:hover { text-decoration: underline; color: #f1f5f9; }")
        btn_desel_all.clicked.connect(lambda: self._set_all_checked(False))
        top_bar.addWidget(btn_desel_all)

        layout.addLayout(top_bar)

        # Separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #1e293b;")
        layout.addWidget(sep)

        # Scroll Area for matched items
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #0f172a;
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #334155;
                border-radius: 3px;
            }
        """)

        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(0, 4, 4, 4)
        c_layout.setSpacing(10)

        for key, item in self.matches.items():
            card = QFrame()
            card.setStyleSheet("""
                QFrame {
                    background-color: #0b1329;
                    border: 1px solid #1e293b;
                    border-left: 3px solid #00f2ff;
                    border-radius: 7px;
                }
                QFrame:hover {
                    border-color: #334155;
                    border-left: 3px solid #38bdf8;
                }
            """)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(14, 10, 14, 10)
            card_layout.setSpacing(6)

            # Row 1: Checkbox + Target Size Pill + Status Badge
            top_row = QHBoxLayout()
            top_row.setSpacing(10)

            title = item.get("title", key.upper())
            cb = QCheckBox(title)
            cb.setChecked(True)
            cb.stateChanged.connect(self._on_check_changed)
            self.checkboxes[key] = cb
            top_row.addWidget(cb)

            top_row.addStretch()

            # Target Size & Offset Pill
            sz_str = format_size(item.get("size", 0))
            offset = item.get("offset")
            pill_text = f"{sz_str} • 0x{offset:X}" if offset is not None else sz_str
            pill = QLabel(pill_text)
            pill.setStyleSheet("""
                background-color: #0f172a;
                color: #38bdf8;
                border: 1px solid #1e293b;
                font-family: 'Consolas', monospace;
                font-size: 10px;
                font-weight: 600;
                padding: 2px 8px;
                border-radius: 4px;
            """)
            top_row.addWidget(pill)

            # Badge: WILL REPLACE / FACTORY RESET
            if key == "me":
                badge = QLabel("FACTORY RESET")
                badge.setStyleSheet("""
                    background-color: #083344;
                    color: #22d3ee;
                    border: 1px solid #0891b2;
                    border-radius: 4px;
                    font-size: 9px;
                    font-weight: 800;
                    padding: 3px 8px;
                    letter-spacing: 0.5px;
                """)
            else:
                badge = QLabel("WILL REPLACE")
                badge.setStyleSheet("""
                    background-color: #064e3b;
                    color: #34d399;
                    border: 1px solid #059669;
                    border-radius: 4px;
                    font-size: 9px;
                    font-weight: 800;
                    padding: 3px 8px;
                    letter-spacing: 0.5px;
                """)
            top_row.addWidget(badge)
            card_layout.addLayout(top_row)

            # Clean Info Row 1: Official Donor
            raw_fn = item.get("filename", "")
            clean_fn = clean_component_name(raw_fn)

            donor_row = QHBoxLayout()
            donor_row.setSpacing(6)
            tag_donor = QLabel("Official Donor:")
            tag_donor.setStyleSheet("color: #64748b; font-size: 10px; font-weight: 600;")
            donor_row.addWidget(tag_donor)

            val_donor = QLabel(clean_fn)
            val_donor.setToolTip(item.get("file", raw_fn))
            val_donor.setStyleSheet("color: #f1f5f9; font-size: 10px; font-weight: 500;")
            donor_row.addWidget(val_donor)
            donor_row.addStretch()
            card_layout.addLayout(donor_row)

            # Clean Info Row 2: Action / Preservation
            action_row = QHBoxLayout()
            action_row.setSpacing(6)
            tag_action = QLabel("Action:")
            tag_action.setStyleSheet("color: #64748b; font-size: 10px; font-weight: 600;")
            action_row.addWidget(tag_action)

            if key == "bios":
                act_str = "Clean binary replacement • Original DMI, Serial & Keys preserved"
            elif key == "me":
                act_str = "Clean factory ME injection • Automatically resets PMC, PCHC & Type-C IOM"
            elif key == "ec":
                act_str = "Clean Embedded Controller firmware injection"
            elif key == "gbe":
                act_str = "Clean Gigabit Ethernet firmware injection • Original MAC preserved"
            else:
                act_str = item.get("op_desc", "Clean firmware injection")

            val_action = QLabel(act_str)
            val_action.setStyleSheet("color: #94a3b8; font-size: 10px;")
            action_row.addWidget(val_action)
            action_row.addStretch()
            card_layout.addLayout(action_row)

            c_layout.addWidget(card)

        # Unmodified regions info card
        untouched_card = QFrame()
        untouched_card.setStyleSheet("""
            QFrame {
                background-color: #060b14;
                border: 1px dashed #1e293b;
                border-radius: 5px;
            }
        """)
        ut_layout = QHBoxLayout(untouched_card)
        ut_layout.setContentsMargins(10, 6, 10, 6)
        ut_lbl = QLabel("Descriptor & non-selected regions will remain 100% original from your backup dump.")
        ut_lbl.setStyleSheet("color: #64748b; font-size: 10px; font-style: italic;")
        ut_layout.addWidget(ut_lbl)
        c_layout.addWidget(untouched_card)

        c_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)

        # Action Buttons Layout
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.summary_lbl = QLabel(f"Ready: {match_count} of {match_count} region(s) selected.")
        self.summary_lbl.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: 500;")
        btn_layout.addWidget(self.summary_lbl)
        btn_layout.addStretch()

        cancel_btn = QPushButton("CANCEL")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setFixedHeight(32)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #0f172a;
                color: #94a3b8;
                border: 1px solid #334155;
                border-radius: 5px;
                font-size: 11px;
                font-weight: 700;
                padding: 0 18px;
            }
            QPushButton:hover {
                background-color: #1e293b;
                color: #f1f5f9;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        self.clean_btn = QPushButton("CLEAN")
        self.clean_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clean_btn.setFixedHeight(32)
        self.clean_btn.setStyleSheet("""
            QPushButton {
                background-color: #00f2ff;
                color: #010409;
                border: none;
                border-radius: 5px;
                font-size: 11px;
                font-weight: 800;
                letter-spacing: 1px;
                padding: 0 22px;
            }
            QPushButton:hover {
                background-color: #38f8ff;
            }
            QPushButton:disabled {
                background-color: #334155;
                color: #64748b;
            }
        """)
        self.clean_btn.clicked.connect(self._on_clean_click)
        btn_layout.addWidget(self.clean_btn)

        layout.addLayout(btn_layout)

    def _set_all_checked(self, checked: bool):
        for cb in self.checkboxes.values():
            cb.setChecked(checked)

    def _on_check_changed(self):
        sel_count = sum(1 for cb in self.checkboxes.values() if cb.isChecked())
        total = len(self.checkboxes)
        self.summary_lbl.setText(f"Ready: {sel_count} of {total} region(s) selected.")
        self.clean_btn.setEnabled(sel_count > 0)

    def get_selected_matches(self) -> dict:
        """Returns only the matches whose checkboxes are selected."""
        selected = {}
        for key, cb in self.checkboxes.items():
            if cb.isChecked() and key in self.matches:
                selected[key] = self.matches[key]
        return selected

    def _on_clean_click(self):
        sel = self.get_selected_matches()
        if not sel:
            return
        self.confirmed = True
        self.accept()
