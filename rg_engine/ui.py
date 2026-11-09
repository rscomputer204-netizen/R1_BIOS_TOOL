"""
R1 BIOS Tool — Simple Extracted File Selection Dialog
=====================================================
Clean, minimalist selection dialog with board matching and safety warnings.
No emojis, clutter-free professional interface.
"""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QHBoxLayout, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush, QFont
from rg_engine.board_matcher import rank_candidates, format_size


class ExtractedFileListDialog(QDialog):
    def __init__(self, extracted_files, original_bios_path=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select BIOS Candidate")
        self.setFixedSize(540, 420)
        self.setStyleSheet("background-color: #0f172a; color: #ffffff;")

        self.selected_file = None
        self.original_bios_path = original_bios_path

        # Rank candidates
        self.ranked_candidates, self.board_info = rank_candidates(extracted_files, original_bios_path)
        self.has_match = any(c["is_match"] for c in self.ranked_candidates)
        self.best_candidate = self.ranked_candidates[0] if self.has_match else None

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        # Title
        title = QLabel("Extracted Files Found")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #38bdf8;")
        layout.addWidget(title)

        # Subtitle
        primary_fam = self.board_info.get("primary_family")
        if self.has_match and primary_fam:
            desc_text = f"Select BIOS file to apply (Detected Board: {primary_fam}):"
        else:
            desc_text = "Please select the valid BIOS Region file from the list below:"

        desc = QLabel(desc_text)
        desc.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(desc)

        # List Widget
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 8px 10px;
                border-bottom: 1px solid #273549;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #0284c7;
                color: #ffffff;
            }
        """)
        self.list_widget.currentRowChanged.connect(self._on_selection_changed)

        recommended_row = 0
        for idx, c in enumerate(self.ranked_candidates):
            item = QListWidgetItem()
            if c["is_match"]:
                display_text = f"{c['filename']}   [{c['size_str']}]   [MATCHED: {c['matched_id']}]"
                item.setText(display_text)
                item.setForeground(QBrush(QColor("#38bdf8")))
                font = item.font()
                font.setBold(True)
                item.setFont(font)
                recommended_row = idx
            else:
                display_text = f"{c['filename']}   [{c['size_str']}]"
                item.setText(display_text)
                item.setForeground(QBrush(QColor("#cbd5e1")))

            self.list_widget.addItem(item)

        layout.addWidget(self.list_widget, 1)

        # Warning label (shows only when mismatched file is selected)
        self.lbl_warning = QLabel("")
        self.lbl_warning.setFixedHeight(22)
        self.lbl_warning.setStyleSheet("font-size: 11px;")
        layout.addWidget(self.lbl_warning)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_select = QPushButton("Select File")

        btn_style = "QPushButton { padding: 8px 18px; font-weight: bold; border-radius: 4px; } "
        self.btn_cancel.setStyleSheet(btn_style + "background-color: #334155; color: white;")
        self.btn_select.setStyleSheet(btn_style + "background-color: #0ea5e9; color: white;")

        self.btn_cancel.clicked.connect(self.reject)
        self.btn_select.clicked.connect(self.on_select)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_select)

        layout.addLayout(btn_layout)

        # Pre-select recommended file
        if self.ranked_candidates:
            self.list_widget.setCurrentRow(recommended_row)
            self._update_warning(recommended_row)

    def _on_selection_changed(self, row: int):
        if 0 <= row < len(self.ranked_candidates):
            self._update_warning(row)

    def _update_warning(self, row: int):
        cand = self.ranked_candidates[row]
        primary_fam = self.board_info.get("primary_family")

        if cand["is_match"]:
            self.lbl_warning.setText(f"<font color='#38bdf8'>Status: Matches detected motherboard board ({cand['matched_id']})</font>")
        elif primary_fam:
            self.lbl_warning.setText(f"<font color='#f87171'>Warning: Selected file does not match detected board ({primary_fam})</font>")
        else:
            self.lbl_warning.setText("")

    def on_select(self):
        row = self.list_widget.currentRow()
        if row < 0 or row >= len(self.ranked_candidates):
            QMessageBox.warning(self, "Selection Required", "Please select a file from the list.")
            return

        selected_candidate = self.ranked_candidates[row]

        # Safety Check if user selected mismatched file
        if not selected_candidate["is_match"] and self.has_match and self.best_candidate:
            primary_fam = self.board_info.get("primary_family", "Target")
            rec_name = self.best_candidate["filename"]

            reply = QMessageBox.question(
                self,
                "Board Mismatch Warning",
                f"The selected file ({selected_candidate['filename']}) does not match your motherboard ({primary_fam}).\n\n"
                f"Recommended match is: {rec_name}\n\n"
                f"Flashing the wrong board revision may cause display issues.\n"
                f"Do you want to proceed anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.No:
                # Switch to recommended file
                self.selected_file = self.best_candidate["path"]
                self.accept()
                return

        self.selected_file = selected_candidate["path"]
        self.accept()
