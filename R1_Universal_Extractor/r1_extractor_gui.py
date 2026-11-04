"""
R1_Universal_Extractor: r1_extractor_gui.py
============================================
Standalone Cyberpunk/Dark GUI for R1 Universal Extractor.
Can run completely independently for testing or embedded inside R1 BIOS TOOL.
"""

import os
import sys
import threading
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QProgressBar,
    QFileDialog, QListWidget, QListWidgetItem, QFrame, QSplitter
)
from PySide6.QtCore import Qt, Signal, Slot, QMetaObject, Q_ARG
from PySide6.QtGui import QFont, QColor, QIcon

# Ensure local core can be imported
sys.path.insert(0, os.path.dirname(__file__))
from r1_extractor_core import R1ExtractorCore


class DropZoneWidget(QFrame):
    """Glossy Drag-and-Drop file zone widget."""
    file_dropped = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFixedHeight(120)
        self.setStyleSheet("""
            QFrame {
                background: #0f1418;
                border: 2px dashed #00f3ff;
                border-radius: 8px;
            }
            QFrame:hover {
                background: #151d24;
                border: 2px dashed #39ff14;
            }
        """)
        layout = QVBoxLayout(self)
        self.label = QLabel("📂 DRAG & DROP BIOS INSTALLER / EXECUTABLE HERE\n(Supports .EXE, .BIN, .ROM, .FD, .CAP, .ZIP, .7Z, .CAB, .MSI, .PKG)", self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("color: #00f3ff; font-weight: bold; font-family: 'Consolas', sans-serif; font-size: 13px; line-height: 1.5;")
        layout.addWidget(self.label)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if path:
                self.file_dropped.emit(path)


class R1ExtractorWindow(QMainWindow):
    """Main standalone window for R1 Universal Extractor."""

    log_signal = Signal(str)
    progress_signal = Signal(int)
    extraction_finished = Signal(dict)
    bios_selected = Signal(str)

    def __init__(self, target_file: str = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("R1 UNIVERSAL BIOS EXTRACTOR v2.0 - [STANDALONE ENGINE]")
        self.resize(950, 680)
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #0b0e11;
                color: #e2e8f0;
                font-family: 'Segoe UI', Consolas, sans-serif;
            }
            QLabel {
                color: #94a3b8;
                font-size: 12px;
            }
            QLineEdit {
                background: #141a20;
                border: 1px solid #1f2933;
                border-radius: 4px;
                color: #00f3ff;
                padding: 6px 10px;
                font-family: 'Consolas', monospace;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #00f3ff;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0052cc, stop:1 #00f3ff);
                color: #ffffff;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                padding: 7px 16px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0066ff, stop:1 #39ff14);
                color: #000000;
            }
            QPushButton#ActionBtn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00875a, stop:1 #39ff14);
                color: #000000;
                font-size: 13px;
                font-weight: 800;
                padding: 10px 20px;
            }
            QTextEdit {
                background-color: #07090b;
                border: 1px solid #1a232c;
                border-radius: 6px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
                color: #4cd3e3;
            }
            QProgressBar {
                border: 1px solid #1a232c;
                border-radius: 4px;
                text-align: center;
                color: #ffffff;
                background-color: #10151b;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0052cc, stop:1 #39ff14);
                border-radius: 3px;
            }
            QListWidget {
                background-color: #0f1418;
                border: 1px solid #1a232c;
                border-radius: 6px;
                color: #ffffff;
                font-family: 'Consolas', monospace;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #141a20;
            }
            QListWidget::item:selected {
                background-color: #1b4b5e;
                color: #39ff14;
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
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # Header Title
        hdr_layout = QHBoxLayout()
        title = QLabel("⚡ R1 UNIVERSAL BIOS EXTRACTOR ⚡")
        title.setStyleSheet("font-size: 18px; font-weight: 900; color: #00f3ff; letter-spacing: 1.5px;")
        hdr_layout.addWidget(title)
        hdr_layout.addStretch()
        version_lbl = QLabel("v2.0 [NATIVE ENGINE]")
        version_lbl.setStyleSheet("color: #39ff14; font-weight: bold; font-family: Consolas;")
        hdr_layout.addWidget(version_lbl)
        main_layout.addLayout(hdr_layout)

        # Drag & Drop Zone
        self.drop_zone = DropZoneWidget(self)
        self.drop_zone.file_dropped.connect(self.set_input_file)
        main_layout.addWidget(self.drop_zone)

        # Input & Output File Selectors
        form_layout = QVBoxLayout()
        form_layout.setSpacing(8)

        # Input row
        in_row = QHBoxLayout()
        in_lbl = QLabel("TARGET FILE:")
        in_lbl.setFixedWidth(110)
        self.in_edit = QLineEdit()
        self.in_edit.setPlaceholderText("Select BIOS installer, package, or raw binary...")
        btn_in_browse = QPushButton("BROWSE")
        btn_in_browse.clicked.connect(self._browse_input)
        in_row.addWidget(in_lbl)
        in_row.addWidget(self.in_edit)
        in_row.addWidget(btn_in_browse)
        form_layout.addLayout(in_row)

        # Output row
        out_row = QHBoxLayout()
        out_lbl = QLabel("EXTRACT TO:")
        out_lbl.setFixedWidth(110)
        self.out_edit = QLineEdit()
        self.out_edit.setPlaceholderText("Output folder destination...")
        btn_out_browse = QPushButton("BROWSE")
        btn_out_browse.clicked.connect(self._browse_output)
        out_row.addWidget(out_lbl)
        out_row.addWidget(self.out_edit)
        out_row.addWidget(btn_out_browse)
        form_layout.addLayout(out_row)

        main_layout.addLayout(form_layout)

        # Action Buttons Row
        action_row = QHBoxLayout()
        self.btn_extract = QPushButton("⚡ START UNIVERSAL EXTRACTION")
        self.btn_extract.setObjectName("ActionBtn")
        self.btn_extract.clicked.connect(self.start_extraction)
        
        self.btn_open_out = QPushButton("📁 OPEN OUTPUT FOLDER")
        self.btn_open_out.setEnabled(False)
        self.btn_open_out.clicked.connect(self._open_output_dir)

        action_row.addWidget(self.btn_extract, 2)
        action_row.addWidget(self.btn_open_out, 1)
        main_layout.addLayout(action_row)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(12)
        self.progress_bar.setTextVisible(False)
        main_layout.addWidget(self.progress_bar)

        # Splitter: Terminal Log (Left) vs Detected Files (Right)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left Panel: Cyber Terminal
        term_box = QWidget()
        term_layout = QVBoxLayout(term_box)
        term_layout.setContentsMargins(0, 0, 0, 0)
        term_lbl = QLabel("EXTRACTION TERMINAL LOG:")
        term_lbl.setStyleSheet("color: #00f3ff; font-weight: bold; font-size: 11px;")
        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        term_layout.addWidget(term_lbl)
        term_layout.addWidget(self.terminal)
        splitter.addWidget(term_box)

        # Right Panel: Classified BIOS Candidates
        res_box = QWidget()
        res_layout = QVBoxLayout(res_box)
        res_layout.setContentsMargins(0, 0, 0, 0)
        res_lbl = QLabel("DETECTED BIOS FIRMWARE CANDIDATES:")
        res_lbl.setStyleSheet("color: #39ff14; font-weight: bold; font-size: 11px;")
        self.file_list = QListWidget()
        self.file_list.doubleClicked.connect(self._on_item_double_clicked)
        res_layout.addWidget(res_lbl)
        res_layout.addWidget(self.file_list)

        cand_btn_box = QHBoxLayout()
        self.btn_load_in_tool = QPushButton("?? LOAD INTO R1 TOOL")
        self.btn_load_in_tool.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff0055, stop:1 #ff5500);
                color: #ffffff;
                font-weight: bold;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff3377, stop:1 #ffaa00);
            }
        """)
        self.btn_load_in_tool.clicked.connect(self._load_selected_candidate)

        self.btn_reveal = QPushButton("?? SHOW IN FOLDER")
        self.btn_reveal.setStyleSheet("""
            QPushButton {
                background: #141a20;
                color: #00f3ff;
                border: 1px solid #1f2933;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background: #1b242d;
                border: 1px solid #00f3ff;
            }
        """)
        self.btn_reveal.clicked.connect(self._reveal_selected_candidate)

        cand_btn_box.addWidget(self.btn_load_in_tool)
        cand_btn_box.addWidget(self.btn_reveal)
        res_layout.addLayout(cand_btn_box)

        splitter.addWidget(res_box)

        splitter.setSizes([550, 400])
        main_layout.addWidget(splitter, 2)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def set_input_file(self, path: str):
        self.in_edit.setText(path)
        base = os.path.basename(path)
        stem = os.path.splitext(base)[0]
        parent_dir = os.path.dirname(path)
        default_out = os.path.join(parent_dir, f"{stem}_extracted")
        self.out_edit.setText(default_out)
        self.log(f"[SELECTED] Target file: {base}")

    def _browse_input(self):
        f, _ = QFileDialog.getOpenFileName(
            self, "Select BIOS File or Installer", "",
            "BIOS & Installer Files (*.exe *.bin *.rom *.fd *.cap *.zip *.7z *.cab *.msi *.pkg);;All Files (*.*)"
        )
        if f:
            self.set_input_file(f)

    def _browse_output(self):
        d = QFileDialog.getExistingDirectory(self, "Select Output Directory", self.out_edit.text() or "")
        if d:
            self.out_edit.setText(d)

    def log(self, text: str):
        self.log_signal.emit(text)

    def _append_log(self, text: str):
        # Color coding in terminal
        color = "#4cd3e3"
        if "[SUCCESS]" in text or "★" in text:
            color = "#39ff14"
        elif "[ERROR]" in text or "[ERR]" in text:
            color = "#ff3366"
        elif "[START]" in text or "[TARGET]" in text or "[SUMMARY]" in text:
            color = "#00f3ff"
        elif "[CARVER]" in text:
            color = "#ffcc00"
        elif "[VENDOR]" in text:
            color = "#c084fc"

        html_msg = f"<span style='color: {color};'>{text}</span>"
        self.terminal.append(html_msg)
        self.terminal.verticalScrollBar().setValue(self.terminal.verticalScrollBar().maximum())

    def start_extraction(self):
        target = self.in_edit.text().strip()
        out_dir = self.out_edit.text().strip()

        if not target or not os.path.isfile(target):
            self.log("[ERROR] Please select a valid target file.")
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

        # Populate candidate list
        for b in main_bios:
            sz_mb = os.path.getsize(b) / (1024 * 1024)
            item = QListWidgetItem(f"★ MAIN BIOS: {os.path.basename(b)}  ({sz_mb:.2f} MB)")
            item.setData(Qt.ItemDataRole.UserRole, b)
            item.setForeground(QColor("#39ff14"))
            self.file_list.addItem(item)

        for ec in ec_list:
            sz_kb = os.path.getsize(ec) / 1024
            item = QListWidgetItem(f"⚙ EC / KBC: {os.path.basename(ec)}  ({sz_kb:.0f} KB)")
            item.setData(Qt.ItemDataRole.UserRole, ec)
            item.setForeground(QColor("#00f3ff"))
            self.file_list.addItem(item)

        for me in me_list:
            sz_mb = os.path.getsize(me) / (1024 * 1024)
            item = QListWidgetItem(f"🔒 ME REGION: {os.path.basename(me)}  ({sz_mb:.2f} MB)")
            item.setData(Qt.ItemDataRole.UserRole, me)
            item.setForeground(QColor("#ffcc00"))
            self.file_list.addItem(item)

        if not main_bios and not ec_list and not me_list:
            all_files = classified.get("all_files", [])
            for f in all_files[:20]:
                item = QListWidgetItem(f"📄 {os.path.basename(f)}  ({os.path.getsize(f):,} B)")
                item.setData(Qt.ItemDataRole.UserRole, f)
                self.file_list.addItem(item)

    def _open_output_dir(self):
        out_dir = self.out_edit.text().strip()
        if os.path.isdir(out_dir):
            os.startfile(out_dir)

    def _load_selected_candidate(self):
        item = self.file_list.currentItem()
        if not item:
            return
        path = item.data(Qt.ItemDataRole.UserRole)
        if path and os.path.isfile(path):
            self.log(f"[ACTION] Loading candidate into R1 BIOS Tool: {os.path.basename(path)}")
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

