"""
firmware_confirm_dialog.py - Enterprise Firmware Ingestion Confirmation Dialog
R1 BIOS TOOL Enterprise Edition

Displays file metadata (Name, Size, Type, Path) upon drag-and-drop or file browsing,
allowing the user to confirm with Enter key before launching heavy binary analysis.
Eliminates UI freeze/lag during file drop/open.
"""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGraphicsDropShadowEffect, QWidget
)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QColor, QFont


class FirmwareConfirmDialog(QDialog):
    """
    Sleek Enterprise dialog that pauses before heavy analysis,
    showing file size/details and prompting 'Press [ENTER] to start analysis'.
    """

    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self.file_path = os.path.abspath(file_path)
        self._drag_pos = None

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setMinimumWidth(500)
        self.resize(520, 340)

        self._setup_ui()
        self._apply_shadow()

    def _format_size(self, size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} bytes"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB  ({size_bytes:,} bytes)"
        else:
            return f"{size_bytes / (1024 * 1024):.2f} MB  ({size_bytes:,} bytes)"

    def _detect_format(self, ext: str) -> str:
        ext = ext.lower()
        formats = {
            ".bin": "RAW FIRMWARE BINARY",
            ".rom": "ROM SPI DUMP",
            ".fd":  "INSYDE H2O FLASH IMAGE",
            ".cap": "UEFI CAPSULE IMAGE",
            ".exe": "VENDOR UPDATE EXECUTABLE",
            ".pfs": "DELL PFS UPDATE PACKAGE",
            ".pkg": "FIRMWARE PACKAGE",
            ".sbk": "SECURE BOOT KEY DUMP",
            ".sbi": "SECURITY BINARY IMAGE",
            ".msdm": "MICROSOFT MSDM LICENSE DATA"
        }
        return formats.get(ext, "FIRMWARE DUMP")

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)

        # ── Card Frame ──
        self.card = QFrame()
        self.card.setObjectName("ConfirmCard")
        self.card.setStyleSheet("""
            QFrame#ConfirmCard {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #252a2e, stop:1 #1c2024);
                border: 1px solid #2d363f;
                border-radius: 12px;
            }
        """)
        root.addWidget(self.card)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(20, 18, 20, 20)
        card_layout.setSpacing(14)

        # ── Header Bar ──
        header = QHBoxLayout()
        header.setSpacing(10)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        lbl_title = QLabel("⚡ FIRMWARE INGESTION")
        lbl_title.setStyleSheet("font-family:'Segoe UI', sans-serif; font-size: 15px; font-weight: 800; color: #4cd3e3; letter-spacing: 1px;")

        lbl_sub = QLabel("File loaded into workspace. Review details and confirm analysis.")
        lbl_sub.setStyleSheet("font-family:'Segoe UI', sans-serif; font-size: 11px; color: #94a3b8;")
        title_col.addWidget(lbl_title)
        title_col.addWidget(lbl_sub)
        header.addLayout(title_col)

        header.addStretch()

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(28, 28)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                background: #252a2f;
                color: #94a3b8;
                border: 1px solid #3c444d;
                border-radius: 14px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #e03131;
                color: white;
                border-color: #e03131;
            }
        """)
        btn_close.clicked.connect(self.reject)
        header.addWidget(btn_close)

        card_layout.addLayout(header)

        # Separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #2d363f; max-height: 1px; border: none;")
        card_layout.addWidget(sep)

        # ── Metadata Box ──
        meta_box = QFrame()
        meta_box.setStyleSheet("background: #14171a; border: 1px solid #283038; border-radius: 8px; padding: 12px;")
        meta_layout = QVBoxLayout(meta_box)
        meta_layout.setSpacing(8)
        meta_layout.setContentsMargins(12, 10, 12, 10)

        file_name = os.path.basename(self.file_path)
        file_size = os.path.getsize(self.file_path) if os.path.exists(self.file_path) else 0
        _, ext = os.path.splitext(self.file_path)
        fmt_label = self._detect_format(ext)

        # File Name Row
        fn_row = QHBoxLayout()
        lbl_icon = QLabel("📄")
        lbl_icon.setStyleSheet("font-size: 15px; border: none; background: transparent;")
        fn_row.addWidget(lbl_icon)

        lbl_name = QLabel(file_name)
        lbl_name.setStyleSheet("font-family:'Segoe UI', sans-serif; font-size: 13px; font-weight: 700; color: #f1f5f9; border: none; background: transparent;")
        lbl_name.setWordWrap(True)
        fn_row.addWidget(lbl_name, stretch=1)

        badge_fmt = QLabel(fmt_label)
        badge_fmt.setStyleSheet("""
            QLabel {
                background: #252a2f;
                color: #38bdf8;
                border: 1px solid #3c444d;
                border-radius: 4px;
                padding: 3px 8px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }
        """)
        fn_row.addWidget(badge_fmt)
        meta_layout.addLayout(fn_row)

        # Size Row
        sz_row = QHBoxLayout()
        sz_title = QLabel("FILE SIZE:")
        sz_title.setStyleSheet("font-family:'Segoe UI', sans-serif; font-size: 10px; font-weight: 800; color: #64748b; border: none; background: transparent;")
        sz_row.addWidget(sz_title)

        sz_val = QLabel(self._format_size(file_size))
        sz_val.setStyleSheet("font-family:'Segoe UI', 'Consolas', monospace; font-size: 12px; font-weight: 700; color: #4cd3e3; border: none; background: transparent;")
        sz_row.addWidget(sz_val)
        sz_row.addStretch()
        meta_layout.addLayout(sz_row)

        # Path Row
        path_row = QHBoxLayout()
        p_title = QLabel("LOCATION:")
        p_title.setStyleSheet("font-family:'Segoe UI', sans-serif; font-size: 10px; font-weight: 800; color: #64748b; border: none; background: transparent;")
        path_row.addWidget(p_title)

        short_path = self.file_path if len(self.file_path) < 55 else "..." + self.file_path[-52:]
        p_val = QLabel(short_path)
        p_val.setStyleSheet("font-family:'Consolas', monospace; font-size: 10px; color: #94a3b8; border: none; background: transparent;")
        p_val.setToolTip(self.file_path)
        path_row.addWidget(p_val)
        path_row.addStretch()
        meta_layout.addLayout(path_row)

        card_layout.addWidget(meta_box)

        # ── Call-To-Action Banner ──
        banner = QFrame()
        banner.setStyleSheet("background: #112626; border: 1px solid #194d4d; border-radius: 6px; padding: 6px 12px;")
        banner_layout = QHBoxLayout(banner)
        banner_layout.setContentsMargins(8, 6, 8, 6)

        lbl_prompt = QLabel("⌨️  Press [ ENTER ] to start analysis  or  [ ESC ] to cancel")
        lbl_prompt.setStyleSheet("font-family:'Segoe UI', sans-serif; font-size: 11px; font-weight: 700; color: #00ff88; border: none; background: transparent;")
        lbl_prompt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        banner_layout.addWidget(lbl_prompt)
        card_layout.addWidget(banner)

        # ── Buttons ──
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        btn_cancel = QPushButton("Cancel (Esc)")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setMinimumHeight(40)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: #252a2e;
                color: #94a3b8;
                border: 1px solid #3c444d;
                border-radius: 6px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
                font-weight: 600;
                padding: 0 18px;
            }
            QPushButton:hover {
                background: #2e353b;
                color: #ffffff;
                border-color: #4cd3e3;
            }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        self.btn_analyze = QPushButton("⚡ START ANALYSIS  [Enter]")
        self.btn_analyze.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_analyze.setMinimumHeight(40)
        self.btn_analyze.setDefault(True)
        self.btn_analyze.setAutoDefault(True)
        self.btn_analyze.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8fe3ea, stop:0.5 #3598a6, stop:1 #247d8a);
                color: #0b151a;
                border: none;
                border-radius: 6px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
                font-weight: 900;
                letter-spacing: 0.5px;
                padding: 0 24px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #bbf2f6, stop:0.5 #45b1bf, stop:1 #2ca0b0);
                color: #000000;
            }
            QPushButton:focus {
                border: 2px solid #0ef6fd;
            }
        """)
        self.btn_analyze.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_analyze, stretch=1)

        card_layout.addLayout(btn_layout)

        # Set default focus to Analyze button so Enter key works right away!
        self.btn_analyze.setFocus()

    def _apply_shadow(self):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(36)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 8)
        self.card.setGraphicsEffect(shadow)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.accept()
        elif event.key() == Qt.Key.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)

    # Window Dragging support
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
