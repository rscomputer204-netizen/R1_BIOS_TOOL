# BIOS Client Application - Remote VPS Integration (Exact Visual Clone of main.py)
import sys
import os
import io
import threading
import socket
import shutil
import time
import struct
from datetime import datetime

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QTextEdit, QFileDialog, 
                             QLabel, QFrame, QDialog, QTableView, QHeaderView, QSplitter,
                             QMenu, QMessageBox, QTabWidget, QLineEdit, QComboBox, 
                             QInputDialog, QDialogButtonBox, QAbstractItemView)
from PySide6.QtCore import (Qt, QSize, QMetaObject, Q_ARG, Slot, QTimer, 
                             QAbstractTableModel, QModelIndex, Signal, Property, 
                             QPropertyAnimation, QRectF, QEasingCurve)
from PySide6.QtGui import (QFont, QColor, QIcon, QShortcut, QKeySequence, 
                            QPainter, QPen, QBrush, QPainterPath, QPixmap, QAction)

# Import logic
from network_manager import NetworkManager
from bios_parser import get_bios_metadata
from firmware_organizer import detect_and_organize_local_firmware
from mea_parser import parse_mea_output
from error_manager import ErrorManager
from performance_tracker import tracker
from analysis_suite import AnalysisSuite

# --- EXACT STYLESHEET FROM main.py ---
STYLESHEET = """
QMainWindow { background-color: #0a0b10; }
QFrame#Sidebar { background-color: #12141d; border-right: 1px solid #1f2233; min-width: 200px; max-width: 200px; }
QLabel#Title { color: #00f3ff; font-size: 18px; font-weight: bold; padding: 20px 10px; text-transform: uppercase; letter-spacing: 2px; }
QPushButton { font-family: 'Orbitron', 'Digital-7', monospace; background-color: #1a1d2e; color: #ffffff; border: 1px solid #00f3ff; padding: 12px; font-size: 14px; font-weight: bold; text-align: left; border-radius: 4px; margin: 5px 10px; }
QPushButton:hover { background-color: #00f3ff; color: #0a0b10; }
QPushButton:disabled { background-color: #0a0b10; color: #444444; border: 1px solid #222222; }
QPushButton#ActionButton { text-align: center; border: 2px solid #00ff41; color: #00ff41; }
QPushButton#ActionButton:hover { background-color: #00ff41; color: #000000; }
QTextEdit#Terminal { background-color: #000000; color: #00FF00; font-family: 'Consolas', 'Monaco', monospace; font-size: 12px; border: 1px solid #1f2233; padding: 10px; }
QLabel#InternetStatus { font-family: 'Orbitron', sans-serif; font-size: 11px; font-weight: bold; padding: 2px 8px; border-radius: 10px; background-color: #1a1d2e; border: 1px solid #1f2233; }
QDialog { background-color: #0a0b10; color: #00ff41; }
QPushButton#LogButton { background-color: #12141d; border: 1px solid #333; font-size: 10px; padding: 4px 8px; min-width: 80px; }
QPushButton#LogButton:hover { background-color: #333; color: #fff; }
QScrollBar:vertical { border: none; background: #0a0b10; width: 10px; }
QScrollBar::handle:vertical { background: #1f2233; min-height: 20px; }
QTableView#HexView { background-color: #000000; color: #4CAF50; font-family: 'Consolas', 'Monaco', monospace; font-size: 13px; border: 1px solid #1f2233; gridline-color: transparent; selection-background-color: #004488; selection-color: #ffffff; }
QHeaderView::section { background-color: #0a0b10; color: #00f3ff; border: none; font-family: 'Consolas', 'Monaco', monospace; font-size: 13px; padding: 2px 4px; }
"""

class HexTableModel(QAbstractTableModel):
    CHARS_LOOKUP = [chr(b) if (32 <= b <= 126 or b >= 160) else "." for b in range(256)]
    def __init__(self, data=b"", parent=None):
        super().__init__(parent)
        self._data = bytearray(data)
    def set_data(self, data):
        self.beginResetModel()
        self._data = bytearray(data)
        self.endResetModel()
    def get_data(self): return self._data
    def rowCount(self, parent=QModelIndex()): return (len(self._data) + 15) // 16
    def columnCount(self, parent=QModelIndex()): return 17
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid(): return None
        row, col = index.row(), index.column()
        offset = row * 16 + col
        if role == Qt.DisplayRole:
            if col < 16:
                return f"{self._data[offset]:02X}" if offset < len(self._data) else ""
            else:
                start = row * 16
                end = min(start + 16, len(self._data))
                return "".join(self.CHARS_LOOKUP[b] for b in self._data[start:end])
        return None
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole: return None
        if orientation == Qt.Horizontal: return f"{section:02X}" if section < 16 else "Decoded"
        return f"{section * 16:08X}"

class HexEditorTab(QWidget):
    def __init__(self, data=b"", parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.hex_view = QTableView()
        self.hex_view.setObjectName("HexView")
        self.hex_model = HexTableModel(data)
        self.hex_view.setModel(self.hex_model)
        self.hex_view.setShowGrid(False)
        for i in range(16): self.hex_view.setColumnWidth(i, 26)
        self.hex_view.setColumnWidth(16, 160)
        self.layout.addWidget(self.hex_view)

class LoadingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_NoSystemBackground); self.setAttribute(Qt.WA_TranslucentBackground)
        self.hide(); self.angle = 0; self.status_text = "Processing..."
        self.anim = QPropertyAnimation(self, b"rotation_angle")
        self.anim.setDuration(1200); self.anim.setStartValue(0); self.anim.setEndValue(360)
        self.anim.setLoopCount(-1); self.anim.setEasingCurve(QEasingCurve.Linear)
    @Property(int)
    def rotation_angle(self): return self.angle
    @rotation_angle.setter
    def rotation_angle(self, value): self.angle = value; self.update()
    def start(self, text="Processing..."): self.status_text = text; self.show(); self.anim.start()
    def stop(self): self.anim.stop(); self.hide()
    def paintEvent(self, event):
        painter = QPainter(self); painter.fillRect(self.rect(), QColor(5, 6, 12, 240))
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor(0, 243, 255), 4)); cx, cy = self.width()/2, self.height()/2
        painter.save(); painter.translate(cx, cy); painter.rotate(self.angle)
        painter.drawArc(QRectF(-50, -50, 100, 100), 0, 90*16); painter.restore()
        painter.drawText(self.rect(), Qt.AlignCenter, f"\n\n\n{self.status_text}")

class DropZoneOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_NoSystemBackground); self.setAttribute(Qt.WA_TranslucentBackground); self.hide()
    def paintEvent(self, event):
        painter = QPainter(self); painter.fillRect(self.rect(), QColor(0, 243, 255, 30))
        pen = QPen(QColor(0, 243, 255), 4); pen.setStyle(Qt.DashLine); painter.setPen(pen)
        painter.drawRect(self.rect().adjusted(10, 10, -10, -10))
        painter.setPen(QColor(0, 243, 255)); font = QFont("Orbitron", 20, QFont.Bold); painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignCenter, ">>> INITIALIZE REMOTE DECRYPTION <<<\nDROP BIOS FILE HERE")
    def resizeEvent(self, event):
        if self.parent(): self.setGeometry(self.parent().rect())

class BiosServiceClient(QMainWindow):
    terminal_signal = Signal(str)
    server_status_signal = Signal(bool)
    hex_data_signal = Signal(bytes)

    def __init__(self):
        super().__init__()
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.setWindowTitle("R1 BIOS SERVICE TOOL")
        self.setMinimumSize(1000, 650)
        self.setStyleSheet(STYLESHEET)
        
        self.network = NetworkManager(host='127.0.0.1')
        self.current_bios_file = None
        self.current_regions_map = {}
        self.loading_overlay = LoadingOverlay(self)
        self.drop_overlay = DropZoneOverlay(self)
        self.setAcceptDrops(True)
        
        self.setup_ui()
        self.setup_signals()
        
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.check_connectivity)
        self.status_timer.start(5000)
        self.check_connectivity()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0); main_layout.setSpacing(0)

        # Sidebar
        sidebar = QFrame(); sidebar.setObjectName("Sidebar")
        sidebar_layout = QVBoxLayout(sidebar); sidebar_layout.setContentsMargins(0, 0, 0, 0); sidebar_layout.setSpacing(0)
        
        branding = QWidget(); branding_ly = QVBoxLayout(branding); branding_ly.setContentsMargins(10, 20, 10, 10)
        logo = QLabel()
        logo_path = os.path.join(self.base_path, "assets", "R1AILAB.png")
        if not os.path.exists(logo_path): logo_path = os.path.join(self.base_path, "assets", "R1 IT LAB.png")
        if not os.path.exists(logo_path): logo_path = os.path.join(self.base_path, "_internal", "assets", "R1AILAB.png")
        if os.path.exists(logo_path): logo.setPixmap(QPixmap(logo_path).scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo.setAlignment(Qt.AlignCenter); branding_ly.addWidget(logo)
        
        title = QLabel("R1 editor"); title.setObjectName("Title"); title.setAlignment(Qt.AlignCenter); branding_ly.addWidget(title)
        sidebar_layout.addWidget(branding)

        sidebar_layout.addWidget(QLabel("────── ACTION ENGINE ──────", styleSheet="color: #333; font-size: 9px; margin-top: 15px;", alignment=Qt.AlignCenter))
        self.btn_smart_me = QPushButton("SMART ME FIX"); self.btn_smart_me.setStyleSheet("border-color: #00ff41; color: #00ff41; font-weight: bold;")
        self.btn_bios_rg = QPushButton("BIOS RG FIX"); self.btn_bios_rg.setStyleSheet("border-color: #ff00ff; color: #ff00ff;")
        self.btn_extract_dmi = QPushButton("EXTRACT DMI"); self.btn_extract_dmi.setStyleSheet("border-color: #00f3ff; color: #00f3ff;")
        self.btn_apply_patches = QPushButton("APPLY PATCHES"); self.btn_apply_patches.setStyleSheet("border-color: #00d4ff; color: #00d4ff;")
        self.btn_save_fix = QPushButton("SAVE && FIX"); self.btn_save_fix.setStyleSheet("border-color: #ffaa00; color: #ffaa00;")

        for btn in [self.btn_smart_me, self.btn_bios_rg, self.btn_extract_dmi, self.btn_apply_patches, self.btn_save_fix]:
            sidebar_layout.addWidget(btn); btn.setEnabled(False)
        self.btn_smart_me.clicked.connect(lambda: self.vps_action("SMART_ME_FIX"))
        self.btn_bios_rg.clicked.connect(lambda: self.vps_action("BIOS_RG_FIX"))
        self.btn_extract_dmi.clicked.connect(lambda: self.vps_action("EXTRACT_DMI"))
        self.btn_save_fix.clicked.connect(lambda: self.vps_action("SAVE_AND_FIX"))

        sidebar_layout.addStretch()
        sidebar_layout.addWidget(QLabel("────── UTILITIES ──────", styleSheet="color: #333; font-size: 9px;", alignment=Qt.AlignCenter))
        self.btn_manual = QPushButton("MANUAL EXTRACT"); self.btn_manual.setStyleSheet("font-size: 9px; color: #444;"); sidebar_layout.addWidget(self.btn_manual)
        self.btn_settings = QPushButton("SETTINGS"); self.btn_settings.setStyleSheet("font-size: 9px; color: #444;"); sidebar_layout.addWidget(self.btn_settings)
        
        footer = QLabel("VERSION 2.0.0\nSMART BUILD"); footer.setStyleSheet("color: #333; font-size: 10px; margin: 20px;"); footer.setAlignment(Qt.AlignCenter); sidebar_layout.addWidget(footer)
        main_layout.addWidget(sidebar)

        # Content Area
        content = QWidget(); content_layout = QVBoxLayout(content); content_layout.setContentsMargins(20, 20, 20, 20); content_layout.setSpacing(10)
        header = QLabel("SYSTEM STATUS: ONLINE"); header.setStyleSheet("color: #00ff41; font-family: monospace;"); content_layout.addWidget(header)

        top_btn_ly = QHBoxLayout()
        self.btn_open = QPushButton("OPEN BIOS FILE"); self.btn_open.setObjectName("ActionButton"); self.btn_open.setFixedWidth(200); self.btn_open.clicked.connect(self.open_bios_dialog); top_btn_ly.addWidget(self.btn_open)
        self.btn_save_changes = QPushButton("SAVE CHANGES"); self.btn_save_changes.setObjectName("ActionButton"); self.btn_save_changes.setFixedWidth(200); self.btn_save_changes.setStyleSheet("border-color: #ff00ff; color: #ff00ff;"); self.btn_save_changes.setEnabled(False); top_btn_ly.addWidget(self.btn_save_changes)
        top_btn_ly.addStretch(); content_layout.addLayout(top_btn_ly)

        splitter = QSplitter(Qt.Horizontal); splitter.setHandleWidth(8); splitter.setStyleSheet("QSplitter::handle { background-color: #1f2233; }")
        term_widget = QWidget(); term_ly = QVBoxLayout(term_widget); term_ly.setContentsMargins(0, 0, 0, 0); term_ly.addWidget(QLabel("TERMINAL OUTPUT", styleSheet="color: #00f3ff; font-weight: bold;"))
        self.terminal = QTextEdit(); self.terminal.setObjectName("Terminal"); self.terminal.setReadOnly(True); term_ly.addWidget(self.terminal); splitter.addWidget(term_widget)
        hex_widget = QWidget(); hex_ly = QVBoxLayout(hex_widget); hex_ly.setContentsMargins(0, 0, 0, 0); hex_ly.addWidget(QLabel("HEX VIEWER", styleSheet="color: #00f3ff; font-weight: bold;"))
        self.hex_tabs = QTabWidget(); self.hex_tabs.setStyleSheet("QTabWidget::pane { border: 1px solid #1f2233; } QTabBar::tab { background-color: #12141d; color: #00f3ff; padding: 5px 15px; } QTabBar::tab:selected { border-bottom: 2px solid #00ff41; }")
        self.add_hex_tab("Main BIOS"); hex_ly.addWidget(self.hex_tabs); splitter.addWidget(hex_widget)
        splitter.setSizes([700, 300]); content_layout.addWidget(splitter, 2)

        footer_ly = QHBoxLayout()
        btn_logs = QPushButton("SHOW LOGS"); btn_logs.setObjectName("LogButton"); footer_ly.addWidget(btn_logs); footer_ly.addStretch()
        self.lbl_server_status = QLabel("● SERVER: CHECKING..."); self.lbl_server_status.setObjectName("InternetStatus"); self.lbl_server_status.setStyleSheet("color: #ffa500;"); footer_ly.addWidget(self.lbl_server_status)
        self.lbl_net_status = QLabel("● ONLINE"); self.lbl_net_status.setObjectName("InternetStatus"); self.lbl_net_status.setStyleSheet("color: #00ff41;"); footer_ly.addWidget(self.lbl_net_status)
        content_layout.addLayout(footer_ly)
        main_layout.addWidget(content)

    def setup_signals(self):
        self.terminal_signal.connect(self.log_to_terminal); self.server_status_signal.connect(self.update_server_ui)
        self.hex_data_signal.connect(lambda data: self.hex_tabs.currentWidget().hex_model.set_data(data))

    def add_hex_tab(self, name, data=b""):
        tab = HexEditorTab(data); self.hex_tabs.addTab(tab, name)

    @Slot(str)
    def log_to_terminal(self, msg):
        if threading.current_thread() is not threading.main_thread():
            QMetaObject.invokeMethod(self, "log_to_terminal", Qt.QueuedConnection, Q_ARG(str, msg))
            return
        self.terminal.append(msg)
        self.terminal.verticalScrollBar().setValue(self.terminal.verticalScrollBar().maximum())

    def resizeEvent(self, event):
        if hasattr(self, 'loading_overlay'):
            self.loading_overlay.setGeometry(self.rect())
        if hasattr(self, 'drop_overlay'):
            self.drop_overlay.setGeometry(self.rect())
        super().resizeEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction(); self.drop_overlay.show()
    def dragLeaveEvent(self, event): self.drop_overlay.hide()
    def dropEvent(self, event):
        self.drop_overlay.hide()
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile(): self.load_bios_file(urls[0].toLocalFile())

    def check_connectivity(self):
        def _check(): is_up = self.network.check_connection(); self.server_status_signal.emit(is_up)
        threading.Thread(target=_check, daemon=True).start()

    @Slot(bool)
    def update_server_ui(self, is_up):
        if is_up: self.lbl_server_status.setText("● SERVER: CONNECTED"); self.lbl_server_status.setStyleSheet("color: #00ff41;")
        else: self.lbl_server_status.setText("● SERVER: DISCONNECTED"); self.lbl_server_status.setStyleSheet("color: #ff3131;")

    def open_bios_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open BIOS File", "", "BIOS Files (*.bin *.rom *.fd *.cap);;All Files (*)")
        if path: self.load_bios_file(path)

    def load_bios_file(self, path):
        self.current_bios_file = path
        self.terminal.clear()
        self.log_to_terminal(f"[INFO] Loading: {os.path.basename(path)}")
        self.loading_overlay.start("Analyzing Locally...")
        
        def _analyze():
            try:
                with open(path, "rb") as f: 
                    data = f.read()
                    self.hex_data_signal.emit(data)
                
                # 1. Base Metadata & ME Analyzer
                metadata = get_bios_metadata(path, self.log_to_terminal)
                
                if metadata:
                    # 2. Additional Analyses (Matching main.py)
                    self.log_to_terminal("-" * 30)
                    self.log_to_terminal(">>> SYSTEM HEALTH REPORT GENERATED")
                    self.log_to_terminal("-" * 30)
                    
                    AnalysisSuite.run_microcode_analyzer(path, self.log_to_terminal)
                    AnalysisSuite.run_security_descriptor_parser(path, self.log_to_terminal)
                    AnalysisSuite.run_bios_guard_analysis(path, self.log_to_terminal)
                    
                    self.log_to_terminal("-" * 30)
                    self.log_to_terminal("[SUCCESS] ALL ANALYSES COMPLETE")
                    self.log_to_terminal("-" * 30)

                    regions = metadata.get("regions")
                    if regions:
                        self.current_regions_map = regions
                        QMetaObject.invokeMethod(self.btn_smart_me, "setEnabled", Qt.QueuedConnection, Q_ARG(bool, "me_csme" in regions or "me_region" in regions))
                        QMetaObject.invokeMethod(self.btn_bios_rg, "setEnabled", Qt.QueuedConnection, Q_ARG(bool, "bios" in regions or "bios_region" in regions))
                        QMetaObject.invokeMethod(self.btn_extract_dmi, "setEnabled", Qt.QueuedConnection, Q_ARG(bool, "bios" in regions or "bios_region" in regions))
                        QMetaObject.invokeMethod(self.btn_apply_patches, "setEnabled", Qt.QueuedConnection, Q_ARG(bool, True))
                        QMetaObject.invokeMethod(self.btn_save_fix, "setEnabled", Qt.QueuedConnection, Q_ARG(bool, True))
                        QMetaObject.invokeMethod(self.btn_save_changes, "setEnabled", Qt.QueuedConnection, Q_ARG(bool, True))
                else:
                    for btn in [self.btn_smart_me, self.btn_bios_rg, self.btn_extract_dmi, self.btn_apply_patches, self.btn_save_fix, self.btn_save_changes]:
                        QMetaObject.invokeMethod(btn, "setEnabled", Qt.QueuedConnection, Q_ARG(bool, True))
            except Exception as e:
                self.log_to_terminal(f"[ERROR] Analysis failed: {str(e)}")
            finally:
                QMetaObject.invokeMethod(self.loading_overlay, "stop", Qt.QueuedConnection)
            
        threading.Thread(target=_analyze, daemon=True).start()

    def vps_action(self, command):
        if not self.current_bios_file: return
        if not self.network.check_connection():
            QMessageBox.critical(self, "Server Error", "VPS Server is not connected. Please check your network or server status.")
            return
        self.loading_overlay.start(f"VPS: {command}...")
        def _thread():
            result = self.network.send_and_process(self.current_bios_file, command, self.terminal_signal.emit)
            if result:
                self.current_bios_file = result
                with open(result, "rb") as f: self.hex_data_signal.emit(f.read())
            QMetaObject.invokeMethod(self.loading_overlay, "stop", Qt.QueuedConnection)
        threading.Thread(target=_thread, daemon=True).start()

if __name__ == "__main__":
    app = QApplication(sys.argv); window = BiosServiceClient(); window.show(); sys.exit(app.exec())
