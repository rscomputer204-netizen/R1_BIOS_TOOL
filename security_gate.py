"""
R1 BIOS Tool - Final Security Gate
====================================
Dual-layer security enforcement:
  Layer 1: Valid Activation Key (GitHub verified + HWID locked)
  Layer 2: R1 BIOS Programmer (FT232H hardware dongle)

Rules:
  - Software WILL NOT start or operate without at least ONE of these.
  - If NEITHER is present: show activation dialog, block all features.
  - If Activation Key is valid: programmer is optional.
  - If Programmer is connected: activation key is optional.
  - If both are valid: full access, maximum trust level.
  - Disconnect monitoring: if programmer disconnects AND no valid key, close immediately.
"""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QWidget, QApplication, QMessageBox,
    QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QTimer, QPoint, Signal
from PySide6.QtGui import QColor, QFont, QPixmap

# ─── Trust Levels ───────────────────────────────────────────────────────────
TRUST_NONE     = 0   # No key, no programmer → BLOCKED
TRUST_KEY_ONLY = 1   # Valid activation key only
TRUST_HW_ONLY  = 2   # Programmer connected only
TRUST_FULL     = 3   # Both valid → Maximum security


def compute_trust_level(has_valid_license: bool, has_programmer: bool) -> int:
    if has_valid_license and has_programmer:
        return TRUST_FULL
    elif has_valid_license:
        return TRUST_KEY_ONLY
    elif has_programmer:
        return TRUST_HW_ONLY
    else:
        return TRUST_NONE


# ─── Custom Title Bar ────────────────────────────────────────────────────────
class _TitleBar(QFrame):
    """Frameless window custom title bar with teal gradient and drag support."""

    def __init__(self, parent_dialog, title: str):
        super().__init__(parent_dialog)
        self._dialog = parent_dialog
        self._drag_pos = None
        self.setObjectName("_TitleBar")
        self.setFixedHeight(38)
        self.setStyleSheet("""
            QFrame#_TitleBar {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0ef6fd, stop:0.5 #06ecf8, stop:1 #00e0ed);
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                border-bottom: 1px solid rgba(0,0,0,0.15);
            }
            QLabel#_TitleText {
                color: #043040;
                font-family: Segoe UI, Arial, sans-serif;
                font-size: 13px;
                font-weight: 600;
                padding-left: 2px;
            }
            QPushButton {
                background: transparent;
                border: none;
                color: #043040;
                font-family: Segoe UI, Arial, sans-serif;
                font-size: 14px;
                font-weight: bold;
                min-width: 36px;
                max-width: 36px;
                min-height: 38px;
                max-height: 38px;
                border-radius: 0px;
            }
            QPushButton:hover { background-color: rgba(0,0,0,0.12); }
            QPushButton#_CloseBtn:hover {
                background-color: #e81123;
                color: #ffffff;
                border-top-right-radius: 10px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 0, 0)
        layout.setSpacing(6)

        # Shield icon in title bar
        self._icon_lbl = QLabel()
        from path_utils import get_resource_path
        pix = QPixmap(get_resource_path(os.path.join("assets", "shield_badge.png")))
        if not pix.isNull():
            self._icon_lbl.setPixmap(
                pix.scaled(20, 22, Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation))
        layout.addWidget(self._icon_lbl)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("_TitleText")
        layout.addWidget(title_lbl)
        layout.addStretch()

        self._min_btn = QPushButton("—")
        self._min_btn.clicked.connect(self._dialog.showMinimized)
        layout.addWidget(self._min_btn)

        self._max_btn = QPushButton("□")
        layout.addWidget(self._max_btn)

        self._close_btn = QPushButton("✕")
        self._close_btn.setObjectName("_CloseBtn")
        self._close_btn.clicked.connect(self._dialog._do_exit)
        layout.addWidget(self._close_btn)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint() - self._dialog.frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self._dialog.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None


# ─── Activation Dialog ───────────────────────────────────────────────────────
class ActivationDialog(QDialog):
    """
    Shown when neither programmer nor license key is available.
    Cannot be dismissed — user must activate or exit the application.
    Redesigned to match the R1 BIOS TOOL Enterprise reference UI.
    """
    activation_success = Signal(dict)

    def __init__(self, parent=None, programmer_connected=False):
        super().__init__(parent)
        self.programmer_connected = programmer_connected

        # ── Frameless, always-on-top, translucent for shadow ──
        self.setWindowTitle("R1 BIOS TOOL Enterprise Edition — License Activation")
        self.setModal(True)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(760, 600)

        self._build_ui()

    def showEvent(self, event):
        super().showEvent(event)
        self.raise_()
        self.activateWindow()

    # ── UI Construction ─────────────────────────────────────────────────────
    def _build_ui(self):
        from path_utils import get_resource_path

        # Outer layout — gives room for drop shadow
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)

        # ── Main container card ──
        card = QFrame()
        card.setObjectName("_Card")
        card.setStyleSheet("""
            QFrame#_Card {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #252a2e, stop:1 #1c2024);
                border: 1px solid #1a2026;
                border-radius: 10px;
            }
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(32)
        shadow.setColor(QColor(0, 0, 0, 200))
        shadow.setOffset(0, 10)
        card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # 1. Title Bar
        self._title_bar = _TitleBar(
            self,
            "R1 BIOS TOOL Enterprise Edition — License Activation"
        )
        card_layout.addWidget(self._title_bar)

        # 2. Content
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(44, 26, 44, 26)
        content_layout.setSpacing(14)

        # ── HERO: Shield + Titles ──
        hero = QHBoxLayout()
        hero.setSpacing(26)
        hero.setAlignment(Qt.AlignmentFlag.AlignCenter)

        shield_lbl = QLabel()
        pix = QPixmap(get_resource_path(os.path.join("assets", "shield_badge.png")))
        if not pix.isNull():
            shield_lbl.setPixmap(
                pix.scaled(112, 132, Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation))
        hero.addWidget(shield_lbl)

        titles = QVBoxLayout()
        titles.setSpacing(2)
        titles.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        lbl_t1 = QLabel("R1 BIOS TOOL")
        lbl_t1.setFont(QFont("Segoe UI", 26, QFont.Weight.Bold))
        lbl_t1.setStyleSheet("color: #ffffff; letter-spacing: 1px;")

        lbl_t2 = QLabel("Enterprise Edition")
        lbl_t2.setFont(QFont("Segoe UI", 16, QFont.Weight.Medium))
        lbl_t2.setStyleSheet("color: #c8d6e0;")

        lbl_t3 = QLabel("Advanced Hardware Security System")
        lbl_t3.setFont(QFont("Segoe UI", 10))
        lbl_t3.setStyleSheet("color: #7b8b9a; margin-top: 4px;")

        titles.addWidget(lbl_t1)
        titles.addWidget(lbl_t2)
        titles.addWidget(lbl_t3)
        hero.addLayout(titles)
        content_layout.addLayout(hero)
        content_layout.addSpacing(4)

        # ── Programmer status pill ──
        pill = QFrame()
        pill.setFixedHeight(44)
        pill.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3c444a, stop:1 #2d3338);
                border: 1px solid #4a535b;
                border-radius: 8px;
            }
        """)
        pill_layout = QHBoxLayout(pill)
        pill_layout.setContentsMargins(20, 0, 20, 0)
        pill_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if self.programmer_connected:
            prog_txt = "✅  R1 BIOS Programmer: [STATUS: Connected]"
        else:
            prog_txt = "⚠️  R1 BIOS Programmer: [STATUS: Not Detected]"

        prog_lbl = QLabel(prog_txt)
        prog_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        prog_lbl.setStyleSheet("color: #c8d6e0;")
        pill_layout.addWidget(prog_lbl)
        content_layout.addWidget(pill)

        # ── License status ──
        lock_lbl = QLabel(
            'License Status: <span style="color:#4cd3e3; font-weight:bold; '
            'letter-spacing:1px;">LOCKED</span>'
        )
        lock_lbl.setFont(QFont("Segoe UI", 12))
        lock_lbl.setStyleSheet("color: #94a3b8;")
        lock_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(lock_lbl)

        # ── Activation Key input ──
        key_label = QLabel("Enter Activation Key:")
        key_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        key_label.setStyleSheet("color: #94a3b8;")
        content_layout.addWidget(key_label)

        self.key_input = QLineEdit()
        self.key_input.setObjectName("key_input")
        self.key_input.setFixedHeight(50)
        self.key_input.setFont(QFont("Consolas", 13, QFont.Weight.DemiBold))
        self.key_input.setPlaceholderText("XXXXX - XXXXX - XXXXX - XXXXX - XXXXX")
        self.key_input.setMaxLength(35)
        self.key_input.setStyleSheet("""
            QLineEdit#key_input {
                background-color: #171a1d;
                border: 2px solid #2ac4db;
                border-radius: 9px;
                padding: 0px 16px;
                color: #c8d6e0;
                letter-spacing: 2px;
            }
            QLineEdit#key_input:focus {
                border: 2px solid #00f3ff;
            }
        """)
        self.key_input.textChanged.connect(self._on_key_changed)
        self.key_input.returnPressed.connect(self._do_activate)
        content_layout.addWidget(self.key_input)

        # Status / feedback label
        self.status_msg = QLabel("")
        self.status_msg.setObjectName("status_msg")
        self.status_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_msg.setWordWrap(True)
        self.status_msg.setFixedHeight(22)
        self.status_msg.setFont(QFont("Segoe UI", 10))
        self.status_msg.setStyleSheet("color: #888888;")
        content_layout.addWidget(self.status_msg)

        # ── Buttons row ──
        btn_row = QHBoxLayout()
        btn_row.setSpacing(16)

        self.activate_btn = QPushButton("🔑  ACTIVATE")
        self.activate_btn.setFixedHeight(48)
        self.activate_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.activate_btn.setEnabled(False)
        self.activate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.activate_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #8fe3ea, stop:0.5 #57c7d4, stop:1 #3598a6);
                border: 1px solid #a5f0f7;
                border-radius: 9px;
                color: #062630;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #a6eff5, stop:0.5 #6fe0ed, stop:1 #43abc0);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3598a6, stop:1 #2b7e90);
            }
            QPushButton:disabled {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2c383b, stop:1 #1e2629);
                border: 1px solid #364a50;
                color: #4e6870;
            }
        """)
        self.activate_btn.clicked.connect(self._do_activate)
        btn_row.addWidget(self.activate_btn, 3)

        self.cancel_btn = QPushButton("✕  CANCEL")
        self.cancel_btn.setFixedHeight(48)
        self.cancel_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #474b50, stop:0.5 #383c40, stop:1 #2a2e32);
                border: 1px solid #565b61;
                border-radius: 9px;
                color: #c8d6e0;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #575c62, stop:0.5 #474b50, stop:1 #353a3e);
                border: 1px solid #6c737a;
                color: #ffffff;
            }
            QPushButton:pressed {
                background: #2a2e32;
                color: #94a3b8;
            }
        """)
        self.cancel_btn.clicked.connect(self._do_exit)
        btn_row.addWidget(self.cancel_btn, 1)
        content_layout.addLayout(btn_row)

        # Footer
        footer = QLabel(
            "Contact R1AILAB for key purchase or support: "
            "<b>contact@r1ailab.com</b>"
        )
        footer.setFont(QFont("Segoe UI", 9))
        footer.setStyleSheet("color: #637080;")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(footer)

        card_layout.addWidget(content)
        root.addWidget(card)

    # ── Logic ──────────────────────────────────────────────────────────────
    def _on_key_changed(self, text: str):
        clean = text.replace("-", "").replace(" ", "").upper()
        if len(clean) > 25:
            clean = clean[:25]
        formatted = "-".join(clean[i:i+5] for i in range(0, len(clean), 5))
        if formatted != text:
            self.key_input.blockSignals(True)
            self.key_input.setText(formatted)
            self.key_input.blockSignals(False)
        self.activate_btn.setEnabled(len(formatted.replace("-", "")) == 25)

    def _do_activate(self):
        key = self.key_input.text().strip()
        if not key:
            return

        self.activate_btn.setEnabled(False)
        self.activate_btn.setText("⏳  Verifying...")
        self.status_msg.setStyleSheet("color: #ffaa00;")
        self.status_msg.setText("🔄  Connecting to verification server...")
        QApplication.processEvents()

        try:
            from license_manager import verify_and_activate
            success, message = verify_and_activate(key)
        except Exception as e:
            success, message = False, f"Internal error: {str(e)}"

        if success:
            from license_manager import get_active_license
            payload = get_active_license()
            self.status_msg.setStyleSheet(
                "color: #00ff88; background: rgba(0,255,100,0.06); "
                "border: 1px solid rgba(0,255,100,0.25); border-radius: 6px; padding: 2px 8px;"
            )
            self.status_msg.setText(f"✅  {message}")
            QApplication.processEvents()
            QTimer.singleShot(1200, lambda: self.activation_success.emit(payload or {}))
            QTimer.singleShot(1500, self.accept)
        else:
            self.status_msg.setStyleSheet(
                "color: #ff5555; background: rgba(255,50,50,0.06); "
                "border: 1px solid rgba(255,50,50,0.25); border-radius: 6px; padding: 2px 8px;"
            )
            self.status_msg.setText(f"❌  {message}")
            self.activate_btn.setEnabled(True)
            self.activate_btn.setText("🔑  ACTIVATE")

    def _do_exit(self):
        import sys
        sys.exit(0)

    def closeEvent(self, event):
        # Block window-X close — must use Exit/Cancel button
        event.ignore()
        self._do_exit()


# ─── Security Gate Manager ───────────────────────────────────────────────────
class SecurityGate:
    """
    Main security controller.
    1. Call check_and_unlock() once at startup before showing main window.
    2. Call start_monitoring(window) after main window is shown.
    """

    def __init__(self):
        self._trust_level = TRUST_NONE
        self._monitor_timer = None
        self._license_payload = None

    def check_and_unlock(self, parent_widget=None) -> int:
        """
        Startup gate. Returns trust level.
        If TRUST_NONE: shows ActivationDialog. Exits if user closes dialog.
        """
        from programmer_guard import is_programmer_connected
        from license_manager import get_active_license

        has_programmer = is_programmer_connected()
        license_payload = get_active_license()
        has_license = license_payload is not None

        self._trust_level = compute_trust_level(has_license, has_programmer)
        self._license_payload = license_payload

        if self._trust_level == TRUST_NONE:
            dlg = ActivationDialog(parent=parent_widget, programmer_connected=has_programmer)
            dlg.activation_success.connect(self._on_activation_success)
            result = dlg.exec()

            if result == QDialog.DialogCode.Accepted:
                from license_manager import get_active_license
                from programmer_guard import is_programmer_connected
                license_payload = get_active_license()
                has_programmer = is_programmer_connected()
                has_license = license_payload is not None
                self._license_payload = license_payload
                self._trust_level = compute_trust_level(has_license, has_programmer)
            else:
                import sys
                sys.exit(0)

        return self._trust_level

    def _on_activation_success(self, payload: dict):
        self._license_payload = payload

    def start_monitoring(self, window, check_interval_ms: int = 10000):
        """
        Periodic monitoring. If all auth is lost, forces app closure.
        """
        self._monitor_timer = QTimer()
        self._monitor_timer.setInterval(check_interval_ms)
        self._monitor_timer.timeout.connect(lambda: self._monitor_tick(window))
        self._monitor_timer.start()

    def _monitor_tick(self, window):
        from programmer_guard import is_programmer_connected
        from license_manager import get_active_license

        has_programmer = is_programmer_connected()
        license_payload = get_active_license()
        has_license = license_payload is not None
        new_trust = compute_trust_level(has_license, has_programmer)

        if new_trust != self._trust_level:
            self._trust_level = new_trust
            if hasattr(window, 'on_security_trust_changed'):
                try:
                    window.on_security_trust_changed(new_trust)
                except Exception:
                    pass

        if new_trust == TRUST_NONE:
            if self._monitor_timer:
                self._monitor_timer.stop()
            self._force_close(window)

    def _force_close(self, window):
        msg = QMessageBox(window)
        msg.setWindowTitle("Security Alert — Access Revoked")
        msg.setText(
            "Security Verification Failed!\n\n"
            "Your license was revoked or the programmer was disconnected.\n\n"
            "The software will now close.\n"
            "Please reconnect your programmer or contact R1AILAB support."
        )
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setStyleSheet(
            "QMessageBox { background-color: #1c2024; color: #ff5555; }"
            "QLabel { color: #ff5555; font-weight: bold; font-size: 13px; }"
            "QPushButton { background-color: #2a1414; color: #ff5555; "
            "border: 1px solid #ff5555; border-radius: 6px; padding: 8px 20px; }"
            "QPushButton:hover { background-color: #ff5555; color: #000000; }"
        )
        msg.exec()
        import sys
        sys.exit(0)

    def get_trust_level(self) -> int:
        return self._trust_level

    def get_license_payload(self) -> dict:
        return self._license_payload or {}

    def is_authorized(self) -> bool:
        return self._trust_level > TRUST_NONE

    def trust_label(self) -> str:
        labels = {
            TRUST_NONE:     "Unauthorized",
            TRUST_KEY_ONLY: "License Key Active",
            TRUST_HW_ONLY:  "Hardware Dongle",
            TRUST_FULL:     "Full Dual-Auth",
        }
        return labels.get(self._trust_level, "Unknown")
