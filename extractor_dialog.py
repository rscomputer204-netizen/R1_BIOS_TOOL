"""
extractor_dialog.py
====================
A reusable, glossy drag-and-drop file selection popup dialog.
Used by both Universal Extractor and Dell PFS Extractor buttons.
"""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QGraphicsDropShadowEffect, QSizePolicy
)
from PySide6.QtCore import Qt, QMimeData, Signal, QPropertyAnimation, QEasingCurve, QRect
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QColor, QFont, QPainter, QPen, QBrush, QPainterPath, QLinearGradient


class DropZone(QLabel):
    """A glossy, animated drag-and-drop zone widget."""
    
    file_dropped = Signal(str)
    clicked_browse = Signal()
    
    def __init__(self, accepted_exts=None, parent=None):
        super().__init__(parent)
        self._accepted_exts = accepted_exts or []
        self._is_hovering_drag = False
        self._is_hovering_mouse = False
        
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._update_text()
        
    def _update_text(self):
        ext_hint = " / ".join(f"*.{e.lstrip('.')}" for e in self._accepted_exts) if self._accepted_exts else "Any file"
        self.setText(
            f"<div style='text-align:center; line-height:1.8;'>"
            f"<span style='font-size:38px;'>📂</span><br>"
            f"<span style='font-size:14px; font-weight:900; letter-spacing:2px; color:#00f3ff;'>DROP FILE HERE</span><br>"
            f"<span style='font-size:11px; color:#888; margin-top:6px; display:block;'>or click to browse</span><br>"
            f"<span style='font-size:10px; color:#555;'>{ext_hint}</span>"
            f"</div>"
        )
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                path = urls[0].toLocalFile()
                if not self._accepted_exts or any(path.lower().endswith(e) for e in self._accepted_exts):
                    self._is_hovering_drag = True
                    self.update()
                    event.acceptProposedAction()
                    return
        event.ignore()
        
    def dragLeaveEvent(self, event):
        self._is_hovering_drag = False
        self.update()
        
    def dropEvent(self, event: QDropEvent):
        self._is_hovering_drag = False
        self.update()
        urls = event.mimeData().urls()
        if urls:
            self.file_dropped.emit(urls[0].toLocalFile())
            
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


class ExtractorDropDialog(QDialog):
    """
    A glossy, reusable drag-and-drop popup for file extraction operations.
    
    Usage:
        dialog = ExtractorDropDialog(
            title="Universal Extractor",
            subtitle="Drop any installer or BIOS executable to extract",
            accepted_exts=[".exe", ".bin", ".rom"],
            parent=self
        )
        result = dialog.exec()
        if result == QDialog.Accepted:
            filepath = dialog.selected_file
    """
    
    def __init__(self, title="File Extractor", subtitle="", accepted_exts=None, parent=None):
        super().__init__(parent)
        self.selected_file = None
        self._title = title
        self._subtitle = subtitle
        self._accepted_exts = accepted_exts or []
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setMinimumSize(480, 380)
        
        self._setup_ui()
        self._apply_shadow()
        
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
        card_layout.setSpacing(16)
        
        # ── HEADER ──
        header = QHBoxLayout()
        
        # Icon + Title
        icon_title = QVBoxLayout()
        
        title_row = QHBoxLayout()
        icon_lbl = QLabel("⚡")
        icon_lbl.setStyleSheet("font-size: 22px;")
        title_lbl = QLabel(self._title)
        title_lbl.setStyleSheet("""
            color: #00f3ff;
            font-size: 17px;
            font-weight: 900;
            letter-spacing: 2px;
            font-family: 'Segoe UI', 'Orbitron', sans-serif;
        """)
        title_row.addWidget(icon_lbl)
        title_row.addWidget(title_lbl)
        title_row.addStretch()
        icon_title.addLayout(title_row)
        
        if self._subtitle:
            sub_lbl = QLabel(self._subtitle)
            sub_lbl.setStyleSheet("color: #556; font-size: 11px; margin-left: 4px;")
            sub_lbl.setWordWrap(True)
            icon_title.addWidget(sub_lbl)
            
        header.addLayout(icon_title)
        
        # Close button
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #445;
                border: none;
                font-size: 16px;
                border-radius: 15px;
            }
            QPushButton:hover {
                background: #ff4444;
                color: #fff;
            }
        """)
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
        self.file_lbl.setStyleSheet("""
            color: #445;
            font-size: 11px;
            padding: 6px 10px;
            background: #0a0c18;
            border-radius: 8px;
            border: 1px solid #1a1e30;
        """)
        self.file_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.file_lbl.setWordWrap(True)
        card_layout.addWidget(self.file_lbl)
        
        # ── BOTTOM BUTTONS ──
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        
        cancel_btn = QPushButton("CANCEL")
        cancel_btn.setFixedHeight(38)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #445;
                border: 1px solid #1f2840;
                border-radius: 8px;
                font-size: 12px;
                font-weight: bold;
                letter-spacing: 1px;
                padding: 0 20px;
            }
            QPushButton:hover {
                border-color: #ff4444;
                color: #ff4444;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        self.extract_btn = QPushButton("▶  EXTRACT")
        self.extract_btn.setFixedHeight(38)
        self.extract_btn.setEnabled(False)
        self.extract_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0066aa, stop:1 #00aadd);
                color: #000;
                border: none;
                border-radius: 8px;
                font-size: 12px;
                font-weight: 900;
                letter-spacing: 1.5px;
                padding: 0 24px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00aafff, stop:1 #00f3ff);
                color: #000;
            }
            QPushButton:disabled {
                background: #1a1e30;
                color: #334;
            }
        """)
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
        
    def _on_file_received(self, path: str):
        self.selected_file = path
        name = os.path.basename(path)
        self.file_lbl.setText(f"✅  {name}")
        self.file_lbl.setStyleSheet("""
            color: #00f3ff;
            font-size: 11px;
            padding: 6px 10px;
            background: #0a1525;
            border-radius: 8px;
            border: 1px solid #00f3ff44;
        """)
        self.extract_btn.setEnabled(True)
        
    def _browse_file(self):
        from PySide6.QtWidgets import QFileDialog
        
        ext_filter = ""
        if self._accepted_exts:
            ext_str = " ".join(f"*{e}" for e in self._accepted_exts)
            ext_filter = f"Supported Files ({ext_str});;All Files (*)"
        else:
            ext_filter = "All Files (*)"
            
        path, _ = QFileDialog.getOpenFileName(self, "Select File", "", ext_filter)
        if path:
            self._on_file_received(path)
            
    # Allow dragging the window by clicking the card background
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, '_drag_pos'):
            self.move(event.globalPosition().toPoint() - self._drag_pos)
