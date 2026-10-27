import sys
import os
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt, QTimer, QRectF, Signal, QPoint
from PySide6.QtGui import (QPainter, QColor, QFont, QPen, QBrush, 
                           QPainterPath, QPixmap, QConicalGradient)

class ModernSplashScreen(QWidget):
    finished = Signal()

    def __init__(self, duration_ms=6000, auto_timer=False, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SubWindow)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Dimensions matching the 1106x960 aspect ratio (~1.15 : 1)
        self.target_width = 560
        self.target_height = 486
        self.setFixedSize(self.target_width, self.target_height)
        
        # Load background
        from path_utils import get_resource_path
        bg_path = get_resource_path(os.path.join("assets", "splash_bg.png"))
        if os.path.exists(bg_path):
            self.bg_pixmap = QPixmap(bg_path).scaled(
                self.target_width, self.target_height, 
                Qt.IgnoreAspectRatio, Qt.SmoothTransformation
            )
        else:
            self.bg_pixmap = None
            
        self.progress = 0.0  # 0.0 to 100.0
        self.status_text = "INITIALIZING SECURITY SYSTEM..."
        self.duration_ms = duration_ms
        self.auto_timer = auto_timer
        self.step_interval = 16  # ~60 fps
        self.elapsed = 0
        self._drag_pos = QPoint()
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_progress)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and not self._drag_pos.isNull():
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def start_animation(self):
        self.progress = 0.0
        self.elapsed = 0
        self.show()
        # Center on screen
        screen = QApplication.primaryScreen()
        if screen:
            screen_geom = screen.geometry()
            x = (screen_geom.width() - self.width()) // 2
            y = (screen_geom.height() - self.height()) // 2
            self.move(x, y)
        self.update()
        if self.auto_timer:
            self.timer.start(self.step_interval)

    def pause(self):
        self.timer.stop()

    def resume(self):
        self.timer.start(self.step_interval)

    def set_progress_val(self, val, text=None):
        self.progress = min(100.0, max(0.0, val))
        if text:
            self.status_text = text
        else:
            if self.progress < 25:
                self.status_text = "INITIALIZING SECURITY SYSTEM..."
            elif self.progress < 50:
                self.status_text = "VERIFYING HARDWARE DONGLE..."
            elif self.progress < 75:
                self.status_text = "LOADING FIRMWARE ENGINES..."
            elif self.progress < 100:
                self.status_text = "PREPARING WORKSPACE..."
            else:
                self.status_text = "SYSTEM READY"
        self.update()

    def _update_progress(self):
        self.elapsed += self.step_interval
        t = min(1.0, self.elapsed / self.duration_ms)
        # Ease out cubic curve for ultra smooth motion
        eased = 1.0 - pow(1.0 - t, 3)
        val = eased * 100.0
        self.set_progress_val(val)
        
        if t >= 1.0:
            self.timer.stop()
            self.set_progress_val(100.0, "SYSTEM READY")
            QTimer.singleShot(350, self._on_finish)

    def _on_finish(self):
        self.finished.emit()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.TextAntialiasing)

        w = self.width()
        h = self.height()
        radius = 24.0

        # 1. Clip to rounded rectangle (translucent antialiased window)
        clip_path = QPainterPath()
        clip_rect = QRectF(0.5, 0.5, w - 1.0, h - 1.0)
        clip_path.addRoundedRect(clip_rect, radius, radius)
        painter.setClipPath(clip_path)

        # 2. Draw background image
        if self.bg_pixmap and not self.bg_pixmap.isNull():
            painter.drawPixmap(0, 0, self.bg_pixmap)
        else:
            painter.fillRect(0, 0, w, h, QColor("#171a1d"))

        # 3. Dynamic Circular Gauge
        # Exact center matching reference image: cx = 553 / 1106 = 0.500, cy = 753 / 960 = 0.784375
        cx = w * 0.500
        cy = h * (753.0 / 960.0)

        # Concentric ring radii matching the reference image grooves
        r_outer = h * (127.0 / 960.0)
        r_mid = h * (108.0 / 960.0)
        r_inner = h * (88.0 / 960.0)

        progress_ratio = self.progress / 100.0
        max_angle = progress_ratio * 360.0

        if max_angle > 0:
            # Gradient matching original aesthetic:
            # Bottom is electric cyan / teal, transitioning clockwise to golden bronze/amber at top
            conical = QConicalGradient(cx, cy, -90.0)
            conical.setColorAt(0.00, QColor("#00f0ff"))  # Neon teal/cyan
            conical.setColorAt(0.30, QColor("#38bdf8"))  # Sky cyan
            conical.setColorAt(0.55, QColor("#fde68a"))  # Light gold
            conical.setColorAt(0.75, QColor("#e2a865"))  # Copper/amber
            conical.setColorAt(0.95, QColor("#00f0ff"))  # Seamless loop

            # --- Outer Ring (Full progress arc) ---
            # Soft glow pass
            pen_outer_glow = QPen(QBrush(QColor(0, 240, 255, 60)), 7.0)
            pen_outer_glow.setCapStyle(Qt.RoundCap)
            painter.setPen(pen_outer_glow)
            rect_outer = QRectF(cx - r_outer, cy - r_outer, r_outer * 2, r_outer * 2)
            painter.drawArc(rect_outer, int(-90 * 16), int(-max_angle * 16))

            # Main sharp ribbon
            pen_outer = QPen(QBrush(conical), 4.5)
            pen_outer.setCapStyle(Qt.RoundCap)
            painter.setPen(pen_outer)
            painter.drawArc(rect_outer, int(-90 * 16), int(-max_angle * 16))

            # --- Middle Ring (Slight phase lag for cyber depth) ---
            mid_angle = max_angle * 0.90
            pen_mid = QPen(QBrush(conical), 3.5)
            pen_mid.setCapStyle(Qt.RoundCap)
            painter.setPen(pen_mid)
            rect_mid = QRectF(cx - r_mid, cy - r_mid, r_mid * 2, r_mid * 2)
            painter.drawArc(rect_mid, int(-90 * 16), int(-mid_angle * 16))

            # --- Inner Ring (Slightly further offset) ---
            inner_angle = max_angle * 0.82
            pen_inner = QPen(QBrush(conical), 3.0)
            pen_inner.setCapStyle(Qt.RoundCap)
            painter.setPen(pen_inner)
            rect_inner = QRectF(cx - r_inner, cy - r_inner, r_inner * 2, r_inner * 2)
            painter.drawArc(rect_inner, int(-90 * 16), int(-inner_angle * 16))

        # 4. Center Percentage Text
        pct_str = f"{int(self.progress)}%"
        rect_pct = QRectF(cx - 70, cy - 25, 140, 50)
        
        font_pct = QFont("Segoe UI", 19, QFont.Bold)
        font_pct.setLetterSpacing(QFont.AbsoluteSpacing, 1.2)
        painter.setFont(font_pct)

        # Subtle embossed drop shadow
        painter.setPen(QColor(10, 15, 20, 220))
        painter.drawText(rect_pct.adjusted(1.5, 1.5, 1.5, 1.5), Qt.AlignCenter, pct_str)

        # Metallic champagne/silver text
        painter.setPen(QColor("#f1ece1"))
        painter.drawText(rect_pct, Qt.AlignCenter, pct_str)

        # 5. Status Text at the bottom (Matching y=918/960 = 0.956)
        font_status = QFont("Segoe UI", 9, QFont.Bold)
        font_status.setLetterSpacing(QFont.AbsoluteSpacing, 2.0)
        painter.setFont(font_status)
        
        status_y = h * (918.0 / 960.0) - 14.0
        rect_status = QRectF(0, status_y, w, 28)
        
        if self.progress >= 100:
            painter.setPen(QColor("#00ff88"))  # Neon green when complete
        else:
            painter.setPen(QColor("#4cd3e3"))  # Cyber teal during loading
            
        painter.drawText(rect_status, Qt.AlignCenter, self.status_text)

        # 6. Sleek subtle outer border for floating window
        painter.setClipping(True)
        painter.setClipPath(clip_path)
        border_pen = QPen(QColor(56, 189, 248, 80), 1.2)
        painter.setPen(border_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(clip_rect, radius, radius)
