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
from PySide6.QtGui import (
    QColor, QFont, QCursor, QPainter, QPen, QBrush, QLinearGradient
)

# Ensure local core can be imported
sys.path.insert(0, os.path.dirname(__file__))
from r1_extractor_core import R1ExtractorCore


class DropZoneWidget(QFrame):
    """Sleek vector-drawn Drag-and-Drop file zone widget matching R1 BIOS TOOL aesthetics."""
    file_dropped = Signal(str)
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("UniversalDropZone")
        self.setAcceptDrops(True)
        self.setFixedHeight(125)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._is_hover = False
        self._loaded_path = None

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(5)
        layout.setContentsMargins(10, 24, 10, 10)

        self.title_label = QLabel("DROP BIOS INSTALLER OR FIRMWARE PACKAGE HERE", self)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("color: #00f3ff; font-weight: 800; font-family: 'Segoe UI', sans-serif; font-size: 13px; letter-spacing: 1.5px; background: transparent;")

        self.sub_label = QLabel("Supports: .exe, .bin, .rom, .fd, .cap, .zip, .7z, .cab, .msi, .pkg  •  Click to Browse", self)
        self.sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sub_label.setStyleSheet("color: #94a3b8; font-size: 11px; font-family: 'Segoe UI', sans-serif; background: transparent;")

        layout.addWidget(self.title_label)
        layout.addWidget(self.sub_label)

    def set_file_info(self, path: str):
        self._loaded_path = path
        if path and os.path.exists(path):
            base = os.path.basename(path)
            try:
                sz_mb = os.path.getsize(path) / (1024 * 1024)
                sz_str = f"({sz_mb:.2f} MB)"
            except OSError:
                sz_str = ""
            self.title_label.setText(f"{base}  {sz_str}")
            self.title_label.setStyleSheet("color: #00f3ff; font-weight: 800; font-family: 'Segoe UI', Consolas, sans-serif; font-size: 13px; letter-spacing: 1px; background: transparent;")
            self.sub_label.setText("READY FOR EXTRACTION  •  Click or drag another file to replace")
            self.sub_label.setStyleSheet("color: #4ade80; font-size: 11px; font-weight: 700; font-family: 'Segoe UI', sans-serif; background: transparent;")
        else:
            self.reset_state()
        self.update()

    def reset_state(self):
        self._loaded_path = None
        self.title_label.setText("DROP BIOS INSTALLER OR FIRMWARE PACKAGE HERE")
        self.title_label.setStyleSheet("color: #00f3ff; font-weight: 800; font-family: 'Segoe UI', sans-serif; font-size: 13px; letter-spacing: 1.5px; background: transparent;")
        self.sub_label.setText("Supports: .exe, .bin, .rom, .fd, .cap, .zip, .7z, .cab, .msi, .pkg  •  Click to Browse")
        self.sub_label.setStyleSheet("color: #94a3b8; font-size: 11px; font-family: 'Segoe UI', sans-serif; background: transparent;")
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)
        bg = QLinearGradient(0, 0, 0, rect.height())
        if self._is_hover:
            bg.setColorAt(0, QColor("#132235"))
            bg.setColorAt(1, QColor("#0d1624"))
            border_col = QColor("#00f3ff")
            icon_col = QColor("#00f3ff")
        else:
            bg.setColorAt(0, QColor("#101722"))
            bg.setColorAt(1, QColor("#080d15"))
            border_col = QColor("#1e3a5f") if self._loaded_path else QColor("#1e293b")
            icon_col = QColor("#38bdf8") if self._loaded_path else QColor("#2ac4db")

        painter.setBrush(QBrush(bg))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, 8, 8)

        # Minimalist Vector Download/Tray Icon
        cx = rect.center().x()
        cy = 28
        pen_icon = QPen(icon_col, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_icon)

        # Tray
        painter.drawLine(cx - 16, cy + 10, cx + 16, cy + 10)
        painter.drawLine(cx - 16, cy + 4, cx - 16, cy + 10)
        painter.drawLine(cx + 16, cy + 4, cx + 16, cy + 10)

        # Arrow
        painter.drawLine(cx, cy - 8, cx, cy + 4)
        painter.drawLine(cx - 5, cy - 1, cx, cy + 4)
        painter.drawLine(cx + 5, cy - 1, cx, cy + 4)

        # Subtle dashed border
        pen_border = QPen(border_col, 1.2, Qt.PenStyle.DashLine)
        pen_border.setDashPattern([6, 4])
        painter.setPen(pen_border)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, 8, 8)
        painter.end()

        super().paintEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._is_hover = True
            self.update()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self._is_hover = False
        self.update()

    def dropEvent(self, event):
        self._is_hover = False
        self.update()
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
        self.resize(980, 680)
        self.setMinimumSize(880, 580)

        self._target_file = ""
        self._output_dir = ""

        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #080c14;
                color: #e2e8f0;
                font-family: 'Segoe UI', -apple-system, sans-serif;
            }
            QLabel {
                color: #94a3b8;
                font-size: 12px;
            }
            QLineEdit {
                background: #060910;
                border: 1px solid #1a2536;
                border-radius: 5px;
                color: #38bdf8;
                padding: 7px 12px;
                font-family: 'Consolas', 'Cascadia Code', monospace;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #00f3ff;
            }
            QPushButton {
                background: linear-gradient(to bottom, #1e2838 0%, #131b26 100%);
                color: #e2e8f0;
                border: 1px solid #2a3a50;
                border-radius: 5px;
                padding: 8px 18px;
                font-size: 12px;
                font-weight: 700;
                font-family: 'Segoe UI', sans-serif;
            }
            QPushButton:hover {
                border-color: #00f3ff;
                color: #00f3ff;
                background: #1a273b;
            }
            QPushButton:disabled {
                background: #0f151f;
                color: #475569;
                border-color: #1a2332;
            }
            QPushButton#ActionBtn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:0.5 #00b4d8, stop:1 #00f3ff);
                color: #05131e;
                font-size: 12px;
                font-weight: 800;
                padding: 10px 22px;
                border-radius: 6px;
                border: none;
                letter-spacing: 0.8px;
            }
            QPushButton#ActionBtn:hover:not(:disabled) {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0369a1, stop:0.5 #38bdf8, stop:1 #67e8f9);
                color: #000000;
            }
            QPushButton#ActionBtn:disabled {
                background: #151d28;
                color: #475569;
                border: 1px solid #1e293b;
            }
            QPushButton#SecondaryBtn {
                background: linear-gradient(to bottom, #1a2433 0%, #101722 100%);
                border: 1px solid #1e3a5f;
                color: #38bdf8;
                font-size: 11px;
                font-weight: 700;
                padding: 9px 18px;
                border-radius: 6px;
                letter-spacing: 0.5px;
            }
            QPushButton#SecondaryBtn:hover:not(:disabled) {
                background: #16263b;
                border-color: #00f3ff;
                color: #ffffff;
            }
            QPushButton#SecondaryBtn:disabled {
                background: #101620;
                color: #475569;
                border-color: #182230;
            }
            QTextEdit {
                background-color: #05080e;
                border: 1px solid #16202c;
                border-radius: 6px;
                font-family: 'Consolas', 'Cascadia Code', monospace;
                font-size: 11px;
                color: #cbd5e1;
                padding: 8px 10px;
                line-height: 1.4;
            }
            QProgressBar {
                border: 1px solid #16202c;
                border-radius: 3px;
                text-align: center;
                background-color: #080d14;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0052cc, stop:1 #00f3ff);
                border-radius: 2px;
            }
            QListWidget {
                background-color: #070b12;
                border: 1px solid #16202c;
                border-radius: 6px;
                color: #e2e8f0;
                font-family: 'Consolas', monospace;
                font-size: 11px;
            }
            QListWidget::item {
                padding: 8px 10px;
                border-bottom: 1px solid #0f1622;
            }
            QListWidget::item:hover {
                background-color: #0d1a29;
            }
            QListWidget::item:selected {
                background-color: #132a40;
                border: 1px solid #00f3ff;
                color: #ffffff;
            }
        """)

        self._init_ui()
        self.log_signal.connect(self._append_log)
        self.progress_signal.connect(self.progress_bar.setValue)
        self.extraction_finished.connect(self._on_extract_complete)

        # Welcome message in terminal
        self.log("[SYSTEM] R1 Universal Extractor Engine (Native 5-Tier Unpacker) ready.")
        self.log("[INFO] Drop any BIOS package or installer (.exe, .cap, .zip, .bin) to begin.")

        if target_file and os.path.isfile(target_file):
            self.set_input_file(target_file)

    def _init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(18, 16, 18, 16)
        main_layout.setSpacing(10)

        # 1. Header Bar
        hdr_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title = QLabel("R1 UNIVERSAL BIOS EXTRACTOR", self)
        title.setStyleSheet("font-size: 16px; font-weight: 900; color: #00f3ff; letter-spacing: 1.5px;")
        subtitle = QLabel("Native 5-Tier Firmware Unpacker • Auto-Path Resolution • SPI Carver", self)
        subtitle.setStyleSheet("font-size: 11px; color: #64748b; font-weight: 500;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        hdr_layout.addLayout(title_box)
        hdr_layout.addStretch()

        engine_chip = QLabel("ENGINE: 100% NATIVE IN-HOUSE", self)
        engine_chip.setStyleSheet("background: #0c2438; color: #38bdf8; border: 1px solid #0284c7; border-radius: 4px; padding: 5px 12px; font-size: 11px; font-weight: 700; font-family: 'Segoe UI', Consolas, sans-serif; letter-spacing: 0.5px;")
        hdr_layout.addWidget(engine_chip)
        main_layout.addLayout(hdr_layout)

        # 2. Interactive Drag & Drop Zone (Click to Browse)
        self.drop_zone = DropZoneWidget(self)
        self.drop_zone.file_dropped.connect(self.set_input_file)
        self.drop_zone.clicked.connect(self._browse_input)
        main_layout.addWidget(self.drop_zone)

        # 3. File Info & Auto-Destination Card
        info_frame = QFrame(self)
        info_frame.setStyleSheet("""
            QFrame {
                background: #0b111a;
                border: 1px solid #1a2536;
                border-radius: 6px;
            }
        """)
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(12, 10, 12, 10)
        info_layout.setSpacing(8)

        # Target file row
        t_row = QHBoxLayout()
        t_lbl = QLabel("SELECTED FILE:", self)
        t_lbl.setFixedWidth(140)
        t_lbl.setStyleSheet("color: #94a3b8; font-weight: 700; font-size: 11px; letter-spacing: 0.5px;")
        self.in_edit = QLineEdit(self)
        self.in_edit.setPlaceholderText("No file selected. Drop an installer above or click Browse...")
        self.in_edit.setReadOnly(True)
        btn_in_browse = QPushButton("BROWSE", self)
        btn_in_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_in_browse.clicked.connect(self._browse_input)
        t_row.addWidget(t_lbl)
        t_row.addWidget(self.in_edit)
        t_row.addWidget(btn_in_browse)
        info_layout.addLayout(t_row)

        # Auto-Destination Row (Display only, no manual target input needed)
        dest_row = QHBoxLayout()
        d_lbl = QLabel("AUTO DESTINATION:", self)
        d_lbl.setFixedWidth(140)
        d_lbl.setStyleSheet("color: #38bdf8; font-weight: 700; font-size: 11px; letter-spacing: 0.5px;")
        self.dest_display = QLabel("Output folder will be created automatically alongside the source file", self)
        self.dest_display.setStyleSheet("color: #64748b; font-family: 'Consolas', monospace; font-size: 11px;")
        dest_row.addWidget(d_lbl)
        dest_row.addWidget(self.dest_display, 1)
        info_layout.addLayout(dest_row)

        main_layout.addWidget(info_frame)

        # 4. Action Row (Start Extraction & Open Output Folder)
        action_row = QHBoxLayout()
        action_row.setSpacing(10)
        self.btn_extract = QPushButton("START UNIVERSAL EXTRACTION", self)
        self.btn_extract.setObjectName("ActionBtn")
        self.btn_extract.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_extract.setFixedHeight(40)
        self.btn_extract.setEnabled(False)
        self.btn_extract.clicked.connect(self.start_extraction)

        self.btn_open_out = QPushButton("OPEN OUTPUT FOLDER", self)
        self.btn_open_out.setObjectName("SecondaryBtn")
        self.btn_open_out.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_out.setFixedHeight(40)
        self.btn_open_out.setEnabled(False)
        self.btn_open_out.clicked.connect(self._open_output_dir)

        action_row.addWidget(self.btn_extract, 2)
        action_row.addWidget(self.btn_open_out, 1)
        main_layout.addLayout(action_row)

        # 5. Progress Bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(5)
        self.progress_bar.setTextVisible(False)
        main_layout.addWidget(self.progress_bar)

        # 6. Splitter: Live Terminal (Left) vs Detected Firmware Candidates (Right)
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setHandleWidth(6)

        # Left Panel: Live Terminal Log
        term_box = QWidget(self)
        term_layout = QVBoxLayout(term_box)
        term_layout.setContentsMargins(0, 0, 0, 0)
        term_layout.setSpacing(6)
        term_lbl = QLabel("LIVE EXTRACTION LOG", self)
        term_lbl.setStyleSheet("color: #38bdf8; font-weight: 800; font-size: 11px; letter-spacing: 0.8px;")
        self.terminal = QTextEdit(self)
        self.terminal.setReadOnly(True)
        term_layout.addWidget(term_lbl)
        term_layout.addWidget(self.terminal)
        splitter.addWidget(term_box)

        # Right Panel: Classified BIOS Candidates
        res_box = QWidget(self)
        res_layout = QVBoxLayout(res_box)
        res_layout.setContentsMargins(0, 0, 0, 0)
        res_layout.setSpacing(6)
        res_lbl = QLabel("DETECTED FIRMWARE CANDIDATES", self)
        res_lbl.setStyleSheet("color: #00f3ff; font-weight: 800; font-size: 11px; letter-spacing: 0.8px;")
        self.file_list = QListWidget(self)
        self.file_list.doubleClicked.connect(self._on_item_double_clicked)
        res_layout.addWidget(res_lbl)
        res_layout.addWidget(self.file_list)

        # Candidate Action Buttons
        cand_btn_box = QHBoxLayout()
        cand_btn_box.setSpacing(8)
        self.btn_load_in_tool = QPushButton("LOAD INTO R1 TOOL", self)
        self.btn_load_in_tool.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_load_in_tool.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0052cc, stop:1 #00b4d8);
                color: #ffffff;
                font-weight: 800;
                border-radius: 5px;
                padding: 8px 16px;
                font-size: 11px;
                border: none;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0066ff, stop:1 #00f3ff);
                color: #ffffff;
            }
        """)
        self.btn_load_in_tool.clicked.connect(self._load_selected_candidate)

        self.btn_reveal = QPushButton("SHOW IN FOLDER", self)
        self.btn_reveal.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reveal.setStyleSheet("""
            QPushButton {
                background: linear-gradient(to bottom, #1e2838 0%, #131b26 100%);
                border: 1px solid #2a3a50;
                color: #94a3b8;
                font-weight: 700;
                border-radius: 5px;
                padding: 8px 16px;
                font-size: 11px;
            }
            QPushButton:hover {
                border-color: #00f3ff;
                color: #ffffff;
                background: #1a273b;
            }
        """)
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

        self.drop_zone.set_file_info(path)
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
        elif "[START]" in text or "[TARGET]" in text or "[SUMMARY]" in text or "[SELECTED]" in text:
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
            item = QListWidgetItem(f"[MAIN BIOS] {os.path.basename(b)}  ({sz_mb:.2f} MB)")
            item.setData(Qt.ItemDataRole.UserRole, b)
            item.setForeground(QColor("#00f3ff"))  # Cyber Cyan
            self.file_list.addItem(item)

        for ec in ec_list:
            sz_kb = os.path.getsize(ec) / 1024
            item = QListWidgetItem(f"[EC / KBC] {os.path.basename(ec)}  ({sz_kb:.0f} KB)")
            item.setData(Qt.ItemDataRole.UserRole, ec)
            item.setForeground(QColor("#38bdf8"))  # Sky Blue
            self.file_list.addItem(item)

        for me in me_list:
            sz_mb = os.path.getsize(me) / (1024 * 1024)
            item = QListWidgetItem(f"[ME REGION] {os.path.basename(me)}  ({sz_mb:.2f} MB)")
            item.setData(Qt.ItemDataRole.UserRole, me)
            item.setForeground(QColor("#fbbf24"))  # Amber Gold
            self.file_list.addItem(item)

        if not main_bios and not ec_list and not me_list:
            all_files = classified.get("all_files", [])
            for f in all_files[:25]:
                item = QListWidgetItem(f"[FILE] {os.path.basename(f)}  ({os.path.getsize(f):,} B)")
                item.setData(Qt.ItemDataRole.UserRole, f)
                item.setForeground(QColor("#94a3b8"))
                self.file_list.addItem(item)

        if self.file_list.count() > 0:
            self.file_list.setCurrentRow(0)

    def _open_output_dir(self):
        if self._output_dir and os.path.isdir(self._output_dir):
            if sys.platform == "win32":
                os.startfile(self._output_dir)
            else:
                subprocess.Popen(["xdg-open", self._output_dir])

    def _on_item_double_clicked(self, item: QListWidgetItem):
        file_path = item.data(Qt.ItemDataRole.UserRole)
        if file_path and os.path.isfile(file_path):
            self.bios_selected.emit(file_path)
            self.close()

    def _load_selected_candidate(self):
        item = self.file_list.currentItem()
        if item:
            self._on_item_double_clicked(item)

    def _reveal_selected_candidate(self):
        item = self.file_list.currentItem()
        if item:
            file_path = item.data(Qt.ItemDataRole.UserRole)
            if file_path and os.path.isfile(file_path):
                if sys.platform == "win32":
                    subprocess.run(["explorer", "/select,", os.path.normpath(file_path)])
                else:
                    self._open_output_dir()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    target = sys.argv[1] if len(sys.argv) > 1 else None
    win = R1ExtractorWindow(target_file=target)
    win.show()
    sys.exit(app.exec())
