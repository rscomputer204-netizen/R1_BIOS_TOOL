"""
R1 EC Finder - Standalone GUI
==============================
Standalone test application for carving and extracting Embedded Controller (EC / KBC)
firmware from BIOS dumps and manufacturer update files.

Can be run independently:
    python R1_EC_Finder/standalone_gui.py
"""

import os
import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QMessageBox, QFrame, QComboBox, QTextEdit, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QCursor

# Ensure parent directory is in python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from R1_EC_Finder.carver_engine import ECCarverEngine, ECCandidate


CYBER_STYLE = """
QMainWindow, QWidget#CentralWidget {
    background-color: #0b1017;
    color: #e2e8f0;
    font-family: 'Segoe UI', sans-serif;
}
QFrame#Card {
    background-color: #0e1520;
    border: 1px solid #1a2536;
    border-radius: 8px;
}
QFrame#DropBox {
    background-color: #0a0f18;
    border: 2px dashed #00adb5;
    border-radius: 10px;
    min-height: 85px;
}
QFrame#DropBox:hover {
    border-color: #00f3ff;
    background-color: #0d1624;
}
QTableWidget {
    background-color: #0c1421;
    color: #f1f5f9;
    border: 1px solid #1e293b;
    border-radius: 6px;
    gridline-color: #1a2434;
    selection-background-color: #0284c7;
    selection-color: #ffffff;
    font-size: 11px;
}
QTableWidget::item {
    padding: 6px 10px;
}
QHeaderView::section {
    background-color: #0f1a2a;
    color: #38bdf8;
    font-weight: bold;
    font-size: 11px;
    padding: 6px 10px;
    border: 1px solid #1e293b;
}
QPushButton {
    background-color: #1e293b;
    color: #cbd5e1;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 7px 18px;
    font-weight: bold;
    font-size: 11px;
}
QPushButton:hover {
    background-color: #334155;
    color: #ffffff;
}
QPushButton#PrimaryBtn {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #38bdf8, stop:0.5 #0ea5e9, stop:1 #0284c7);
    color: #041018;
    border: 1px solid #7dd3fc;
    border-radius: 6px;
    font-weight: 900;
    font-size: 12px;
    padding: 9px 24px;
    letter-spacing: 1px;
}
QPushButton#PrimaryBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #7dd3fc, stop:0.5 #38bdf8, stop:1 #0ea5e9);
    color: #000000;
}
QPushButton#PrimaryBtn:disabled {
    background: #161e2e;
    color: #475569;
    border: 1px solid #1e293b;
}
QComboBox {
    background-color: #161e2e;
    color: #f1f5f9;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 5px 12px;
    font-size: 11px;
}
QComboBox::drop-down { border: none; }
QComboBox QAbstractItemView {
    background-color: #161e2e;
    color: #f1f5f9;
    selection-background-color: #0284c7;
}
QTextEdit {
    background-color: #070a0f;
    color: #00ff88;
    border: 1px solid #1a2536;
    border-radius: 6px;
    font-family: 'Consolas', monospace;
    font-size: 10px;
}
"""


class StandaloneECFinderWindow(QMainWindow):
    """Standalone tester application for R1 EC Finder."""

    def __init__(self, initial_file=None):
        super().__init__()
        self.setWindowTitle("R1 EC Finder — Embedded Controller Firmware Carver (Standalone Engine)")
        self.resize(880, 680)
        self.setStyleSheet(CYBER_STYLE)

        self.current_data: bytes = b""
        self.current_filepath: str = ""
        self.candidates: list[ECCandidate] = []

        self._setup_ui()

        if initial_file and os.path.exists(initial_file):
            self.load_file(initial_file)

    def _setup_ui(self):
        central = QWidget()
        central.setObjectName("CentralWidget")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(10)

        # ── Header Bar ───────────────────────────────────────────────
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        lbl_title = QLabel("R1 EC FINDER — EMBEDDED CONTROLLER CARVER")
        lbl_title.setStyleSheet("color: #00f3ff; font-size: 16px; font-weight: 900; letter-spacing: 1.5px;")
        lbl_sub = QLabel("Advanced multi-architecture scanner for ITE, ENE, Nuvoton, and Microchip EC firmware blocks")
        lbl_sub.setStyleSheet("color: #64748b; font-size: 11px;")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        header_layout.addLayout(title_box)
        header_layout.addStretch()

        self.lbl_badge = QLabel("Engine: Standalone v1.0")
        self.lbl_badge.setStyleSheet("color: #22c55e; background: #0c2018; border: 1px solid #16a34a; padding: 4px 10px; border-radius: 4px; font-size: 10px; font-weight: bold;")
        header_layout.addWidget(self.lbl_badge)
        root.addLayout(header_layout)

        # Divider
        div1 = QFrame()
        div1.setFixedHeight(1)
        div1.setStyleSheet("background: #1e293b;")
        root.addWidget(div1)

        # ── Drop Zone ────────────────────────────────────────────────
        self.drop_box = QFrame()
        self.drop_box.setObjectName("DropBox")
        self.drop_box.setCursor(Qt.CursorShape.PointingHandCursor)
        self.drop_box.setAcceptDrops(True)
        self.drop_box.mousePressEvent = lambda e: self.browse_file() if e.button() == Qt.MouseButton.LeftButton else None
        self.drop_box.dragEnterEvent = self._drag_enter
        self.drop_box.dropEvent = self._drop_event

        drop_lay = QVBoxLayout(self.drop_box)
        drop_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_lay.setSpacing(4)
        self.lbl_drop_title = QLabel("DROP BIOS DUMP OR UPDATE FILE HERE")
        self.lbl_drop_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_drop_title.setStyleSheet("color: #38bdf8; font-size: 13px; font-weight: bold; letter-spacing: 1px;")
        self.lbl_drop_sub = QLabel("or click anywhere inside this box to browse (*.bin, *.rom, *.fd, *.exe)")
        self.lbl_drop_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_drop_sub.setStyleSheet("color: #64748b; font-size: 10px;")
        drop_lay.addWidget(self.lbl_drop_title)
        drop_lay.addWidget(self.lbl_drop_sub)
        root.addWidget(self.drop_box)

        # ── Filters & Controls Bar ───────────────────────────────────
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(10)

        lbl_filter_sz = QLabel("Filter Size:")
        lbl_filter_sz.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: bold;")
        self.combo_size = QComboBox()
        self.combo_size.addItems(["All Sizes", "128 KB", "160 KB", "192 KB", "256 KB", "320 KB", "512 KB", "1024 KB"])
        self.combo_size.currentTextChanged.connect(self._apply_filters)

        lbl_filter_arch = QLabel("Architecture:")
        lbl_filter_arch.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: bold;")
        self.combo_arch = QComboBox()
        self.combo_arch.addItems(["All Architectures", "8051 (ITE / ENE)", "ARM Cortex-M (Nuvoton / MEC)", "Intel Descriptor Region"])
        self.combo_arch.currentTextChanged.connect(self._apply_filters)

        self.lbl_count = QLabel("Candidates: 0")
        self.lbl_count.setStyleSheet("color: #00f3ff; font-weight: bold; font-size: 11px;")

        filter_bar.addWidget(lbl_filter_sz)
        filter_bar.addWidget(self.combo_size)
        filter_bar.addWidget(lbl_filter_arch)
        filter_bar.addWidget(self.combo_arch)
        filter_bar.addStretch()
        filter_bar.addWidget(self.lbl_count)
        root.addLayout(filter_bar)

        # ── Table of Discovered EC Candidates ────────────────────────
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Confidence", "Chip Family / Architecture", "Offset (Hex)", "Size", "Entropy", "Detection Method"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.itemSelectionChanged.connect(self._on_candidate_selected)
        root.addWidget(self.table, stretch=2)

        # ── Preview Box ──────────────────────────────────────────────
        preview_box = QVBoxLayout()
        preview_box.setSpacing(4)
        lbl_prev_title = QLabel("CARVED CANDIDATE PREVIEW (FIRST 128 BYTES HEX DUMP)")
        lbl_prev_title.setStyleSheet("color: #64748b; font-size: 10px; font-weight: bold;")
        self.txt_preview = QTextEdit()
        self.txt_preview.setReadOnly(True)
        self.txt_preview.setFixedHeight(75)
        self.txt_preview.setPlaceholderText("Select any candidate in the table above to view raw binary inspection...")
        preview_box.addWidget(lbl_prev_title)
        preview_box.addWidget(self.txt_preview)
        root.addLayout(preview_box)

        # ── Bottom Action Row ─────────────────────────────────────────
        bottom_row = QHBoxLayout()
        self.lbl_status = QLabel("Ready. Please drop or open a BIOS file to begin.")
        self.lbl_status.setStyleSheet("color: #94a3b8; font-size: 11px;")

        self.btn_export = QPushButton("SAVE EXTRACTED EC (.BIN)")
        self.btn_export.setObjectName("PrimaryBtn")
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self.save_selected_ec)

        bottom_row.addWidget(self.lbl_status)
        bottom_row.addStretch()
        bottom_row.addWidget(self.btn_export)
        root.addLayout(bottom_row)

    # ── Drag and Drop Handlers ────────────────────────────────────────
    def _drag_enter(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def _drop_event(self, event):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if os.path.isfile(path):
                self.load_file(path)

    def browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open BIOS Image", "",
            "BIOS & Firmware Files (*.bin *.rom *.fd *.cap *.exe);;All Files (*)"
        )
        if path:
            self.load_file(path)

    # ── File Loading & Scanning ───────────────────────────────────────
    def load_file(self, filepath: str):
        if not os.path.isfile(filepath):
            return
        self.current_filepath = filepath
        name = os.path.basename(filepath)
        size_mb = os.path.getsize(filepath) / (1024 * 1024)

        self.lbl_drop_title.setText(f"LOADED: {name} ({size_mb:.2f} MB)")
        self.lbl_drop_sub.setText("Click or drop another file to replace")
        self.lbl_status.setText(f"Scanning '{name}' for Embedded Controller firmware...")
        QApplication.processEvents()

        with open(filepath, "rb") as f:
            self.current_data = f.read()

        engine = ECCarverEngine(self.current_data)
        self.candidates = engine.scan()
        self._apply_filters()

        self.lbl_status.setText(f"Scan complete. Discovered {len(self.candidates)} EC firmware candidate(s).")

    def _apply_filters(self):
        sz_filter = self.combo_size.currentText()
        arch_filter = self.combo_arch.currentText()

        filtered = []
        for c in self.candidates:
            # Size filter
            if sz_filter != "All Sizes":
                req_kb = int(sz_filter.split()[0])
                if (c.size // 1024) != req_kb:
                    continue
            # Architecture filter
            if arch_filter == "8051 (ITE / ENE)" and "8051" not in c.chip_family:
                continue
            if arch_filter == "ARM Cortex-M (Nuvoton / MEC)" and "Cortex-M" not in c.chip_family:
                continue
            if arch_filter == "Intel Descriptor Region" and "Intel" not in c.chip_family:
                continue

            filtered.append(c)

        self.table.setRowCount(len(filtered))
        for row, c in enumerate(filtered):
            # Confidence badge
            conf_item = QTableWidgetItem(f"{c.confidence}%")
            conf_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if c.confidence >= 90:
                conf_item.setForeground(QColor("#22c55e"))
            elif c.confidence >= 80:
                conf_item.setForeground(QColor("#00f3ff"))
            else:
                conf_item.setForeground(QColor("#f59e0b"))

            # Chip family
            arch_item = QTableWidgetItem(c.chip_family)
            # Offset
            off_item = QTableWidgetItem(f"0x{c.offset:08X}")
            off_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            # Size
            sz_str = f"{c.size // 1024} KB" if c.size < 1048576 else f"{c.size / (1024*1024):.2f} MB"
            sz_item = QTableWidgetItem(sz_str)
            sz_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            # Entropy
            ent_item = QTableWidgetItem(f"{c.entropy:.2f}")
            ent_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            # Method
            meth_item = QTableWidgetItem(c.detection_method)

            # Store object reference in row 0
            conf_item.setData(Qt.ItemDataRole.UserRole, c)

            self.table.setItem(row, 0, conf_item)
            self.table.setItem(row, 1, arch_item)
            self.table.setItem(row, 2, off_item)
            self.table.setItem(row, 3, sz_item)
            self.table.setItem(row, 4, ent_item)
            self.table.setItem(row, 5, meth_item)

        self.lbl_count.setText(f"Candidates: {len(filtered)}")
        if len(filtered) > 0:
            self.table.selectRow(0)
        else:
            self.txt_preview.clear()
            self.btn_export.setEnabled(False)

    def _on_candidate_selected(self):
        rows = self.table.selectedItems()
        if not rows:
            self.btn_export.setEnabled(False)
            return

        c: ECCandidate = self.table.item(self.table.currentRow(), 0).data(Qt.ItemDataRole.UserRole)
        if not c:
            return

        self.btn_export.setEnabled(True)
        # Generate hex dump preview
        sample = self.current_data[c.offset : c.offset + min(c.size, 128)]
        hex_lines = []
        for i in range(0, len(sample), 16):
            chunk = sample[i : i + 16]
            hex_part = " ".join(f"{b:02X}" for b in chunk)
            ascii_part = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
            hex_lines.append(f"0x{c.offset + i:08X}:  {hex_part:<48}  |{ascii_part}|")

        self.txt_preview.setText("\n".join(hex_lines))

    def save_selected_ec(self):
        rows = self.table.selectedItems()
        if not rows:
            return
        c: ECCandidate = self.table.item(self.table.currentRow(), 0).data(Qt.ItemDataRole.UserRole)
        if not c:
            return

        orig_base = os.path.splitext(os.path.basename(self.current_filepath))[0] if self.current_filepath else "BIOS"
        sz_tag = f"{c.size // 1024}KB"
        default_name = f"{orig_base}_CARVED_EC_{sz_tag}.bin"

        dest_path, _ = QFileDialog.getSaveFileName(
            self, "Save Carved EC Firmware", default_name,
            "Binary Files (*.bin);;ROM Files (*.rom);;All Files (*)"
        )
        if not dest_path:
            return

        carved_bytes = self.current_data[c.offset : c.offset + c.size]
        with open(dest_path, "wb") as f:
            f.write(carved_bytes)

        QMessageBox.information(
            self, "EC Carve Successful",
            f"Successfully carved and saved EC firmware!\n\n"
            f"File: {os.path.basename(dest_path)}\n"
            f"Size: {len(carved_bytes) // 1024} KB ({len(carved_bytes)} bytes)\n"
            f"Source Offset: 0x{c.offset:08X}"
        )


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    initial = sys.argv[1] if len(sys.argv) > 1 else None
    win = StandaloneECFinderWindow(initial_file=initial)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

