"""
all_rg_clean_dialog.py
======================
User-friendly, informative region replacement dialog for ALL RG CLEAN.
Clearly presents target regions in the backup dump, official donor files,
and surgical operations with per-region selection checkboxes.
"""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QWidget, QCheckBox, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QCursor


class AllRgCleanDialog(QDialog):
    def __init__(self, matches: dict, parent=None):
        super().__init__(parent)
        self.matches = matches
        self.confirmed = False
        self.checkboxes = {}

        self.setWindowTitle("ALL RG CLEAN - REGION REPLACEMENT")
        self.setFixedSize(560, 460)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self.setStyleSheet("""
            QDialog {
                background-color: #0b1120;
                border: 1px solid #1e293b;
                border-radius: 8px;
            }
            QLabel {
                font-family: 'Segoe UI', sans-serif;
            }
            QCheckBox {
                color: #f1f5f9;
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
                font-weight: bold;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #38bdf8;
                border-radius: 3px;
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
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(8)

        # Header Title
        title_lbl = QLabel("ALL RG CLEAN")
        title_lbl.setStyleSheet("color: #00f2ff; font-size: 15px; font-weight: 900; letter-spacing: 1.5px;")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_lbl)

        # Subtitle
        match_count = len(self.matches)
        sub_lbl = QLabel(f"Detected {match_count} component(s) ready for surgical clean & replacement:")
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
        btn_select_all.setStyleSheet("QPushButton { background: transparent; color: #38bdf8; font-size: 10px; border: none; } QPushButton:hover { text-decoration: underline; }")
        btn_select_all.clicked.connect(lambda: self._set_all_checked(True))
        top_bar.addWidget(btn_select_all)

        lbl_slash = QLabel("|")
        lbl_slash.setStyleSheet("color: #334155; font-size: 10px;")
        top_bar.addWidget(lbl_slash)

        btn_desel_all = QPushButton("Deselect All")
        btn_desel_all.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_desel_all.setStyleSheet("QPushButton { background: transparent; color: #94a3b8; font-size: 10px; border: none; } QPushButton:hover { text-decoration: underline; }")
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
            }
            QScrollBar::handle:vertical {
                background: #334155;
                border-radius: 3px;
            }
        """)

        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(2, 2, 2, 2)
        c_layout.setSpacing(8)

        op_desc_map = {
            "bios": "Surgical binary replacement from official update (DMI data preserved)",
            "me": "Clean factory MFS partition injection (Resets PMC, PCHC, IOM) -> Configured State",
            "ec": "Official Embedded Controller binary replacement into dump EC region",
            "gbe": "Official Gigabit Ethernet binary replacement into dump GbE region"
        }

        for key, item in self.matches.items():
            card = QFrame()
            card.setStyleSheet("""
                QFrame {
                    background-color: #0f172a;
                    border: 1px solid #1e293b;
                    border-left: 3px solid #00f2ff;
                    border-radius: 6px;
                }
            """)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(10, 8, 10, 8)
            card_layout.setSpacing(4)

            # Row 1: Checkbox + Action Badge
            header_row = QHBoxLayout()
            cb = QCheckBox(item.get("title", key.upper()))
            cb.setChecked(True)
            cb.stateChanged.connect(self._on_check_changed)
            self.checkboxes[key] = cb
            header_row.addWidget(cb)
            header_row.addStretch()

            if key == "me":
                badge = QLabel("FACTORY RESET")
                badge.setStyleSheet("""
                    background-color: #083344;
                    color: #22d3ee;
                    border: 1px solid #0891b2;
                    border-radius: 3px;
                    font-size: 9px;
                    font-weight: 800;
                    padding: 2px 6px;
                    letter-spacing: 0.5px;
                """)
            else:
                badge = QLabel("WILL REPLACE")
                badge.setStyleSheet("""
                    background-color: #064e3b;
                    color: #34d399;
                    border: 1px solid #059669;
                    border-radius: 3px;
                    font-size: 9px;
                    font-weight: 800;
                    padding: 2px 6px;
                    letter-spacing: 0.5px;
                """)
            header_row.addWidget(badge)
            card_layout.addLayout(header_row)

            # Row 2: Target in Backup BIOS
            target_row = QHBoxLayout()
            target_lbl = QLabel("Target in Backup:")
            target_lbl.setFixedWidth(105)
            target_lbl.setStyleSheet("color: #64748b; font-size: 10px; font-weight: bold;")
            target_row.addWidget(target_lbl)

            target_val = QLabel(item.get("target_desc", "Region Match"))
            target_val.setStyleSheet("color: #f1f5f9; font-size: 10px;")
            target_row.addWidget(target_val)
            target_row.addStretch()
            card_layout.addLayout(target_row)

            # Row 3: Official Donor File
            donor_row = QHBoxLayout()
            donor_lbl = QLabel("Official Donor File:")
            donor_lbl.setFixedWidth(105)
            donor_lbl.setStyleSheet("color: #64748b; font-size: 10px; font-weight: bold;")
            donor_row.addWidget(donor_lbl)

            fname = item.get("filename", "")
            donor_val = QLabel(fname)
            donor_val.setToolTip(item.get("file", fname))
            donor_val.setStyleSheet("color: #38bdf8; font-size: 10px; font-family: 'Consolas', monospace;")
            donor_val.setWordWrap(True)
            donor_row.addWidget(donor_val)
            card_layout.addLayout(donor_row)

            # Row 4: Operation Explanation
            op_row = QHBoxLayout()
            op_lbl = QLabel("Operation:")
            op_lbl.setFixedWidth(105)
            op_lbl.setStyleSheet("color: #64748b; font-size: 10px; font-weight: bold;")
            op_row.addWidget(op_lbl)

            op_text = item.get("op_desc") or op_desc_map.get(key, "Surgical clean replacement")
            op_val = QLabel(op_text)
            op_val.setStyleSheet("color: #94a3b8; font-size: 9px; font-style: italic;")
            op_row.addWidget(op_val)
            op_row.addStretch()
            card_layout.addLayout(op_row)

            c_layout.addWidget(card)

        # Unmodified regions info card
        untouched_card = QFrame()
        untouched_card.setStyleSheet("""
            QFrame {
                background-color: #0b1329;
                border: 1px dashed #334155;
                border-radius: 4px;
                padding: 4px;
            }
        """)
        ut_layout = QHBoxLayout(untouched_card)
        ut_layout.setContentsMargins(8, 4, 8, 4)
        ut_lbl = QLabel("Descriptor & non-selected regions will remain 100% original from your backup dump.")
        ut_lbl.setStyleSheet("color: #64748b; font-size: 9px; font-style: italic;")
        ut_layout.addWidget(ut_lbl)
        c_layout.addWidget(untouched_card)

        c_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)

        # Action Buttons Layout
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.summary_lbl = QLabel(f"Ready: {match_count} of {match_count} region(s) selected.")
        self.summary_lbl.setStyleSheet("color: #94a3b8; font-size: 10px;")
        btn_layout.addWidget(self.summary_lbl)
        btn_layout.addStretch()

        cancel_btn = QPushButton("CANCEL")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setFixedHeight(30)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #0f172a;
                color: #94a3b8;
                border: 1px solid #334155;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 700;
                padding: 0 16px;
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
        self.clean_btn.setFixedHeight(30)
        self.clean_btn.setStyleSheet("""
            QPushButton {
                background-color: #00f2ff;
                color: #010409;
                border: none;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 800;
                letter-spacing: 1px;
                padding: 0 20px;
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
