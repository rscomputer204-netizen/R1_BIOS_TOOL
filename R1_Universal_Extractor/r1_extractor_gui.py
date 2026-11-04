"""
R1_Universal_Extractor: r1_extractor_gui.py
============================================
Professional Cyber Blue GUI for R1 Universal Extractor.
Integrated with R1 BIOS TOOL theme.
"""

import os
import sys
import threading
import subprocess
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QProgressBar,
    QFileDialog, QListWidget, QListWidgetItem, QFrame, QSplitter,
    QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QCursor

# Ensure local core can be imported
sys.path.insert(0, os.path.dirname(__file__))
from r1_extractor_core import R1ExtractorCore


class DropZoneWidget(QFrame):
    """Glossy Drag-and-Drop file zone widget matching R1 BIOS TOOL design."""
    file_dropped = Signal(str)
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFixedHeight(120)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._set_idle_style()

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.icon_label = QLabel("📂", self)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setStyleSheet("font-size: 26px; background: transparent;")

        self.title_label = QLabel("DROP BIOS INSTALLER OR FIRMWARE PACKAGE HERE", self)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("color: #00f3ff; font-weight: 800; font-family: 'Segoe UI', sans-serif; font-size: 13px; letter-spacing: 1px; background: transparent;")

        self.sub_label = QLabel("Click to browse or drag file (.exe, .bin, .rom, .fd, .cap, .zip, .7z, .cab, .msi, .pkg)", self)
        self.sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sub_label.setStyleSheet("color: #7dd3fc; font-size: 11px; background: transparent;")

        layout.addWidget(self.icon_label)
        layout.addWidget(self.title_label)
        layout.addWidget(self.sub_label)

    def _set_idle_style(self):
        self.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0f1722, stop:1 #090e15);
                border: 2px dashed #0284c7;
                border-radius: 8px;
            }
        """)

    def _set_hover_style(self):
        self.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #132235, stop:1 #0c1622);
                border: 2px dashed #00f3ff;
                border-radius: 8px;
            }
        """)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._set_hover_style()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self._set_idle_style()

    def dropEvent(self, event):
        self._set_idle_style()
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if path:
                self.file_dropped.emit(path)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()


class R1ExtractorWindow(QMainWindow):
    """Main professional window for R1 Universal Extractor."""

    log_signal = Signal(str)
    progress_signal = Signal(int)
    extraction_finished = Signal(dict)
    bios_selected = Signal(str)

    def __init__(self, target_file: str = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("R1 UNIVERSAL BIOS EXTRACTOR - [5-TIER FIRMWARE ENGINE]")
        self.resize(960, 650)
        self.setMinimumSize(850, 550)

        self._target_file = ""
        self._output_dir = ""

        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #0b0f15;
                color: #e2e8f0;
                font-family: 'Segoe UI', Consolas, sans-serif;
            }
            QLabel {
                color: #94a3b8;
                font-size: 12px;
            }
            QLineEdit {
                background: #111722;
                border: 1px solid #1e293b;
                border-radius: 5px;
                color: #00f3ff;
                padding: 7px 12px;
                font-family: 'Consolas', monospace;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #00f3ff;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0052cc, stop:1 #00a2ff);
                color: #ffffff;
                font-weight: bold;
                border: none;
                border-radius: 5px;
                padding: 8px 18px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0066ff, stop:1 #00f3ff);
                color: #ffffff;
            }
            QPushButton:disabled {
                background: #1a2332;
                color: #475569;
            }
            QPushButton#ActionBtn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:1 #00f3ff);
                color: #05131e;
                font-size: 13px;
                font-weight: 800;
                padding: 10px 22px;
                border-radius: 6px;
                letter-spacing: 0.5px;
            }
            QPushButton#ActionBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0369a1, stop:1 #38bdf8);
                color: #ffffff;
            }
            QPushButton#SecondaryBtn {
                background: #111824;
                border: 1px solid #0284c7;
                color: #38bdf8;
                font-size: 12px;
                font-weight: 600;
                padding: 8px 16px;
                border-radius: 5px;
            }
            QPushButton#SecondaryBtn:hover {
                background: #162235;
                border: 1px solid #00f3ff;
                color: #ffffff;
            }
            QTextEdit {
                background-color: #070a0f;
                border: 1px solid #16202c;
                border-radius: 6px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
                color: #7dd3fc;
                padding: 8px;
            }
            QProgressBar {
                border: 1px solid #16202c;
                border-radius: 4px;
                text-align: center;
                color: #ffffff;
                background-color: #0e1520;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0052cc, stop:1 #00f3ff);
                border-radius: 3px;
            }
            QListWidget {
                background-color: #0c121a;
                border: 1px solid #16202c;
                border-radius: 6px;
                color: #ffffff;
                font-family: 'Consolas', monospace;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 9px;
                border-bottom: 1px solid #141c28;
            }
            QListWidget::item:selected {
                background-color: #16324d;
                border: 1px solid #00f3ff;
                color: #ffffff;
            }
        """)

        self._init_ui()
        self.log_signal.connect(self._append_log)
        self.progress_signal.connect(self.progress_bar.setValue)
        self.extraction_finished.connect(self._on_extract_complete)

        if target_file and os.path.isfile(target_file):
            self.set_input_file(target_file)

    def _init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(10)

        # 1. Header Bar
        hdr_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("R1 UNIVERSAL BIOS EXTRACTOR", self)
        title.setStyleSheet("font-size: 17px; font-weight: 900; color: #00f3ff; letter-spacing: 1.5px;")
        subtitle = QLabel("Native 5-Tier Firmware Unpacker • Auto-Path Resolution • SPI Carver", self)
        subtitle.setStyleSheet("font-size: 11px; color: #64748b; font-weight: 500;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        hdr_layout.addLayout(title_box)
        hdr_layout.addStretch()

        engine_chip = QLabel("ENGINE: 100% NATIVE IN-HOUSE", self)
        engine_chip.setStyleSheet("background: #0d1e30; color: #38bdf8; border: 1px solid #0284c7; border-radius: 4px; padding: 5px 10px; font-size: 11px; font-weight: 700; font-family: Consolas;")
        hdr_layout.addWidget(engine_chip)
        main_layout.addLayout(hdr_layout)

        # 2. Interactive Drag & Drop Zone (Click to Browse)
        self.drop_zone = DropZoneWidget(self)
        self.drop_zone.file_dropped.connect(self.set_input_file)
        self.drop_zone.clicked.connect(self._browse_input)
        main_layout.addWidget(self.drop_zone)

        # 3. File Info & Auto-Destination Indicator Strip
        info_frame = QFrame(self)
        info_frame.setStyleSheet("""
            QFrame {
                background: #0e1622;
                border: 1px solid #1a2536;
                border-radius: 6px;
                padding: 6px;
            }
        """)
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(8, 6, 8, 6)
        info_layout.setSpacing(6)

        # Target file row
        t_row = QHBoxLayout()
        t_lbl = QLabel("SELECTED FILE:", self)
        t_lbl.setFixedWidth(110)
        t_lbl.setStyleSheet("color: #94a3b8; font-weight: 700; font-size: 11px;")
        self.in_edit = QLineEdit(self)
        self.in_edit.setPlaceholderText("No file selected. Drop an installer above or click Browse...")
        self.in_edit.setReadOnly(True)
        btn_in_browse = QPushButton("BROWSE", self)
        btn_in_browse.clicked.connect(self._browse_input)
        t_row.addWidget(t_lbl)
        t_row.addWidget(self.in_edit)
        t_row.addWidget(btn_in_browse)
        info_layout.addLayout(t_row)

        # Auto-Destination Row (Display only, no manual target input needed)
        dest_row = QHBoxLayout()
        d_lbl = QLabel("AUTO DESTINATION:", self)
        d_lbl.setFixedWidth(110)
        d_lbl.setStyleSheet("color: #38bdf8; font-weight: 700; font-size: 11px;")
        self.dest_display = QLabel("Output folder will be created automatically alongside the source file", self)
        self.dest_display.setStyleSheet("color: #64748b; font-family: 'Consolas', monospace; font-size: 11px;")
        dest_row.addWidget(d_lbl)
        dest_row.addWidget(self.dest_display, 1)
        info_layout.addLayout(dest_row)

        main_layout.addWidget(info_frame)

        # 4. Action Row (Start Extraction & Open Output Folder)
        action_row = QHBoxLayout()
        self.btn_extract = QPushButton("⚡ START UNIVERSAL EXTRACTION", self)
        self.btn_extract.setObjectName("ActionBtn")
        self.btn_extract.setEnabled(False)
        self.btn_extract.clicked.connect(self.start_extraction)

        self.btn_open_out = QPushButton("📁 OPEN OUTPUT FOLDER", self)
        self.btn_open_out.setObjectName("SecondaryBtn")
        self.btn_open_out.setEnabled(False)
        self.btn_open_out.clicked.connect(self._open_output_dir)

        action_row.addWidget(self.btn_extract, 2)
        action_row.addWidget(self.btn_open_out, 1)
        main_layout.addLayout(action_row)

        # 5. Progress Bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        main_layout.addWidget(self.progress_bar)

        # 6. Splitter: Live Terminal (Left) vs Detected Firmware Candidates (Right)
        splitter = QSplitter(Qt.Orientation.Horizontal, self)

        # Left Panel: Live Terminal Log
        term_box = QWidget(self)
        term_layout = QVBoxLayout(term_box)
        term_layout.setContentsMargins(0, 0, 0, 0)
        term_lbl = QLabel("LIVE EXTRACTION LOG:", self)
        term_lbl.setStyleSheet("color: #38bdf8; font-weight: 700; font-size: 11px; letter-spacing: 0.5px;")
        self.terminal = QTextEdit(self)
        self.terminal.setReadOnly(True)
        term_layout.addWidget(term_lbl)
        term_layout.addWidget(self.terminal)
        splitter.addWidget(term_box)

        # Right Panel: Classified BIOS Candidates
        res_box = QWidget(self)
        res_layout = QVBoxLayout(res_box)
        res_layout.setContentsMargins(0, 0, 0, 0)
        res_lbl = QLabel("DETECTED FIRMWARE CANDIDATES:", self)
        res_lbl.setStyleSheet("color: #00f3ff; font-weight: 700; font-size: 11px; letter-spacing: 0.5px;")
        self.file_list = QListWidget(self)
        self.file_list.doubleClicked.connect(self._on_item_double_clicked)
        res_layout.addWidget(res_lbl)
        res_layout.addWidget(self.file_list)

        # Candidate Action Buttons
        cand_btn_box = QHBoxLayout()
        self.btn_load_in_tool = QPushButton("⚡ LOAD INTO R1 TOOL", self)
        self.btn_load_in_tool.setObjectName("ActionBtn")
        self.btn_load_in_tool.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0052cc, stop:1 #00b4d8);
                color: #ffffff;
                font-weight: 800;
                border-radius: 5px;
                padding: 8px 14px;
                font-size: 11px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0066ff, stop:1 #00f3ff);
            }
        """)
        self.btn_load_in_tool.clicked.connect(self._load_selected_candidate)

        self.btn_reveal = QPushButton("🔍 SHOW IN FOLDER", self)
        self.btn_reveal.setObjectName("SecondaryBtn")
        self.btn_reveal.clicked.connect(self._reveal_selected_candidate)

        cand_btn_box.addWidget(self.btn_load_in_tool)
        cand_btn_box.addWidget(self.btn_reveal)
        res_layout.addLayout(cand_btn_box)

        splitter.addWidget(res_box)
        splitter.setSizes([550, 410])
        main_layout.addWidget(splitter, 2)

        central_widget = QWidget(self)
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def set_input_file(self, path: str):
        if not path or not os.path.isfile(path):
            return

        self._target_file = path
        base = os.path.basename(path)
        stem = os.path.splitext(base)[0]
        parent_dir = os.path.dirname(os.path.abspath(path))

        # Automatic destination: created right alongside the file location
        self._output_dir = os.path.join(parent_dir, f"{stem}_extracted")

        self.in_edit.setText(path)
        self.dest_display.setText(self._output_dir)
        self.dest_display.setStyleSheet("color: #38bdf8; font-family: 'Consolas', monospace; font-size: 11px; font-weight: bold;")
        self.btn_extract.setEnabled(True)

        try:
            sz_mb = os.path.getsize(path) / (1024 * 1024)
            self.log(f"[SELECTED] Target: {base} ({sz_mb:.2f} MB)")
            self.log(f"[AUTO DESTINATION] Output will be saved to: {self._output_dir}")
        except OSError:
            self.log(f"[SELECTED] Target: {base}")

    def _browse_input(self):
        f, _ = QFileDialog.getOpenFileName(
            self, "Select BIOS Installer or Firmware File", "",
            "BIOS & Installer Files (*.exe *.bin *.rom *.fd *.cap *.zip *.7z *.cab *.msi *.pkg);;All Files (*.*)"
        )
        if f:
            self.set_input_file(f)

    def log(self, text: str):
        self.log_signal.emit(text)

    def _append_log(self, text: str):
        """Color-codes terminal messages in Cyber Blue palette (no neon green)."""
        color = "#7dd3fc"
        if "[SUCCESS]" in text or "★" in text:
            color = "#00f3ff"  # Vibrant Cyber Cyan
        elif "[ERROR]" in text or "[ERR]" in text:
            color = "#f43f5e"  # Crimson
        elif "[START]" in text or "[TARGET]" in text or "[SUMMARY]" in text:
            color = "#38bdf8"  # Electric Blue
        elif "[CARVER]" in text:
            color = "#fbbf24"  # Amber Gold
        elif "[VENDOR]" in text:
            color = "#a78bfa"  # Soft Violet
        elif "[NESTED" in text:
            color = "#67e8f9"  # Light Aqua

        html_msg = f"<span style='color: {color};'>{text}</span>"
        self.terminal.append(html_msg)
        self.terminal.verticalScrollBar().setValue(self.terminal.verticalScrollBar().maximum())

    def start_extraction(self):
        target = self._target_file
        out_dir = self._output_dir

        if not target or not os.path.isfile(target):
            self.log("[ERROR] Please select or drop a valid target file first.")
            return

        self.btn_extract.setEnabled(False)
        self.btn_open_out.setEnabled(False)
        self.file_list.clear()
        self.progress_bar.setValue(10)

        def worker():
            self.progress_signal.emit(25)
            summary = R1ExtractorCore.extract(target, out_dir, logger=self.log)
            self.progress_signal.emit(100)
            self.extraction_finished.emit(summary)

        threading.Thread(target=worker, daemon=True).start()

    def _on_extract_complete(self, summary: dict):
        self.btn_extract.setEnabled(True)
        self.btn_open_out.setEnabled(True)

        classified = summary.get("classified", {})
        main_bios = classified.get("main_bios", [])
        ec_list = classified.get("ec_firmware", [])
        me_list = classified.get("me_regions", [])

        # Populate candidate list with professional blue/cyan tags
        for b in main_bios:
            sz_mb = os.path.getsize(b) / (1024 * 1024)
            item = QListWidgetItem(f"★ MAIN BIOS: {os.path.basename(b)}  ({sz_mb:.2f} MB)")
            item.setData(Qt.ItemDataRole.UserRole, b)
            item.setForeground(QColor("#00f3ff"))  # Cyber Cyan
            self.file_list.addItem(item)

        for ec in ec_list:
            sz_kb = os.path.getsize(ec) / 1024
            item = QListWidgetItem(f"⚙ EC / KBC: {os.path.basename(ec)}  ({sz_kb:.0f} KB)")
            item.setData(Qt.ItemDataRole.UserRole, ec)
            item.setForeground(QColor("#38bdf8"))  # Sky Blue
            self.file_list.addItem(item)

        for me in me_list:
            sz_mb = os.path.getsize(me) / (1024 * 1024)
            item = QListWidgetItem(f"🔒 ME REGION: {os.path.basename(me)}  ({sz_mb:.2f} MB)")
            item.setData(Qt.ItemDataRole.UserRole, me)
            item.setForeground(QColor("#fbbf24"))  # Amber Gold
            self.file_list.addItem(item)

        if not main_bios and not ec_list and not me_list:
            all_files = classified.get("all_files", [])
            for f in all_files[:25]:
                item = QListWidgetItem(f"📄 {os.path.basename(f)}  ({os.path.getsize(f):,} B)")
                item.setData(Qt.ItemDataRole.UserRole, f)
                item.setForeground(QColor("#94a3b8"))
                self.file_list.addItem(item)

        if self.file_list.count() > 0:
            self.file_list.setCurrentRow(0)

    def _open_output_dir(self):
        out_dir = self._output_dir
        if out_dir and os.path.isdir(out_dir):
            os.startfile(out_dir)
        else:
            self.log("[INFO] Output folder has not been created yet.")

    def _load_selected_candidate(self):
        item = self.file_list.currentItem()
        if not item:
            self.log("[INFO] Please select a firmware file from the list first.")
            return
        path = item.data(Qt.ItemDataRole.UserRole)
        if path and os.path.isfile(path):
            self.log(f"[ACTION] Loading into R1 BIOS Tool: {os.path.basename(path)}")
            self.bios_selected.emit(path)

    def _reveal_selected_candidate(self):
        item = self.file_list.currentItem()
        if not item:
            return
        path = item.data(Qt.ItemDataRole.UserRole)
        if path and os.path.isfile(path):
            subprocess.run(["explorer", f"/select,{os.path.abspath(path)}"])

    def _on_item_double_clicked(self, item):
        path = item.data(Qt.ItemDataRole.UserRole)
        if path and os.path.isfile(path):
            self.log(f"[ACTION] Loading candidate into R1 BIOS Tool: {os.path.basename(path)}")
            self.bios_selected.emit(path)


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    target = sys.argv[1] if len(sys.argv) > 1 else None
    win = R1ExtractorWindow(target)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
