"""
firmware_confirm_dialog.py - Enterprise Firmware Ingestion Confirmation Dialog
R1 BIOS TOOL Enterprise Edition

Displays file metadata (Name, Size) upon drag-and-drop or file browsing,
allowing the user to confirm with Enter key before launching heavy binary analysis.
Eliminates UI freeze/lag during file drop/open.
"""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen, QBrush


class CloseCrossButton(QPushButton):
    """Vector-drawn cross button with zero font dependencies."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(28, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Close")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        is_hover = self.underMouse()
        bg_color = QColor("#e03131") if is_hover else QColor("#252a2f")
        border_color = QColor("#ff4d4f") if is_hover else QColor("#3c444d")
        cross_color = QColor("#ffffff") if is_hover else QColor("#e2e8f0")
        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(border_color, 1))
        painter.drawEllipse(1, 1, 26, 26)
        pen = QPen(cross_color, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(9, 9, 19, 19)
        painter.drawLine(9, 19, 19, 9)
        painter.end()


class FirmwareConfirmDialog(QDialog):
    """
    Sleek, minimalist Enterprise dialog that pauses before heavy analysis,
    showing file size/details and prompting user to confirm.
    """

    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self.file_path = os.path.abspath(file_path)
        self._drag_pos = None

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setFixedWidth(500)

        self._setup_ui()
        self._apply_shadow()

    def _format_size(self, size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} bytes"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB  ({size_bytes:,} bytes)"
        else:
            return f"{size_bytes / (1024 * 1024):.2f} MB  ({size_bytes:,} bytes)"

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
        card_layout.setContentsMargins(22, 18, 22, 20)
        card_layout.setSpacing(14)

        # ── Header Bar ──
        header = QHBoxLayout()
        header.setSpacing(10)

        lbl_title = QLabel("FIRMWARE INGESTION")
        lbl_title.setStyleSheet("font-family:'Segoe UI', sans-serif; font-size: 15px; font-weight: 700; color: #38bdf8; letter-spacing: 0.5px;")
        header.addWidget(lbl_title)

        header.addStretch()

        btn_close = CloseCrossButton(self)
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
        meta_box.setStyleSheet("background: #14171a; border: 1px solid #283038; border-radius: 8px;")
        meta_layout = QVBoxLayout(meta_box)
        meta_layout.setSpacing(10)
        meta_layout.setContentsMargins(16, 14, 16, 14)

        file_name = os.path.basename(self.file_path)
        file_size = os.path.getsize(self.file_path) if os.path.exists(self.file_path) else 0

        # File Name
        lbl_name = QLabel(file_name)
        lbl_name.setStyleSheet("font-family:'Segoe UI', sans-serif; font-size: 13px; font-weight: 700; color: #f1f5f9; border: none; background: transparent;")
        lbl_name.setWordWrap(True)
        meta_layout.addWidget(lbl_name)

        # Size Row
        sz_row = QHBoxLayout()
        sz_title = QLabel("FILE SIZE:")
        sz_title.setStyleSheet("font-family:'Segoe UI', sans-serif; font-size: 11px; font-weight: 800; color: #64748b; border: none; background: transparent;")
        sz_row.addWidget(sz_title)

        sz_val = QLabel(self._format_size(file_size))
        sz_val.setStyleSheet("font-family:'Segoe UI', 'Consolas', monospace; font-size: 12px; font-weight: 700; color: #38bdf8; border: none; background: transparent;")
        sz_row.addWidget(sz_val)
        sz_row.addStretch()
        meta_layout.addLayout(sz_row)

        card_layout.addWidget(meta_box)

        # ── Buttons ──
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        btn_cancel = QPushButton("Cancel (Esc)")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setMinimumHeight(42)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: #252a2e;
                color: #94a3b8;
                border: 1px solid #3c444d;
                border-radius: 6px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
                font-weight: 600;
                padding: 0 20px;
            }
            QPushButton:hover {
                background: #2e353b;
                color: #ffffff;
                border-color: #38bdf8;
            }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        self.btn_analyze = QPushButton("START ANALYSIS  [Enter]")
        self.btn_analyze.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_analyze.setMinimumHeight(42)
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
