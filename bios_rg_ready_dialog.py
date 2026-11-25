"""
bios_rg_ready_dialog.py
======================
A modern, glossy drag-and-drop popup dialog for 'BIOS RG READY' direct region replacement.
Features:
- Displays target BIOS Region size from loaded backup dump.
- DropZone for ready donor BIOS Region (.bin, .rom, .fd, .cap, etc.).
- Live byte-for-byte size comparison & status banner.
- Real-time validation: 'REPLACE' button is enabled ONLY when donor size matches 100% byte-for-byte.
- Cancel and Replace action buttons.
"""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QGraphicsDropShadowEffect, QSizePolicy, QFileDialog, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import (
    QDragEnterEvent, QDragMoveEvent, QDropEvent, QColor, QFont,
    QPainter, QPen, QBrush, QPainterPath, QLinearGradient
)
from extractor_dialog import CloseCrossButton, _format_size


class ReadyDropZone(QLabel):
    """Glossy animated drag-and-drop zone specifically styled for BIOS RG READY."""
    
    file_dropped = Signal(str)
    clicked_browse = Signal()
    
    def __init__(self, accepted_exts=None, parent=None):
        super().__init__(parent)
        self._accepted_exts = accepted_exts or [".bin", ".rom", ".fd", ".cap", ".wph"]
        self._is_hovering_drag = False
        self._is_hovering_mouse = False
        self._is_loaded = False
        
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(170)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.reset_text()
        
    def reset_text(self):
        self._is_loaded = False
        ext_hint = " / ".join(f"*.{e.lstrip('.')}" for e in self._accepted_exts)
        self.setText(
            f"<div style='text-align:center; line-height:1.9;'>"
            f"<span style='font-size:15px; font-weight:900; letter-spacing:1.8px; color:#00f3ff;'>DROP DONOR BIOS REGION HERE</span><br>"
            f"<span style='font-size:12px; color:#94a3b8; margin-top:4px; display:block;'>or click anywhere in this box to browse</span><br>"
            f"<span style='font-size:10px; color:#64748b;'>Supported: {ext_hint}</span>"
            f"</div>"
        )
        self.update()

    def set_file_loaded(self, filename: str, size_bytes: int):
        self._is_loaded = True
        sz_text = _format_size(size_bytes)
        self.setText(
            f"<div style='text-align:center; line-height:1.9;'>"
            f"<span style='font-size:14px; font-weight:900; letter-spacing:1.5px; color:#38bdf8;'>DONOR FILE SELECTED</span><br>"
            f"<span style='font-size:13px; font-weight:700; color:#f1f5f9;'>{filename}</span><br>"
            f"<span style='font-size:11px; color:#94a3b8;'>Size: {size_bytes:,} bytes ({sz_text})</span><br>"
            f"<span style='font-size:10px; color:#64748b; margin-top:4px; display:block;'>Click or drop another file to change</span>"
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
        
        grad = QLinearGradient(0, 0, 0, rect.height())
        if self._is_hovering_drag:
            grad.setColorAt(0, QColor(0, 200, 255, 60))
            grad.setColorAt(1, QColor(0, 100, 180, 30))
            border_color = QColor(0, 243, 255, 230)
            border_width = 2.5
        elif self._is_loaded:
            grad.setColorAt(0, QColor(14, 165, 233, 30))
            grad.setColorAt(1, QColor(10, 20, 35, 120))
            border_color = QColor(56, 189, 248, 190)
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
        painter.fillPath(path, QBrush(grad))
        
        pen = QPen(border_color, border_width, Qt.PenStyle.DashLine)
        pen.setDashPattern([6, 4])
        painter.setPen(pen)
        painter.drawPath(path)
        
        gloss = QPainterPath()
        gloss.addRoundedRect(rect.adjusted(8, 8, -8, rect.height() // 2 * -1), radius - 4, radius - 4)
        painter.fillPath(gloss, QBrush(QColor(255, 255, 255, 15)))
        painter.end()
        
        super().paintEvent(event)


class BiosRgReadyDialog(QDialog):
    """
    Custom pop-up dialog for BIOS RG READY:
    - Drag & drop or browse donor BIOS Region file.
    - Real-time byte size comparison against backup dump's target BIOS Region.
    - Status message showing 100% size match.
    - Cancel and Replace action buttons.
    """

    def __init__(self, backup_file_path: str, target_size: int, parent=None):
        super().__init__(parent)
        self.backup_file_path = backup_file_path or ""
        self.target_size = target_size or 0
        self.selected_file = None
        self.donor_size = 0
        self.is_matched = False

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setMinimumSize(540, 480)
        self.setAcceptDrops(True)

        self._setup_ui()
        self._apply_shadow()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)

        card = QWidget()
        card.setObjectName("ReadyCard")
        card.setStyleSheet("""
            QWidget#ReadyCard {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #161928,
                    stop:0.4 #0f1120,
                    stop:1 #090b14);
                border-radius: 20px;
                border: 1px solid #1f2840;
            }
        """)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(26, 22, 26, 22)
        card_layout.setSpacing(12)

        # ── HEADER ──
        header = QHBoxLayout()
        icon_title = QVBoxLayout()
        icon_title.setSpacing(3)

        title_lbl = QLabel("BIOS RG READY")
        title_lbl.setStyleSheet("""
            color: #00f3ff;
            font-size: 17px;
            font-weight: 800;
            letter-spacing: 1.5px;
            font-family: 'Segoe UI', sans-serif;
        """)
        icon_title.addWidget(title_lbl)

        sub_lbl = QLabel("Direct 1:1 Replacement for Ready Donor BIOS Region (No Cutting / No Slicing)")
        sub_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        icon_title.addWidget(sub_lbl)
        header.addLayout(icon_title)

        close_btn = CloseCrossButton(self)
        close_btn.clicked.connect(self.reject)
        header.addWidget(close_btn, 0, Qt.AlignmentFlag.AlignTop)
        card_layout.addLayout(header)

        # Divider
        div1 = QWidget()
        div1.setFixedHeight(1)
        div1.setStyleSheet("background: #1f2840;")
        card_layout.addWidget(div1)

        # ── TARGET BIOS REGION INFO BANNER ──
        target_card = QFrame()
        target_card.setStyleSheet("""
            QFrame {
                background: #0d1222;
                border: 1px solid #233050;
                border-radius: 10px;
                padding: 6px 12px;
            }
        """)
        t_lay = QVBoxLayout(target_card)
        t_lay.setContentsMargins(8, 6, 8, 6)
        t_lay.setSpacing(4)

        backup_fname = os.path.basename(self.backup_file_path) if self.backup_file_path else "No Backup Loaded"
        target_sz_str = _format_size(self.target_size)
        
        info_row1 = QLabel(f"<b>Backup File:</b> <span style='color:#e2e8f0;'>{backup_fname}</span>")
        info_row1.setStyleSheet("color: #94a3b8; font-size: 11px;")
        t_lay.addWidget(info_row1)

        info_row2 = QLabel(f"<b>Required BIOS Region Size:</b> <span style='color:#00f3ff; font-weight:800;'>{self.target_size:,} bytes</span> <span style='color:#38bdf8;'>({target_sz_str})</span>")
        info_row2.setStyleSheet("color: #94a3b8; font-size: 12px;")
        t_lay.addWidget(info_row2)

        card_layout.addWidget(target_card)

        # ── DROP ZONE ──
        self.drop_zone = ReadyDropZone(parent=self)
        self.drop_zone.file_dropped.connect(self._on_file_selected)
        self.drop_zone.clicked_browse.connect(self._browse_file)
        card_layout.addWidget(self.drop_zone)

        # ── LIVE STATUS / COMPARISON MESSAGE BOX ──
        self.status_box = QFrame()
        self.status_box.setStyleSheet("""
            QFrame {
                background: #0a0c18;
                border: 1px solid #1a1e30;
                border-radius: 10px;
                padding: 8px 12px;
            }
        """)
        self.status_lay = QVBoxLayout(self.status_box)
        self.status_lay.setContentsMargins(10, 8, 10, 8)
        self.status_lay.setSpacing(3)

        self.status_title = QLabel("Waiting for donor file...")
        self.status_title.setStyleSheet("color: #64748b; font-size: 12px; font-weight: 700;")
        self.status_lay.addWidget(self.status_title)

        self.status_desc = QLabel("Please drag and drop or browse your ready donor BIOS Region file above.")
        self.status_desc.setStyleSheet("color: #475569; font-size: 11px;")
        self.status_desc.setWordWrap(True)
        self.status_lay.addWidget(self.status_desc)

        card_layout.addWidget(self.status_box)

        # ── BOTTOM ACTION BUTTONS ──
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
                padding: 0 24px;
            }
            QPushButton:hover {
                background: #334155;
                color: #ffffff;
            }
        """)
        cancel_btn.clicked.connect(self.reject)

        self.replace_btn = QPushButton("REPLACE")
        self.replace_btn.setFixedHeight(42)
        self.replace_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.replace_btn.setEnabled(False)
        self._apply_replace_btn_style(enabled=False)
        self.replace_btn.clicked.connect(self._on_replace_clicked)

        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.replace_btn)
        card_layout.addLayout(btn_row)

        outer.addWidget(card)

    def _apply_shadow(self):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 200, 255, 75))
        shadow.setOffset(0, 0)
        self.setGraphicsEffect(shadow)

    def _apply_replace_btn_style(self, enabled=False):
        if enabled:
            self.replace_btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #00f3ff,
                        stop:0.5 #0284c7,
                        stop:1 #00f3ff);
                    color: #030712;
                    border: none;
                    border-radius: 8px;
                    font-size: 13px;
                    font-weight: 900;
                    letter-spacing: 1.5px;
                    padding: 0 32px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #38bdf8,
                        stop:0.5 #0ea5e9,
                        stop:1 #38bdf8);
                    color: #000000;
                }
                QPushButton:pressed {
                    background: #0284c7;
                }
            """)
        else:
            self.replace_btn.setStyleSheet("""
                QPushButton {
                    background: #151c2e;
                    color: #475569;
                    border: 1px solid #1e2840;
                    border-radius: 8px;
                    font-size: 13px;
                    font-weight: 800;
                    letter-spacing: 1.5px;
                    padding: 0 32px;
                }
            """)

    def _browse_file(self):
        init_dir = os.path.dirname(self.backup_file_path) if self.backup_file_path else os.getcwd()
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Ready Donor BIOS Region", init_dir,
            "BIOS Region Binaries (*.bin *.rom *.fd *.cap *.wph);;All Files (*)"
        )
        if path:
            self._on_file_selected(path)

    def _on_file_selected(self, file_path: str):
        if not file_path or not os.path.exists(file_path):
            return

        self.selected_file = file_path
        self.donor_size = os.path.getsize(file_path)
        fname = os.path.basename(file_path)

        # Update drop zone
        self.drop_zone.set_file_loaded(fname, self.donor_size)

        # Live Size Comparison
        if self.donor_size == self.target_size:
            self.is_matched = True
            self.status_box.setStyleSheet("""
                QFrame {
                    background: #032b20;
                    border: 1.5px solid #10b981;
                    border-radius: 10px;
                    padding: 8px 12px;
                }
            """)
            self.status_title.setText("[MATCHED] SIZE 100% MATCHED!")
            self.status_title.setStyleSheet("color: #10b981; font-size: 13px; font-weight: 900; letter-spacing: 0.5px;")

            donor_sz_fmt = _format_size(self.donor_size)
            self.status_desc.setText(
                f"Selected Donor: <b>{fname}</b> ({self.donor_size:,} bytes | {donor_sz_fmt})<br>"
                f"<span style='color:#34d399;'>Exact byte-for-byte match verified! File will be automatically renamed to match backup decompiled partition.</span>"
            )
            self.status_desc.setStyleSheet("color: #e2e8f0; font-size: 11px;")
            self.replace_btn.setEnabled(True)
            self._apply_replace_btn_style(enabled=True)
        else:
            self.is_matched = False
            diff = self.donor_size - self.target_size
            diff_str = f"+{diff:,}" if diff > 0 else f"{diff:,}"
            self.status_box.setStyleSheet("""
                QFrame {
                    background: #2b0b0b;
                    border: 1.5px solid #ef4444;
                    border-radius: 10px;
                    padding: 8px 12px;
                }
            """)
            self.status_title.setText("[MISMATCH] FILE SIZE DOES NOT MATCH TARGET!")
            self.status_title.setStyleSheet("color: #ef4444; font-size: 13px; font-weight: 900; letter-spacing: 0.5px;")

            donor_sz_fmt = _format_size(self.donor_size)
            target_sz_fmt = _format_size(self.target_size)
            self.status_desc.setText(
                f"Selected Donor Size: <b>{self.donor_size:,} bytes</b> ({donor_sz_fmt})<br>"
                f"Target Region Size: <b>{self.target_size:,} bytes</b> ({target_sz_fmt})<br>"
                f"<span style='color:#f87171;'>Difference: {diff_str} bytes. Direct replacement requires an exact byte match!</span>"
            )
            self.status_desc.setStyleSheet("color: #e2e8f0; font-size: 11px;")
            self.replace_btn.setEnabled(False)
            self._apply_replace_btn_style(enabled=False)

    def _on_replace_clicked(self):
        if not self.selected_file or not self.is_matched:
            return
        self.accept()
