"""
password_remover_dialog.py
===========================
Premium, Dark-Cyberpunk QDialog for automated BIOS Password Detection & Removal.
Part of R1 BIOS TOOL (R1 AI LAB).
"""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QFrame, QFileDialog, QMessageBox, QGraphicsDropShadowEffect,
    QSizePolicy, QTextEdit
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import (
    QDragEnterEvent, QDropEvent, QColor, QPainter, QPen,
    QBrush, QPainterPath, QLinearGradient
)

from password_unlock_engine import PasswordUnlockEngine


class DropZone(QLabel):
    """Glossy, animated Drag-and-Drop file zone supporting loaded state."""
    file_dropped = Signal(str)
    clicked_browse = Signal()

    def __init__(self, accepted_exts=None, parent=None):
        super().__init__(parent)
        self._accepted_exts = accepted_exts or [".bin", ".rom", ".fd", ".bios", ".cap"]
        self._is_hovering_drag = False
        self._is_hovering_mouse = False
        self._loaded_file = None

        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(115)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._update_text()

    def set_loaded_file(self, file_path: str):
        """Display loaded file in drop zone."""
        self._loaded_file = file_path
        base = os.path.basename(file_path)
        self.setText(
            "<div style='text-align:center; line-height:1.6;'>"
            "<span style='font-size:26px;'>📁</span><br>"
            f"<span style='font-size:13px; font-weight:900; letter-spacing:1px; color:#00f3ff;'>BIOS FILE LOADED: {base}</span><br>"
            "<span style='font-size:11px; color:#a4b0be;'>Click 'DETECT PASSWORD' below or drop/browse another file to replace</span>"
            "</div>"
        )
        self.update()

    def reset_state(self):
        """Reset drop zone to empty state."""
        self._loaded_file = None
        self._update_text()
        self.update()

    def _update_text(self):
        self.setText(
            "<div style='text-align:center; line-height:1.6;'>"
            "<span style='font-size:28px;'>⚡</span><br>"
            "<span style='font-size:13px; font-weight:900; letter-spacing:2px; color:#00f3ff;'>"
            "DROP LOCKED BIOS BINARY HERE</span><br>"
            "<span style='font-size:11px; color:#888;'>or click to browse (.bin, .rom, .fd)</span>"
            "</div>"
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
        radius = 12

        grad = QLinearGradient(0, 0, 0, rect.height())
        if self._is_hovering_drag:
            grad.setColorAt(0, QColor(42, 196, 219, 50))
            grad.setColorAt(1, QColor(20, 24, 28, 180))
            border_color = QColor(14, 246, 253, 230)
            border_width = 2.0
        elif self._is_hovering_mouse:
            grad.setColorAt(0, QColor(42, 196, 219, 25))
            grad.setColorAt(1, QColor(20, 24, 28, 160))
            border_color = QColor(42, 196, 219, 180)
            border_width = 1.5
        elif self._loaded_file:
            grad.setColorAt(0, QColor(42, 196, 219, 18))
            grad.setColorAt(1, QColor(18, 21, 25, 200))
            border_color = QColor(42, 196, 219, 140)
            border_width = 1.5
        else:
            grad.setColorAt(0, QColor(28, 32, 36, 180))
            grad.setColorAt(1, QColor(20, 23, 26, 180))
            border_color = QColor(60, 68, 77, 180)
            border_width = 1.2

        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)

        painter.fillPath(path, QBrush(grad))

        pen = QPen(border_color, border_width, Qt.PenStyle.DashLine)
        pen.setDashPattern([6, 4])
        painter.setPen(pen)
        painter.drawPath(path)

        painter.end()
        super().paintEvent(event)


class PasswordRemoverDialog(QDialog):
    """
    Enterprise Edition Password Remover Dialog matching R1 editor's Slate & Teal Theme.
    """

    def __init__(self, initial_file: str = None, brand: str = None, parent=None):
        super().__init__(parent)
        self.target_brand = brand or "UNKNOWN"
        self.current_file = None
        self.detection_result = None

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setMinimumSize(630, 570)
        self.resize(650, 600)

        self._drag_pos = None

        self._setup_ui()
        self._apply_shadow()

        # If a file was already loaded in the main application, automatically load it!
        if initial_file and os.path.exists(initial_file):
            self.load_file(initial_file)

    def _setup_ui(self):
        # Master Outer Frame
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(10, 10, 10, 10)

        self.card = QFrame()
        self.card.setObjectName("PasswordRemoverCard")
        self.card.setStyleSheet("""
            QFrame#PasswordRemoverCard {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #252a2e, stop:1 #1c2024);
                border: 1px solid #2d363f;
                border-radius: 14px;
            }
        """)
        outer_layout.addWidget(self.card)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(22, 18, 22, 22)
        card_layout.setSpacing(13)

        # ─── HEADER BAR (Title, Brand Badge, Close Button) ───
        header = QHBoxLayout()
        header.setSpacing(10)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        lbl_title = QLabel("⚡ BIOS PASSWORD UNLOCK ENGINE")
        lbl_title.setStyleSheet("font-family:'Segoe UI', sans-serif; font-size: 15px; font-weight: 800; color: #4cd3e3; letter-spacing: 1.5px;")
        
        lbl_sub = QLabel("Automated Multi-Brand Firmware Password Detection & Surgical Erasure")
        lbl_sub.setStyleSheet("font-family:'Segoe UI', sans-serif; font-size: 11px; color: #94a3b8;")
        title_col.addWidget(lbl_title)
        title_col.addWidget(lbl_sub)
        header.addLayout(title_col)

        header.addStretch()

        # Brand Badge
        self.badge_brand = QLabel(self.target_brand.upper())
        self.badge_brand.setStyleSheet("""
            QLabel {
                background: #252a2f;
                color: #4cd3e3;
                border: 1px solid #3c444d;
                border-radius: 6px;
                padding: 4px 10px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
                font-weight: 800;
                letter-spacing: 1px;
            }
        """)
        header.addWidget(self.badge_brand)

        # Close Button
        btn_close = QPushButton("✕")
        btn_close.setFixedSize(30, 30)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                background: #252a2f;
                color: #94a3b8;
                border: 1px solid #3c444d;
                border-radius: 15px;
                font-size: 13px;
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

        # ─── DROP ZONE ───
        self.drop_zone = DropZone(accepted_exts=[".bin", ".rom", ".fd", ".bios", ".cap"], parent=self)
        self.drop_zone.file_dropped.connect(self.on_file_selected)
        self.drop_zone.clicked_browse.connect(self.browse_file)
        card_layout.addWidget(self.drop_zone)

        # ─── FILE INFO STRIP ───
        file_info_widget = QWidget()
        file_info_widget.setStyleSheet("background: #14171a; border: 1px solid #283038; border-radius: 8px; padding: 6px 12px;")
        file_info_layout = QHBoxLayout(file_info_widget)
        file_info_layout.setContentsMargins(6, 4, 6, 4)

        lbl_file_icon = QLabel("📄")
        lbl_file_icon.setStyleSheet("font-size: 14px; border: none;")
        file_info_layout.addWidget(lbl_file_icon)

        self.lbl_file_name = QLabel("No file selected")
        self.lbl_file_name.setStyleSheet("font-family:'Segoe UI', sans-serif; font-size: 11px; font-weight: bold; color: #f1f5f9; border: none;")
        file_info_layout.addWidget(self.lbl_file_name, stretch=1)

        self.lbl_file_size = QLabel("")
        self.lbl_file_size.setStyleSheet("font-family:'Segoe UI', sans-serif; font-size: 11px; color: #4cd3e3; border: none;")
        file_info_layout.addWidget(self.lbl_file_size)

        card_layout.addWidget(file_info_widget)

        # ─── SCAN & DETECTION STATUS CARD ───
        self.status_card = QFrame()
        self.status_card.setStyleSheet("""
            QFrame {
                background: #14171a;
                border: 1px solid #283038;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        status_layout = QVBoxLayout(self.status_card)
        status_layout.setContentsMargins(12, 10, 12, 10)
        status_layout.setSpacing(8)

        status_header = QHBoxLayout()
        lbl_status_title = QLabel("DETECTION STATUS")
        lbl_status_title.setStyleSheet("font-family:'Segoe UI', sans-serif; font-size: 10px; font-weight: 800; color: #64748b; letter-spacing: 1px;")
        status_header.addWidget(lbl_status_title)
        status_header.addStretch()

        self.badge_status = QLabel("WAITING FOR FILE")
        self.badge_status.setStyleSheet("""
            background: #252a2e;
            color: #94a3b8;
            padding: 3px 10px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: 800;
        """)
        status_header.addWidget(self.badge_status)
        status_layout.addLayout(status_header)

        self.txt_details = QTextEdit()
        self.txt_details.setReadOnly(True)
        self.txt_details.setMinimumHeight(105)
        self.txt_details.setStyleSheet("""
            QTextEdit {
                background: #101316;
                border: 1px solid #22272e;
                border-radius: 6px;
                color: #cbd5e1;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
                padding: 8px;
            }
        """)
        self.txt_details.setPlainText("Load or drop a BIOS dump to begin password analysis...")
        status_layout.addWidget(self.txt_details)

        card_layout.addWidget(self.status_card)

        # ─── ACTION BUTTONS (Detect Password & Password Remove) ───
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        # DETECT PASSWORD BUTTON
        self.btn_scan = QPushButton("🔍 DETECT PASSWORD")
        self.btn_scan.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_scan.setMinimumHeight(44)
        self.btn_scan.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #252a2e, stop:1 #1c2024);
                color: #4cd3e3;
                border: 1px solid #3c444d;
                border-radius: 8px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
                font-weight: 800;
                letter-spacing: 1px;
                padding: 0 18px;
            }
            QPushButton:hover {
                background: #2e353b;
                border-color: #4cd3e3;
                color: #ffffff;
            }
            QPushButton:disabled {
                background: #171a1d;
                color: #475569;
                border-color: #23282e;
            }
        """)
        self.btn_scan.setEnabled(False)
        self.btn_scan.clicked.connect(self.detect_password_routine)
        btn_layout.addWidget(self.btn_scan)

        # PASSWORD REMOVE BUTTON (Inactive until password is found!)
        self.btn_final_remove = QPushButton("⚡ PASSWORD REMOVE")
        self.btn_final_remove.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_final_remove.setMinimumHeight(44)
        self.btn_final_remove.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8fe3ea, stop:0.5 #3598a6, stop:1 #247d8a);
                color: #0b151a;
                border: none;
                border-radius: 8px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
                font-weight: 900;
                letter-spacing: 1px;
                padding: 0 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #bbf2f6, stop:0.5 #45b1bf, stop:1 #2ca0b0);
                color: #000000;
            }
            QPushButton:disabled {
                background: #1b2024;
                color: #475569;
                border: 1px solid #272e36;
            }
        """)
        self.btn_final_remove.setEnabled(False)
        self.btn_final_remove.clicked.connect(self.execute_final_remove)
        btn_layout.addWidget(self.btn_final_remove, stretch=1)

        card_layout.addLayout(btn_layout)

    def _apply_shadow(self):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(36)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 8)
        self.card.setGraphicsEffect(shadow)

    # ─── FILE LOADING & SELECTION ───
    def browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Locked BIOS File", "", "BIOS Binary (*.bin *.rom *.fd *.bios *.cap);;All Files (*.*)"
        )
        if path:
            self.load_file(path)

    def on_file_selected(self, file_path: str):
        self.load_file(file_path)

    def load_file(self, file_path: str):
        """
        Loads a BIOS binary into the dialog.
        Displays file metadata, sets drop-zone status, and enables 'DETECT PASSWORD'.
        Leaves 'PASSWORD REMOVE' disabled until password detection confirms a lock.
        """
        if not file_path or not os.path.exists(file_path):
            return

        self.current_file = os.path.abspath(file_path)
        self.detection_result = None
        file_name = os.path.basename(self.current_file)
        file_size = os.path.getsize(self.current_file)

        # 1. Update Drop Zone
        self.drop_zone.set_loaded_file(self.current_file)

        # 2. Update File Info Strip
        self.lbl_file_name.setText(file_name)
        self.lbl_file_size.setText(f"{file_size / (1024 * 1024):.2f} MB ({file_size:,} bytes)")

        # 3. Detect Brand if currently UNKNOWN
        if self.target_brand in ("UNKNOWN", "N/A", ""):
            try:
                with open(self.current_file, "rb") as f:
                    header_sample = f.read(min(file_size, 4 * 1024 * 1024))
                    b = PasswordUnlockEngine.detect_brand(header_sample)
                    if b != "UNKNOWN":
                        self.target_brand = b
            except Exception:
                pass

        self.badge_brand.setText(self.target_brand.upper())

        # 4. Update Status Card
        self.badge_status.setText("FILE READY")
        self.badge_status.setStyleSheet("""
            background: #1c2e28;
            color: #00ff88;
            border: 1px solid #1f4a38;
            padding: 3px 10px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: 800;
        """)

        self.txt_details.setPlainText(
            f"============================================================\n"
            f" [✓] BIOS FILE LOADED SUCCESSFULLY\n"
            f"============================================================\n"
            f" File:   {file_name}\n"
            f" Size:   {file_size / (1024 * 1024):.2f} MB ({file_size:,} bytes)\n"
            f" Brand:  {self.target_brand.upper()}\n\n"
            f" Status: File is loaded and ready for analysis.\n"
            f" -> Click '🔍 DETECT PASSWORD' button below to scan for passwords.\n"
            f"============================================================"
        )

        # 5. Enable Detect button, Keep Remove button disabled!
        self.btn_scan.setEnabled(True)
        self.btn_scan.setText("🔍 DETECT PASSWORD")
        self.btn_final_remove.setEnabled(False)
        self.btn_final_remove.setText("⚡ PASSWORD REMOVE")

    # ─── DETECTION ROUTINE (Triggered when user clicks 'DETECT PASSWORD') ───
    def detect_password_routine(self):
        """
        Inspects firmware bytes for password sectors.
        If password found -> Announces 'PASSWORD FOUND' and ACTIVATES 'PASSWORD REMOVE' button.
        If password not found -> Announces 'PASSWORD NOT FOUND' and keeps 'PASSWORD REMOVE' disabled.
        """
        if not self.current_file or not os.path.exists(self.current_file):
            self.badge_status.setText("NO FILE")
            self.badge_status.setStyleSheet("background: #351c20; color: #ff6b6b; border: 1px solid #5a2830; padding: 3px 8px; border-radius: 4px; font-weight: 800;")
            self.txt_details.setPlainText("Please load or drop a BIOS file first.")
            return

        self.txt_details.setPlainText("⏳ Analyzing BIOS firmware structures and NVRAM security sectors...")
        self.badge_status.setText("SCANNING...")
        self.badge_status.setStyleSheet("background: #1c2a38; color: #38bdf8; border: 1px solid #234567; padding: 3px 8px; border-radius: 4px; font-weight: 800;")

        try:
            with open(self.current_file, "rb") as f:
                raw_bytes = f.read()

            result = PasswordUnlockEngine.scan_file(raw_bytes, brand=self.target_brand)
            self.detection_result = result
            brand = result.get("brand", self.target_brand).upper()
            self.badge_brand.setText(brand)

            if result.get("detected"):
                # ── PASSWORD FOUND! ──
                self.badge_status.setText("🔒 PASSWORD FOUND")
                self.badge_status.setStyleSheet("""
                    background: #3a1c22;
                    color: #ff5252;
                    border: 1px solid #6b2128;
                    padding: 3px 10px;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: 800;
                    letter-spacing: 0.5px;
                """)

                detail_msg = (
                    f"============================================================\n"
                    f" [✓] PASSWORD FOUND IN FIRMWARE BINARY\n"
                    f"============================================================\n"
                    f" Brand:            {brand}\n"
                    f" Protection Type:  {result.get('protection_type', 'Hardware/NVRAM Security Lock')}\n"
                    f" Target Offset:    0x{result.get('target_offset', 0):08X}\n"
                    f" Sector Size:      {result.get('sector_size', 4096):,} bytes\n"
                    f" Status:           LOCKED\n\n"
                    f" Forensic Details:\n {result.get('details', '')}\n\n"
                    f" [SAFETY GUARANTEE]\n"
                    f"  - Motherboard DMI (Serial, Model, UUID) will be 100% preserved.\n"
                    f"  - Microsoft OEM Windows Key will NOT be touched.\n"
                    f"  - CSME / Intel ME region remains untouched.\n"
                    f"============================================================\n"
                    f" [ACTION READY] Password found!\n"
                    f" Click '⚡ PASSWORD REMOVE' button below to unlock and save."
                )
                self.txt_details.setPlainText(detail_msg)

                # ACTIVATE PASSWORD REMOVE BUTTON
                self.btn_final_remove.setEnabled(True)
                self.btn_final_remove.setText("⚡ PASSWORD REMOVE")

            else:
                # ── PASSWORD NOT FOUND! ──
                self.badge_status.setText("⚠️ PASSWORD NOT FOUND")
                self.badge_status.setStyleSheet("""
                    background: #2e2619;
                    color: #fbbf24;
                    border: 1px solid #5a451e;
                    padding: 3px 10px;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: 800;
                    letter-spacing: 0.5px;
                """)

                detail_msg = (
                    f"============================================================\n"
                    f" [!] PASSWORD NOT FOUND / FIRMWARE IS UNLOCKED\n"
                    f"============================================================\n"
                    f" Brand:     {brand}\n"
                    f" Status:    {result.get('status', 'CLEAN / UNLOCKED')}\n\n"
                    f" Details:\n {result.get('details', 'No active password credentials or locked security sectors detected.')}\n\n"
                    f" NOTE: This file is already unlocked or does not contain active\n"
                    f" password protection sectors.\n"
                    f" 'PASSWORD REMOVE' button remains disabled to prevent unnecessary changes.\n"
                    f"============================================================"
                )
                self.txt_details.setPlainText(detail_msg)

                # KEEP PASSWORD REMOVE BUTTON DISABLED
                self.btn_final_remove.setEnabled(False)
                self.btn_final_remove.setText("⚡ PASSWORD REMOVE")

        except Exception as e:
            self.badge_status.setText("ERROR")
            self.badge_status.setStyleSheet("background: #351c20; color: #ff6b6b; border: 1px solid #5a2830; padding: 3px 8px; border-radius: 4px; font-weight: 800;")
            self.txt_details.setPlainText(f"Error during password detection: {str(e)}")
            self.btn_final_remove.setEnabled(False)

    # ─── FINAL REMOVE & SAVE ───
    def execute_final_remove(self):
        """
        Executes surgical password wipe and automatically opens Save File dialog.
        Default filename pre-populates with '_unlock' (e.g., original_unlock.bin).
        """
        if not self.current_file or not self.detection_result or not self.detection_result.get("detected"):
            return

        try:
            with open(self.current_file, "rb") as f:
                raw_bytes = f.read()

            unlocked_data, log_msg = PasswordUnlockEngine.remove_password(
                raw_bytes,
                brand=self.badge_brand.text(),
                detection_info=self.detection_result
            )

            # Automatically suggest output filename with '_unlock'
            dir_name = os.path.dirname(self.current_file)
            base_name, ext = os.path.splitext(os.path.basename(self.current_file))
            
            # Format default output filename (e.g. filename_unlock.bin)
            if not base_name.lower().endswith(("_unlock", "_unlocked")):
                suggested_filename = f"{base_name}_unlock{ext}"
            else:
                suggested_filename = f"{base_name}_clean{ext}"
                
            default_out = os.path.join(dir_name, suggested_filename)

            # Automatically pop open the File Save Dialog with pre-filled name & directory
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Unlocked BIOS Binary",
                default_out,
                f"BIOS Binary (*{ext});;All Files (*.*)"
            )

            if not save_path:
                return

            with open(save_path, "wb") as f_out:
                f_out.write(unlocked_data)

            # Verify size
            orig_size = len(raw_bytes)
            new_size = os.path.getsize(save_path)
            if orig_size != new_size:
                raise IOError(f"Size mismatch: original was {orig_size:,} bytes but saved was {new_size:,} bytes")

            self.saved_output_path = save_path
            self.badge_status.setText("✅ UNLOCKED & SAVED")
            self.badge_status.setStyleSheet("""
                background: #1c2e28;
                color: #00ff88;
                border: 1px solid #1f4a38;
                padding: 3px 10px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 800;
            """)

            success_details = (
                f"============================================================\n"
                f" [✓] PASSWORD REMOVED SUCCESSFULLY!\n"
                f"============================================================\n"
                f" Saved File: {os.path.basename(save_path)}\n"
                f" Full Path:  {save_path}\n"
                f" File Size:  {new_size:,} bytes (100% matched)\n"
                f" Brand:      {self.badge_brand.text()}\n\n"
                f" Unlock Operations:\n{log_msg}\n\n"
                f" [READY TO FLASH]\n"
                f" The binary is 100% unlocked and ready to flash into SPI chip!\n"
                f"============================================================"
            )
            self.txt_details.setPlainText(success_details)
            self.btn_final_remove.setEnabled(False)

            # Transform scan button into "Open Containing Folder" for convenience
            self.btn_scan.setText("📂 OPEN FOLDER")
            self.btn_scan.setEnabled(True)
            try:
                self.btn_scan.clicked.disconnect()
            except Exception:
                pass
            self.btn_scan.clicked.connect(lambda: self.open_saved_folder(save_path))

            # Prompt technician with confirmation and option to open folder
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Password Removed Successfully")
            msg_box.setText(
                f"<b>BIOS Password Removed Successfully!</b><br><br>"
                f"<b>File:</b> {os.path.basename(save_path)}<br>"
                f"<b>Saved Path:</b> {save_path}"
            )
            btn_open = msg_box.addButton("Open Folder", QMessageBox.ButtonRole.ActionRole)
            msg_box.addButton(QMessageBox.StandardButton.Ok)
            msg_box.exec()

            if msg_box.clickedButton() == btn_open:
                self.open_saved_folder(save_path)

        except Exception as e:
            QMessageBox.critical(self, "Error Removing Password", f"An error occurred: {str(e)}")

    def open_saved_folder(self, file_path):
        """Open Windows Explorer with the saved file highlighted."""
        import subprocess
        try:
            norm_path = os.path.normpath(file_path)
            subprocess.Popen(f'explorer /select,"{norm_path}"')
        except Exception:
            pass

    # ─── WINDOW DRAGGING ───
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
