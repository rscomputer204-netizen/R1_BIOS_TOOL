"""
extractor_dialog.py
====================
A reusable, glossy drag-and-drop file selection popup dialog.
Used by both Universal Extractor, Dell PFS Extractor, and BIOS RG .EXE buttons.
Clean, professional interface with robust drag-and-drop support on Windows.
"""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QGraphicsDropShadowEffect, QSizePolicy, QFileDialog
)
from PySide6.QtCore import Qt, QMimeData, Signal
from PySide6.QtGui import (
    QDragEnterEvent, QDragMoveEvent, QDropEvent, QColor, QFont,
    QPainter, QPen, QBrush, QPainterPath, QLinearGradient
)


def _format_size(size_bytes: int) -> str:
    """Formats bytes into human readable KB/MB string."""
    if not size_bytes or size_bytes <= 0:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


class DropZone(QLabel):
    """A glossy, animated drag-and-drop zone widget with robust Windows drag support."""
    
    file_dropped = Signal(str)
    clicked_browse = Signal()
    
    def __init__(self, accepted_exts=None, parent=None):
        super().__init__(parent)
        self._accepted_exts = accepted_exts or []
        self._is_hovering_drag = False
        self._is_hovering_mouse = False
        self._is_loaded = False
        
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._reset_text()
        
    def _reset_text(self):
        self._is_loaded = False
        ext_hint = " / ".join(f"*.{e.lstrip('.')}" for e in self._accepted_exts) if self._accepted_exts else "Any file"
        self.setText(
            f"<div style='text-align:center; line-height:2.0;'>"
            f"<span style='font-size:15px; font-weight:900; letter-spacing:2px; color:#00f3ff;'>DROP FILE HERE</span><br>"
            f"<span style='font-size:12px; color:#94a3b8; margin-top:6px; display:block;'>or click to browse</span><br>"
            f"<span style='font-size:10px; color:#64748b;'>{ext_hint}</span>"
            f"</div>"
        )

    def set_file_loaded(self, filename: str, size_str: str):
        self._is_loaded = True
        sz_text = f" ({size_str})" if size_str else ""
        self.setText(
            f"<div style='text-align:center; line-height:2.0;'>"
            f"<span style='font-size:14px; font-weight:900; letter-spacing:1.5px; color:#38bdf8;'>FILE LOADED</span><br>"
            f"<span style='font-size:13px; font-weight:700; color:#f1f5f9;'>{filename}</span>"
            f"<span style='font-size:11px; color:#94a3b8;'>{sz_text}</span><br>"
            f"<span style='font-size:10px; color:#64748b; margin-top:6px; display:block;'>Click or drop another file to replace</span>"
            f"</div>"
        )
        self.update()

    def _extract_file_path(self, mime_data) -> str:
        if mime_data.hasUrls():
            urls = mime_data.urls()
            if urls:
                return os.path.normpath(urls[0].toLocalFile())
        if mime_data.hasText():
            raw = mime_data.text().strip()
            if raw.startswith("file:///"):
                from urllib.request import url2pathname
                raw = url2pathname(raw[8:])
            raw = os.path.normpath(raw)
            if os.path.exists(raw):
                return raw
        return ""

    def dragEnterEvent(self, event: QDragEnterEvent):
        path = self._extract_file_path(event.mimeData())
        if path and (not self._accepted_exts or any(path.lower().endswith(e) for e in self._accepted_exts)):
            self._is_hovering_drag = True
            self.update()
            event.acceptProposedAction()
            return
        event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent):
        path = self._extract_file_path(event.mimeData())
        if path and (not self._accepted_exts or any(path.lower().endswith(e) for e in self._accepted_exts)):
            event.acceptProposedAction()
        else:
            event.ignore()
        
    def dragLeaveEvent(self, event):
        self._is_hovering_drag = False
        self.update()
        
    def dropEvent(self, event: QDropEvent):
        self._is_hovering_drag = False
        self.update()
        path = self._extract_file_path(event.mimeData())
        if path and (not self._accepted_exts or any(path.lower().endswith(e) for e in self._accepted_exts)):
            event.acceptProposedAction()
            self.file_dropped.emit(path)
            
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked_browse.emit()
            
    def enterEvent(self, event):
        self._is_hovering_mouse = True
        self.update()
        
    def leaveEvent(self, event):
        self._is_hovering_mouse = False
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect().adjusted(4, 4, -4, -4)
        radius = 16
        
        # Background gradient
        grad = QLinearGradient(0, 0, 0, rect.height())
        if self._is_hovering_drag:
            grad.setColorAt(0, QColor(0, 200, 255, 60))
            grad.setColorAt(1, QColor(0, 100, 180, 30))
            border_color = QColor(0, 243, 255, 220)
            border_width = 2.5
        elif self._is_loaded:
            grad.setColorAt(0, QColor(14, 165, 233, 30))
            grad.setColorAt(1, QColor(10, 20, 35, 120))
            border_color = QColor(56, 189, 248, 180)
            border_width = 1.8
        elif self._is_hovering_mouse:
            grad.setColorAt(0, QColor(0, 243, 255, 25))
            grad.setColorAt(1, QColor(0, 50, 80, 15))
            border_color = QColor(0, 243, 255, 160)
            border_width = 1.5
        else:
            grad.setColorAt(0, QColor(20, 25, 45, 120))
            grad.setColorAt(1, QColor(10, 12, 25, 80))
            border_color = QColor(0, 243, 255, 80)
            border_width = 1.5
            
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)
        
        # Fill
        painter.fillPath(path, QBrush(grad))
        
        # Dashed border
        pen = QPen(border_color, border_width, Qt.PenStyle.DashLine)
        pen.setDashPattern([6, 4])
        painter.setPen(pen)
        painter.drawPath(path)
        
        # Glossy top highlight
        gloss = QPainterPath()
        gloss.addRoundedRect(rect.adjusted(8, 8, -8, rect.height() // 2 * -1), radius - 4, radius - 4)
        painter.fillPath(gloss, QBrush(QColor(255, 255, 255, 18)))
        
        painter.end()
        
        # Draw text on top
        super().paintEvent(event)


class CloseCrossButton(QPushButton):
    """Vector-drawn cross button with zero font dependencies."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(30, 30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Close")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        is_hover = self.underMouse()
        bg_color = QColor("#e03131") if is_hover else QColor("#252a2f")
        border_color = QColor("#ff4d4f") if is_hover else QColor("#4a5568")
        cross_color = QColor("#ffffff") if is_hover else QColor("#e2e8f0")
        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(border_color, 1))
        painter.drawEllipse(1, 1, 28, 28)
        pen = QPen(cross_color, 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(10, 10, 20, 20)
        painter.drawLine(10, 20, 20, 10)
        painter.end()


class ExtractorDropDialog(QDialog):
    """
    A glossy, reusable drag-and-drop popup for file extraction operations.
    """
    
    def __init__(self, title="File Extractor", subtitle="", accepted_exts=None, initial_file=None, initial_dir=None, parent=None):
        super().__init__(parent)
        self.selected_file = None
        self._title = title
        self._subtitle = subtitle
        self._accepted_exts = accepted_exts or []
        self._initial_file = initial_file
        self._initial_dir = initial_dir
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setMinimumSize(500, 390)
        self.setAcceptDrops(True)
        
        self._setup_ui()
        self._apply_shadow()

        # Pre-load initial file if provided
        if self._initial_file and os.path.exists(self._initial_file):
            self._on_file_received(self._initial_file)
        
    def _setup_ui(self):
        # Outer layout on transparent background
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)
        
        # Main container card
        card = QWidget()
        card.setObjectName("ExtractorCard")
        card.setStyleSheet("""
            QWidget#ExtractorCard {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #161928,
                    stop:0.4 #0f1120,
                    stop:1 #090b14);
                border-radius: 20px;
                border: 1px solid #1f2840;
            }
        """)
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 24, 28, 24)
        card_layout.setSpacing(14)
        
        # ── HEADER ──
        header = QHBoxLayout()
        
        icon_title = QVBoxLayout()
        icon_title.setSpacing(4)
        
        title_row = QHBoxLayout()
        title_lbl = QLabel(self._title)
        title_lbl.setStyleSheet("""
            color: #00f3ff;
            font-size: 16px;
            font-weight: 800;
            letter-spacing: 1.5px;
            font-family: 'Segoe UI', sans-serif;
        """)
        title_row.addWidget(title_lbl)
        title_row.addStretch()
        icon_title.addLayout(title_row)
        
        if self._subtitle:
            sub_lbl = QLabel(self._subtitle)
            sub_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
            sub_lbl.setWordWrap(True)
            icon_title.addWidget(sub_lbl)
            
        header.addLayout(icon_title)
        
        # Close button
        close_btn = CloseCrossButton(self)
        close_btn.clicked.connect(self.reject)
        header.addWidget(close_btn, 0, Qt.AlignmentFlag.AlignTop)
        card_layout.addLayout(header)
        
        # Divider
        divider = QWidget()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background: #1f2840;")
        card_layout.addWidget(divider)
        
        # ── DROP ZONE ──
        self.drop_zone = DropZone(accepted_exts=self._accepted_exts)
        self.drop_zone.file_dropped.connect(self._on_file_received)
        self.drop_zone.clicked_browse.connect(self._browse_file)
        card_layout.addWidget(self.drop_zone)
        
        # ── SELECTED FILE LABEL ──
        self.file_lbl = QLabel("No file selected")
        self.file_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        self.file_lbl.setStyleSheet("""
            QLabel {
                color: #64748b;
                font-size: 11px;
                padding: 10px 14px;
                background: #0a0c18;
                border-radius: 8px;
                border: 1px solid #1a1e30;
            }
            QLabel:hover {
                border-color: #38bdf8;
                color: #94a3b8;
            }
        """)
        self.file_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.file_lbl.setWordWrap(True)
        self.file_lbl.mousePressEvent = lambda e: self._browse_file() if e.button() == Qt.MouseButton.LeftButton else None
        card_layout.addWidget(self.file_lbl)
        
        # ── BOTTOM BUTTONS ──
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        
        cancel_btn = QPushButton("CANCEL")
        cancel_btn.setFixedHeight(42)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #1e293b;
                color: #94a3b8;
                border: 1px solid #334155;
                border-radius: 8px;
                font-size: 12px;
                font-weight: 700;
                letter-spacing: 1px;
                padding: 0 22px;
            }
            QPushButton:hover {
                background: #334155;
                color: #ffffff;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        self.extract_btn = QPushButton("EXTRACT")
        self.extract_btn.setFixedHeight(42)
        self.extract_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.extract_btn.setEnabled(False)
        self._apply_extract_btn_style(enabled=False)
        self.extract_btn.clicked.connect(self.accept)
        
        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.extract_btn)
        card_layout.addLayout(btn_row)
        
        outer.addWidget(card)
        
    def _apply_shadow(self):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 200, 255, 80))
        shadow.setOffset(0, 0)
        self.setGraphicsEffect(shadow)

    def _apply_extract_btn_style(self, enabled: bool):
        if enabled:
            self.extract_btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #38bdf8, stop:0.5 #0ea5e9, stop:1 #0284c7);
                    color: #041018;
                    border: 1px solid #7dd3fc;
                    border-radius: 8px;
                    font-size: 13px;
                    font-weight: 900;
                    letter-spacing: 1.5px;
                    padding: 0 28px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #7dd3fc, stop:0.5 #38bdf8, stop:1 #0ea5e9);
                    color: #000000;
                    border-color: #bae6fd;
                }
                QPushButton:pressed {
                    background: #0369a1;
                }
            """)
        else:
            self.extract_btn.setStyleSheet("""
                QPushButton {
                    background: #161e2e;
                    color: #475569;
                    border: 1px solid #1e293b;
                    border-radius: 8px;
                    font-size: 13px;
                    font-weight: 900;
                    letter-spacing: 1.5px;
                    padding: 0 28px;
                }
            """)
        
    def _on_file_received(self, path: str):
        if not path:
            return
        clean_path = os.path.normpath(path)
        if not os.path.exists(clean_path):
            return
            
        self.selected_file = clean_path
        name = os.path.basename(clean_path)
        
        # Calculate file size
        try:
            sz_bytes = os.path.getsize(clean_path)
            sz_str = _format_size(sz_bytes)
        except Exception:
            sz_str = ""

        # Update DropZone text
        self.drop_zone.set_file_loaded(name, sz_str)

        # Update Selected File Label with bright cyan highlight
        display_text = f"Selected: {name}  [{sz_str}]" if sz_str else f"Selected: {name}"
        self.file_lbl.setText(display_text)
        self.file_lbl.setStyleSheet("""
            QLabel {
                color: #00f3ff;
                font-size: 12px;
                font-weight: 800;
                padding: 10px 14px;
                background: #0b1525;
                border-radius: 8px;
                border: 2px solid #38bdf8;
            }
        """)

        # Enable & Apply Bright Light Blue Highlight to EXTRACT Button
        self.extract_btn.setEnabled(True)
        self._apply_extract_btn_style(enabled=True)
        self.extract_btn.setFocus()
        self.extract_btn.setDefault(True)
        
    def _browse_file(self):
        ext_filter = ""
        if self._accepted_exts:
            ext_str = " ".join(f"*{e}" for e in self._accepted_exts)
            ext_filter = f"Supported Files ({ext_str});;All Files (*)"
        else:
            ext_filter = "All Files (*)"
            
        start_dir = getattr(self, "_initial_dir", "") or (os.path.dirname(self._initial_file) if getattr(self, "_initial_file", None) else "") or ""
        path, _ = QFileDialog.getOpenFileName(self, "Select File", start_dir, ext_filter)
        if path:
            self._on_file_received(path)

    # Window-level drag and drop support
    def dragEnterEvent(self, event: QDragEnterEvent):
        path = self.drop_zone._extract_file_path(event.mimeData())
        if path and (not self._accepted_exts or any(path.lower().endswith(e) for e in self._accepted_exts)):
            event.acceptProposedAction()
            return
        event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent):
        path = self.drop_zone._extract_file_path(event.mimeData())
        if path and (not self._accepted_exts or any(path.lower().endswith(e) for e in self._accepted_exts)):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        path = self.drop_zone._extract_file_path(event.mimeData())
        if path and (not self._accepted_exts or any(path.lower().endswith(e) for e in self._accepted_exts)):
            event.acceptProposedAction()
            self._on_file_received(path)
            
    # Allow dragging the window by clicking the card background
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, '_drag_pos'):
            self.move(event.globalPosition().toPoint() - self._drag_pos)
