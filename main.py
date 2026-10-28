


# Main Entry Point
import sys
import os
import io

# Add current directory and virtualenv site-packages to path
_app_root = os.path.dirname(os.path.abspath(__file__))
if _app_root not in sys.path:
    sys.path.insert(0, _app_root)

_venv_site_packages = os.path.join(_app_root, ".venv", "Lib", "site-packages")
if os.path.exists(_venv_site_packages) and _venv_site_packages not in sys.path:
    sys.path.insert(0, _venv_site_packages)

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QTextEdit, QFileDialog, 
                             QLabel, QFrame, QDialog, QTableView, QHeaderView, QSplitter,
                             QMenu, QMessageBox, QGraphicsBlurEffect, QTabWidget, QScrollArea,
                             QLineEdit, QComboBox, QCheckBox, QDialogButtonBox,
                             QAbstractItemView, QInputDialog, QTextBrowser,
                             QTableWidget, QTableWidgetItem, QRadioButton,
                             QListWidget, QListWidgetItem, QFormLayout, QGroupBox,
                             QStackedWidget)
from PySide6.QtCore import (Qt, QSize, QMetaObject, Q_ARG, Slot, QTimer, 
                            QAbstractTableModel, QModelIndex, Signal, Property, 
                            QPropertyAnimation, QRectF, QEasingCurve, QUrl)
from PySide6.QtGui import (QFont, QColor, QPalette, QIcon, QShortcut, 
                           QKeySequence, QAction, QPainter, QPen, QBrush, QPainterPath, QPixmap)
import threading
import socket
import shutil
import json
from pathlib import Path

# Import logic
from bios_parser import get_bios_metadata
from firmware_organizer import detect_and_organize_local_firmware
from me_cleaner import apply_firmware_patch # Changed from apply_me_clean_patch
from bios_decompiler import decompile_bios
from advanced_extractor import AdvancedExtractor
from path_utils import get_app_root, get_resource_path
from datetime import datetime
from mea_parser import parse_mea_output
from firmware_matcher import FirmwareMatcher
import fit_automator
import smart_repair_engine
from error_manager import ErrorManager
from dmi_migrator import DMIMigrator
from PySide6.QtWidgets import QInputDialog
from performance_tracker import tracker
import time
from dmi_extractor import DMIExtractor
from bios_region_fixer import BIOSRegionFixer
from hp_repair_tool import HPBIOSRepairer
from language_manager import lm, t
from report_settings_ui import ReportSettingsManager, ReportSettingsDialog
from brands.manager import BrandManager
from password_remover_dialog import PasswordRemoverDialog
import re
import queue

HEX_JUMP_RE = re.compile(r'\b(0x[0-9a-fA-F]+)\b')
HTML_STRIP_RE = re.compile(r'<[^>]+>')

# Enterprise Edition Stylesheet (Charcoal & Neon Teal)
STYLESHEET_DARK = """
QMainWindow { background-color: #171a1d; }
QFrame#Sidebar {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1a1e22, stop:1 #15181b);
    border-right: 1px solid #282f37;
    min-width: 210px;
    max-width: 210px;
}
QLabel#Title {
    color: #4cd3e3;
    font-family: 'Segoe UI', sans-serif;
    font-size: 16px;
    font-weight: 800;
    padding: 10px;
    letter-spacing: 2px;
}
QPushButton {
    font-family: 'Segoe UI', sans-serif;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #252a2e, stop:1 #1c2024);
    color: #c8d6e0;
    border: 1px solid #333d47;
    padding: 10px 14px;
    font-size: 12px;
    font-weight: 600;
    text-align: left;
    border-radius: 6px;
    margin: 4px 10px;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2ac4db, stop:0.5 #3598a6, stop:1 #1fa2b5);
    border: 1px solid #0ef6fd;
    color: #0b151a;
    font-weight: 700;
}
QPushButton:pressed {
    background-color: #00e0ed;
    color: #000000;
}
QPushButton:disabled {
    background-color: #181b1e;
    color: #454f59;
    border: 1px solid #23282d;
}
QPushButton#ActionButton {
    text-align: center;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8fe3ea, stop:0.4 #3598a6, stop:1 #247d8a);
    border: 1px solid #0ef6fd;
    color: #0d171c;
    font-weight: 800;
    border-radius: 6px;
}
QPushButton#ActionButton:hover {
    background: #0ef6fd;
    color: #000000;
}
QTextBrowser#Terminal {
    background-color: #121518;
    color: #38bdf8;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
    border: 1px solid #283039;
    border-radius: 8px;
    padding: 10px;
}
QLabel#InternetStatus {
    font-family: 'Segoe UI', sans-serif;
    font-size: 11px;
    font-weight: bold;
    padding: 3px 10px;
    border-radius: 10px;
    background-color: #1a1e22;
    border: 1px solid #283038;
    color: #ffffff;
}
QDialog {
    background-color: #1c2024;
    color: #e2e8f0;
    font-family: 'Segoe UI', sans-serif;
}
QPushButton#LogButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #252a2e, stop:1 #1c2024);
    border: 1px solid #333d47;
    color: #94a3b8;
    font-size: 10px;
    font-weight: 600;
    padding: 4px 10px;
    min-width: 80px;
    border-radius: 4px;
}
QPushButton#LogButton:hover {
    background-color: #2f373f;
    color: #4cd3e3;
    border: 1px solid #2ac4db;
}
QScrollBar:vertical {
    border: none;
    background: #15181b;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #2f3842;
    min-height: 25px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #2ac4db;
}
QTableView#HexView {
    background-color: #121518;
    color: #4cd3e3;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 13px;
    border: 1px solid #283039;
    border-radius: 6px;
    gridline-color: transparent;
    selection-background-color: #1b4b5e;
    selection-color: #ffffff;
}
QTableView#HexView::item {
    padding-left: 2px;
    padding-right: 2px;
}
QHeaderView::section {
    background-color: #1a1e22;
    border: none;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 12px;
    padding: 3px 6px;
    text-align: left;
    color: #94a3b8;
}
QHeaderView::section:horizontal {
    color: #4cd3e3;
    font-weight: bold;
}
QTableView QTableCornerButton::section {
    background-color: #1a1e22;
    border: 1px solid #283039;
}
QPushButton#AdvancedButton {
    border: 1px solid #2ac4db;
    color: #4cd3e3;
}
QPushButton#AdvancedButton:disabled {
    background-color: #181b1e;
    color: #454f59;
    border: 1px solid #23282d;
}
QPushButton#ThemeButtonDark {
    background-color: #252a2e;
    color: #4cd3e3;
    border: 1px solid #2ac4db;
    font-weight: bold;
    text-align: center;
}
QPushButton#ThemeButtonDark:hover {
    background-color: #2ac4db;
    color: #0b151a;
}
QPushButton#ThemeButtonLight {
    background-color: #252a2e;
    color: #94a3b8;
    border: 1px solid #333d47;
    font-weight: bold;
    text-align: center;
}
QPushButton#ThemeButtonLight:hover {
    background-color: #333d47;
    color: #ffffff;
}
QWidget#HexWidget { background-color: #171a1d; }
QLabel#HexLabel { color: #4cd3e3; font-weight: bold; font-family: 'Segoe UI', sans-serif; padding: 10px; }
QTabWidget::pane { border: 1px solid #283039; background-color: #171a1d; border-radius: 6px; }
QTabBar::tab {
    background-color: #1e2328;
    color: #94a3b8;
    padding: 6px 16px;
    border: 1px solid #283039;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
    font-weight: 600;
}
QTabBar::tab:selected {
    background-color: #283037;
    color: #0ef6fd;
    border-bottom: 2px solid #0ef6fd;
    font-weight: bold;
}
QTabBar::tab:hover:!selected {
    background-color: #232930;
    color: #cbd5e1;
}
"""


STYLESHEET_LIGHT = """
QMainWindow { background-color: #f0f2f5; }
QFrame#Sidebar { background-color: #ffffff; border-right: 1px solid #d1d5db; min-width: 200px; max-width: 200px; }
QLabel#Title { color: #2563eb; font-size: 18px; font-weight: bold; padding: 20px 10px; text-transform: uppercase; letter-spacing: 2px; }
QPushButton { font-family: 'Orbitron', 'Digital-7', monospace; background-color: #ffffff; color: #1f2937; border: 1px solid #9ca3af; padding: 12px; font-size: 14px; font-weight: bold; text-align: left; border-radius: 4px; margin: 5px 10px; }
QPushButton:hover { background-color: #3b82f6; color: #ffffff; border-color: #3b82f6; }
QPushButton:disabled { background-color: #e5e7eb; color: #9ca3af; border: 1px solid #d1d5db; }
QPushButton#ActionButton { text-align: center; border: 2px solid #10b981; color: #059669; }
QPushButton#ActionButton:hover { background-color: #10b981; color: #ffffff; }
QTextBrowser#Terminal { background-color: #ffffff; color: #065f46; font-family: 'Consolas', 'Monaco', monospace; font-size: 12px; border: 1px solid #d1d5db; padding: 10px; }
QLabel#InternetStatus { font-family: 'Orbitron', sans-serif; font-size: 11px; font-weight: bold; padding: 2px 8px; border-radius: 10px; background-color: #ffffff; border: 1px solid #d1d5db; color: #1f2937; }
QDialog { background-color: #f0f2f5; color: #1f2937; }
QPushButton#LogButton { background-color: #ffffff; border: 1px solid #d1d5db; font-size: 10px; padding: 4px 8px; min-width: 80px; color: #1f2937; }
QPushButton#LogButton:hover { background-color: #3b82f6; color: #ffffff; }
QScrollBar:vertical { border: none; background: #f0f2f5; width: 10px; }
QScrollBar::handle:vertical { background: #d1d5db; min-height: 20px; border-radius: 4px; }
QTableView#HexView { background-color: #ffffff; color: #065f46; font-family: 'Consolas', 'Monaco', monospace; font-size: 13px; border: 1px solid #d1d5db; gridline-color: transparent; selection-background-color: #bfdbfe; selection-color: #1e3a8a; }
QTableView#HexView::item { padding-left: 2px; padding-right: 2px; }
QHeaderView::section { background-color: #f3f4f6; border: none; font-family: 'Consolas', 'Monaco', monospace; font-size: 13px; padding: 2px 4px; text-align: left; color: #374151; }
QHeaderView::section:horizontal { color: #2563eb; }
QTableView QTableCornerButton::section { background-color: #f3f4f6; border: 1px solid #d1d5db; }
QPushButton#AdvancedButton { border: 1px solid #2563eb; color: #2563eb; }
QPushButton#AdvancedButton:disabled { background-color: #e5e7eb; color: #9ca3af; border: 1px solid #d1d5db; }
QPushButton#ThemeButtonDark { background-color: #ffffff; color: #6b7280; border: 1px solid #d1d5db; font-weight: bold; text-align: center; }
QPushButton#ThemeButtonDark:hover { background-color: #4b5563; color: #ffffff; }
QPushButton#ThemeButtonLight { background-color: #eff6ff; color: #2563eb; border: 2px solid #3b82f6; font-weight: bold; text-align: center; }
QPushButton#ThemeButtonLight:hover { background-color: #3b82f6; color: #ffffff; }
QWidget#HexWidget { background-color: #f0f2f5; }
QLabel#HexLabel { color: #2563eb; font-weight: bold; font-family: monospace; padding: 10px; }
QTabWidget::pane { border: 1px solid #d1d5db; background-color: #ffffff; }
QTabBar::tab { background-color: #f3f4f6; color: #4b5563; padding: 5px 15px; border: 1px solid #d1d5db; }
QTabBar::tab:selected { background-color: #ffffff; color: #2563eb; border-bottom: 2px solid #2563eb; }
QLabel { color: #1f2937; }
"""

class HexTableModel(QAbstractTableModel):
    # Fast character lookup table (Pre-calculating for Latin-1)
    CHARS_LOOKUP = [chr(b) if (32 <= b <= 126 or b >= 160) else "." for b in range(256)]

    def __init__(self, data=b"", parent=None):
        super().__init__(parent)
        from core_workspace import FirmwareDocument, event_bus
        if isinstance(data, FirmwareDocument):
            self.document = data
        else:
            self.document = FirmwareDocument(data=data)
            
        self.regions = []
        self.is_light_mode = False
        
        # Subscribe to document changes
        event_bus.document_modified.connect(self._on_document_modified)
        event_bus.bookmarks_changed.connect(self._on_bookmarks_changed)

    def _on_document_modified(self, doc):
        if doc == self.document:
            self.layoutChanged.emit()

    def _on_bookmarks_changed(self, doc):
        if doc == self.document:
            self.layoutChanged.emit()

    def set_regions(self, regions_map):
        self.regions = []
        if not regions_map:
            self.dataChanged.emit(self.index(0, 0), self.index(self.rowCount()-1, self.columnCount()-1), [Qt.ItemDataRole.ForegroundRole])
            return
        for key, info in regions_map.items():
            start = info.get("offset", 0)
            end = start + info.get("size", 0) - 1
            
            # Use dynamic color provided by bios_parser, fallback to White if not found
            color_hex = info.get("color", "#FFFFFF")
            color = QColor(color_hex)
            
            self.regions.append((start, end, color))
        
        # Trigger full view update for highlighting
        self.dataChanged.emit(self.index(0, 0), self.index(self.rowCount()-1, self.columnCount()-1), [Qt.ItemDataRole.ForegroundRole])
        self.headerDataChanged.emit(Qt.Orientation.Vertical, 0, self.rowCount()-1)

    def get_color_for_offset(self, offset):
        for start, end, color in self.regions:
            if start <= offset <= end:
                return color
        # Default: lighter grey for light mode, darker grey for dark mode
        return QColor("#4a4a4a") if self.is_light_mode else QColor("#4CAF50")

    def set_data(self, data):
        self.beginResetModel()
        from core_workspace import FirmwareDocument
        if isinstance(data, FirmwareDocument):
            self.document = data
        else:
            self.document = FirmwareDocument(data=data)
        self.endResetModel()

    def get_data(self):
        return self.document.data

    def insert_bytes(self, offset, count=1, insert_data=None):
        self.beginInsertRows(QModelIndex(), (offset)//16, (offset + count)//16)
        if insert_data is not None:
            self.document.insert_bytes(offset, insert_data)
        else:
            self.document.insert_bytes(offset, b'\x00' * count)
        self.endInsertRows()
        self.layoutChanged.emit()

    def remove_bytes(self, offset, count=1):
        if count <= 0: return
        self.beginResetModel()
        self.document.remove_bytes(offset, count)
        self.endResetModel()
        self.layoutChanged.emit()

    def replace_bytes(self, offset, new_bytes):
        count = len(new_bytes)
        if count <= 0 or offset >= self.document.size: return
        self.document.edit_bytes(offset, new_bytes)
        # Assuming edit_bytes emits layoutChanged via event_bus
        end = min(offset + count, self.document.size)
        self.dataChanged.emit(self.index(offset//16, 0), self.index((end)//16, 16))

    def search(self, query_bytes, direction="All", start_offset=0):
        results = []
        data = self.document.data
        if not data or not query_bytes: return results
        
        idx = data.find(query_bytes, 0)
        while idx != -1:
            results.append(idx)
            idx = data.find(query_bytes, idx + 1)
            
        if direction == "Forward":
            results = [r for r in results if r >= start_offset]
        elif direction == "Backward":
            results = [r for r in results if r <= start_offset]
            results.sort(reverse=True)
            
        return results

    def rowCount(self, parent=QModelIndex()):
        return (self.document.size + 15) // 16

    def columnCount(self, parent=QModelIndex()):
        return 17
        
    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.ItemIsEnabled
        
        # Make hex columns (0-15) editable
        if index.column() < 16:
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable
        # Decoded text column is read-only
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if role == Qt.ItemDataRole.EditRole and index.column() < 16:
            try:
                val = int(value, 16)
                if 0 <= val <= 255:
                    offset = index.row() * 16 + index.column()
                    if self.document.edit_byte(offset, val):
                        self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole])
                        text_index = self.index(index.row(), 16)
                        self.dataChanged.emit(text_index, text_index, [Qt.ItemDataRole.DisplayRole])
                        return True
            except ValueError:
                return False
        return False

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        
        row = index.row()
        col = index.column()
        offset = row * 16 + col
        
        doc_data = self.document.data
        doc_size = self.document.size
        
        if role == Qt.ItemDataRole.DisplayRole:
            if col < 16:
                if offset < doc_size:
                    return f"{doc_data[offset]:02X}"
                return ""
            else:
                start = row * 16
                end = min(start + 16, doc_size)
                chunk = doc_data[start:end]
                # Fast lookup instead of conditional chr() calling
                return "".join(self.CHARS_LOOKUP[b] for b in chunk)
                
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col < 16:
                return int(Qt.AlignmentFlag.AlignCenter)
            return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
        elif role == Qt.ItemDataRole.ForegroundRole:
            if col < 16:
                return self.get_color_for_offset(offset)
            elif col == 16:
                return self.get_color_for_offset(row * 16)
            return None
            
        elif role == Qt.ItemDataRole.BackgroundRole:
            if col < 16 and offset < doc_size:
                if offset in self.document.bookmarks:
                    color = self.document.bookmarks[offset].get('color', '#4CAF50')
                    # Make it slightly transparent so text is readable
                    return QColor(color).darker(300)
            return None
            
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                if section < 16:
                    return f"{section:02X}"
                return "Decoded text"
            else:
                return f"{section * 16:08X}"
        elif role == Qt.ItemDataRole.ForegroundRole:
            if orientation == Qt.Orientation.Vertical:
                return self.get_color_for_offset(section * 16)
        return None

from PySide6.QtCore import QObject, QEvent, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QPainter, QPainterPath, QFont

class HamburgerButton(QWidget):
    """A custom widget that draws 3 horizontal lines (hamburger icon)."""
    clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(44, 44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Menu")
        self._hovered = False
        
    def enterEvent(self, event):
        self._hovered = True
        self.update()
        
    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        
        # Hover background
        if self._hovered:
            painter.setBrush(QBrush(QColor(42, 196, 219, 35)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(2, 2, w-4, h-4, 6, 6)
        
        # Draw 3 lines
        pen = QPen(QColor("#4cd3e3"), 3.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        line_w = 22
        x_start = (w - line_w) // 2
        for y_offset in [-6, 0, 6]:
            y = h // 2 + y_offset
            painter.drawLine(x_start, y, x_start + line_w, y)
        painter.end()


class AnimatedToolbarMenu(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._root_layout = QHBoxLayout(self)
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(5)
        self.setFixedHeight(38)
        
        # Hamburger Button - hidden since options are now directly visible
        self.btn_menu = HamburgerButton()
        self.btn_menu.clicked.connect(self.toggle_menu)
        self.btn_menu.hide()
        self._root_layout.addWidget(self.btn_menu)
        
        # Container for text buttons (Driver Stealth Style)
        self.menu_container = QFrame()
        self.menu_container.setObjectName("MenuContainer")
        self.menu_container.setStyleSheet("""
            QFrame#MenuContainer { background: transparent; border: none; }
            QPushButton {
                background: #0d1117;
                color: #00f2ff;
                border: 1px solid #30363d;
                border-radius: 4px;
                padding: 4px 14px;
                margin: 0px 3px;
                min-height: 28px;
                max-height: 28px;
                font-family: 'Orbitron', 'Segoe UI', sans-serif;
                font-size: 11px;
                font-weight: 800;
                letter-spacing: 1px;
                text-align: center;
            }
            QPushButton:hover {
                background: #161b22;
                border: 1px solid #00f2ff;
                color: #ffffff;
            }
            QPushButton:pressed {
                background: #00f2ff;
                color: #000000;
                border: 1px solid #00f2ff;
                font-weight: 900;
            }
            QPushButton:disabled {
                background: #0d1117;
                color: #484f58;
                border: 1px solid #21262d;
            }
        """)
        self.menu_layout = QHBoxLayout(self.menu_container)
        self.menu_layout.setContentsMargins(4, 0, 4, 0)
        self.menu_layout.setSpacing(6)
        
        self._root_layout.addWidget(self.menu_container)
        self._root_layout.addStretch()
        
        # Options are permanently visible outside (no auto-hiding/collapsing)
        self.is_expanded = True
        self.menu_container.setMaximumWidth(16777215)
        self.menu_container.setMinimumWidth(0)
        
    def eventFilter(self, obj, event):
        return False

    def enterEvent(self, event):
        super().enterEvent(event)

    def leaveEvent(self, event):
        super().leaveEvent(event)
        
    def add_widget(self, widget):
        self.menu_layout.addWidget(widget)
        
    def toggle_menu(self):
        pass
            
    def expand_menu(self):
        self.menu_container.setMaximumWidth(16777215)
        self.is_expanded = True
            
    def collapse_menu(self):
        # Kept permanently outside as requested
        pass


class ThemeToggleSwitch(QWidget):
    """A premium pill-shaped toggle switch for Dark / Light mode."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_light = False
        self._knob_x = 4   # Current knob X position (animated)
        self.setFixedSize(75, 36)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Toggle Dark / Light mode")

        # Animation for the knob
        self._anim = QPropertyAnimation(self, b"knob_x", self)
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

    def get_knob_x(self):
        return self._knob_x

    def set_knob_x(self, val):
        self._knob_x = val
        self.update()

    knob_x = Property(int, get_knob_x, set_knob_x)

    def set_state(self, is_light: bool, animate=True):
        self._is_light = is_light
        w = self.width()
        h = self.height()
        knob_size = h - 4
        end_x = w - knob_size - 2 if is_light else 2
        if animate:
            self._anim.stop()
            self._anim.setStartValue(self._knob_x)
            self._anim.setEndValue(end_x)
            self._anim.start()
        else:
            self._knob_x = end_x
            self.update()

    def mousePressEvent(self, event):
        self._is_light = not self._is_light
        self.set_state(self._is_light)
        # Notify main window
        main = self.window()
        if hasattr(main, 'apply_theme'):
            main.apply_theme(self._is_light)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        radius = h // 2
        knob_size = h - 4

        # Track colors
        if self._is_light:
            track_color = QColor("#3b82f6")    # Blue for light mode
            knob_color  = QColor("#ffffff")
            text_color  = QColor("#ffffff")
            label = "LIGHT"
        else:
            track_color = QColor("#1a1d2e")    # Dark for dark mode
            knob_color  = QColor("#00f3ff")
            text_color  = QColor("#00f3ff")
            label = "DARK"

        # Draw track (pill)
        track_path = QPainterPath()
        track_path.addRoundedRect(0, 0, w, h, radius, radius)
        painter.fillPath(track_path, track_color)

        # Border glow
        from PySide6.QtGui import QPen
        border_pen = QPen(knob_color, 1)
        painter.setPen(border_pen)
        painter.drawPath(track_path)

        # Draw label text (opposite side of knob)
        font = QFont("Orbitron", 5, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(text_color)
        if self._is_light:
            # knob on right ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ text on left
            painter.drawText(4, 0, self._knob_x - 2, h, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, label)
        else:
            # knob on left ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ text on right
            text_x = self._knob_x + knob_size + 2
            painter.drawText(text_x, 0, w - text_x - 2, h, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, label)

        # Draw knob circle
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(knob_color)
        painter.drawEllipse(self._knob_x, 2, knob_size, knob_size)

        painter.end()


class HexToggleSwitch(QWidget):
    """A premium pill-shaped toggle switch for Hex Viewer."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_on = False
        self._knob_x = 4
        self.setFixedSize(75, 36)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Toggle Hex Viewer (Detached)")

        self._anim = QPropertyAnimation(self, b"knob_x", self)
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

    def get_knob_x(self):
        return self._knob_x

    def set_knob_x(self, val):
        self._knob_x = val
        self.update()

    knob_x = Property(int, get_knob_x, set_knob_x)

    def set_state(self, is_on: bool, animate=True):
        self._is_on = is_on
        w = self.width()
        h = self.height()
        knob_size = h - 4
        end_x = w - knob_size - 2 if is_on else 2
        if animate:
            self._anim.stop()
            self._anim.setStartValue(self._knob_x)
            self._anim.setEndValue(end_x)
            self._anim.start()
        else:
            self._knob_x = end_x
            self.update()

    def mousePressEvent(self, event):
        self._is_on = not self._is_on
        self.set_state(self._is_on)
        main = self.window()
        if hasattr(main, 'toggle_hex_viewer_mode'):
            main.toggle_hex_viewer_mode(self._is_on)
            from PySide6.QtCore import QSettings
            settings = QSettings("R1AILAB", "BIOS_TOOL")
            settings.setValue("detached_hex_viewer", self._is_on)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        radius = h // 2
        knob_size = h - 4

        if self._is_on:
            track_color = QColor("#00f3ff")
            knob_color  = QColor("#0e0f1a")
            text_color  = QColor("#0e0f1a")
            label = "HEX ON"
        else:
            track_color = QColor("#1a1d2e")
            knob_color  = QColor("#00f3ff")
            text_color  = QColor("#00f3ff")
            label = "HEX OFF"

        track_path = QPainterPath()
        track_path.addRoundedRect(0, 0, w, h, radius, radius)
        painter.fillPath(track_path, track_color)

        from PySide6.QtGui import QPen
        border_pen = QPen(QColor("#00f3ff"), 1)
        painter.setPen(border_pen)
        painter.drawPath(track_path)

        font = QFont("Orbitron", 5, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(text_color)
        if self._is_on:
            painter.drawText(4, 0, self._knob_x - 2, h, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, label)
        else:
            text_x = self._knob_x + knob_size + 2
            painter.drawText(text_x, 0, w - text_x - 2, h, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, label)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(knob_color)
        painter.drawEllipse(self._knob_x, 2, knob_size, knob_size)

        painter.end()


class HexWidgetEventFilter(QObject):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Close and obj == self.main_window.hex_widget:
            # Re-dock it
            self.main_window.toggle_hex_viewer_mode(False)
            if hasattr(self.main_window, 'hex_toggle'):
                self.main_window.hex_toggle.set_state(False, animate=True)
            from PySide6.QtCore import QSettings
            settings = QSettings("R1AILAB", "BIOS_TOOL")
            settings.setValue("detached_hex_viewer", False)
            event.ignore() # Prevent actual destruction
            return True
        elif event.type() == QEvent.Type.DragEnter and obj in (self.main_window.hex_widget, getattr(self.main_window, 'hex_tabs', None)):
            if event.mimeData().hasUrls():
                event.acceptProposedAction()
                return True
        elif event.type() == QEvent.Type.Drop and obj in (self.main_window.hex_widget, getattr(self.main_window, 'hex_tabs', None)):
            urls = event.mimeData().urls()
            if urls:
                file_path = urls[0].toLocalFile()
                try:
                    with open(file_path, "rb") as f:
                        data = f.read()
                    import os
                    title = os.path.basename(file_path)
                    # Adding a new tab to hex viewer without affecting main workspace
                    tab = self.main_window.add_new_hex_tab(title, data, file_path=file_path)
                    tab.mark_clean()
                    if hasattr(self.main_window, 'switch_display_tab'):
                        self.main_window.switch_display_tab("HEX")
                except Exception as e:
                    print(f"Error loading dropped file into Hex Viewer: {e}")
            event.acceptProposedAction()
            return True
        return False

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(370, 170)
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #252a2e, stop:1 #1c2024);
                border: 1px solid #2d363f;
                color: #e2e8f0;
                font-family: 'Segoe UI', sans-serif;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(12)
        
        self.cb_detach_hex = QCheckBox("Show Hex Viewer (Floating)")
        self.cb_detach_hex.setStyleSheet("""
            QCheckBox { color: #e2e8f0; font-size: 12px; font-weight: 600; }
            QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #283038; border-radius: 4px; background: #14171a; }
            QCheckBox::indicator:checked { background: #2ac4db; border-color: #0ef6fd; }
        """)
        
        from PySide6.QtCore import QSettings
        self.settings = QSettings("R1AILAB", "BIOS_TOOL")
        self.cb_detach_hex.setChecked(self.settings.value("detached_hex_viewer", False, type=bool))
        
        layout.addWidget(self.cb_detach_hex)
        
        self.btn_report_settings = QPushButton("⚙ Configure Scanning Report")
        self.btn_report_settings.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #252a2e, stop:1 #1c2024);
                color: #4cd3e3;
                border: 1px solid #2ac4db;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background: #2ac4db;
                color: #0b151a;
            }
        """)
        self.btn_report_settings.clicked.connect(self.open_report_settings)
        layout.addWidget(self.btn_report_settings)
        
        layout.addStretch()
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3c444a, stop:1 #2d3338);
                color: #c8d6e0;
                border: 1px solid #4a545c;
                border-radius: 6px;
                padding: 5px 16px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover {
                background: #47525a;
                color: #ffffff;
            }
        """)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def accept(self):
        from PySide6.QtCore import QSettings
        settings = QSettings("R1AILAB", "BIOS_TOOL")
        settings.setValue("detached_hex_viewer", self.cb_detach_hex.isChecked())
        super().accept()

    def open_report_settings(self):
        from report_settings_ui import ReportSettingsDialog
        main_win = self.parent()
        if hasattr(main_win, 'report_manager'):
            dlg = ReportSettingsDialog(main_win.report_manager, self)
            if dlg.exec():
                if getattr(main_win, 'current_bios_file', None) and os.path.exists(main_win.current_bios_file):
                    main_win.log_to_terminal("[INFO] Report settings updated. Refreshing analysis...")
                    main_win.load_bios_file(main_win.current_bios_file)

class HexSearchDialog(QDialog):
    """Professional Advanced Search Dialog with Find Next/Prev/All, history, and live results."""
    
    _STYLE = """
        QDialog { background-color: #171a1d; color: #e2e8f0; font-family: 'Segoe UI', sans-serif; }
        QLabel  { color: #4cd3e3; font-weight: bold; font-size: 11px; }
        QLineEdit {
            background-color: #14171a; color: #ffffff;
            border: 1px solid #283038; border-radius: 6px; padding: 5px 8px;
            font-family: Consolas, monospace; font-size: 12px;
        }
        QLineEdit:focus { border-color: #2ac4db; }
        QComboBox {
            background-color: #14171a; color: #ffffff;
            border: 1px solid #283038; border-radius: 6px; padding: 4px 8px;
        }
        QComboBox QAbstractItemView { background-color: #14171a; color: #ffffff; }
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #252a2e, stop:1 #1c2024);
            color: #c8d6e0; border: 1px solid #333d47; border-radius: 6px;
            padding: 6px 14px; font-weight: 600; font-size: 11px;
        }
        QPushButton:hover  { background-color: #2f373f; color: #4cd3e3; border-color: #2ac4db; }
        QPushButton:pressed { background-color: #00e0ed; color: #000000; }
        QPushButton#FindAll {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8fe3ea, stop:0.4 #3598a6, stop:1 #247d8a);
            border: 1px solid #0ef6fd; color: #0d171c; font-weight: bold;
        }
        QPushButton#FindAll:hover { background: #0ef6fd; color: #000000; }
        QTableView {
            background-color: #14171a; color: #4cd3e3;
            gridline-color: #242930; border: 1px solid #283038; border-radius: 6px;
            font-family: Consolas, monospace; font-size: 11px;
            selection-background-color: #1f4a56;
        }
        QTableView QHeaderView::section {
            background-color: #1a1e22; color: #94a3b8;
            border: 1px solid #283038; padding: 4px;
            font-weight: bold;
        }
        QCheckBox { color: #94a3b8; }
        QCheckBox::indicator { width: 14px; height: 14px; border: 1px solid #283038; border-radius: 3px; background: #14171a; }
        QCheckBox::indicator:checked { background-color: #2ac4db; border-color: #0ef6fd; }
        QStatusBar, QLabel#status { color: #888888; font-size: 10px; font-weight: normal; }
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Advanced Search")
        self.setMinimumSize(580, 460)
        self.setStyleSheet(self._STYLE)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self._results = []
        self._current_idx = -1
        self._search_history = []

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(14, 12, 14, 10)

        # ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ Search Input ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Search:"))
        self.search_input = QComboBox()
        self.search_input.setEditable(True)
        self.search_input.setMinimumWidth(320)
        self.search_input.lineEdit().setPlaceholderText("Enter hex (e.g. 55 AA) or text...")
        self.search_input.lineEdit().returnPressed.connect(self.find_all)
        row1.addWidget(self.search_input, 1)
        layout.addLayout(row1)

        # ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ Options ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Hex Values", "ASCII Text", "Unicode Text"])
        self.type_combo.currentIndexChanged.connect(self._update_placeholder)
        row2.addWidget(self.type_combo)
        row2.addSpacing(12)
        self.case_check = QCheckBox("Case-sensitive")
        row2.addWidget(self.case_check)
        row2.addStretch()
        layout.addLayout(row2)

        # ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ Buttons ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬
        btn_row = QHBoxLayout()
        self.btn_prev = QPushButton("ÃƒÂ¢Ã¢â‚¬â€Ã¢â€šÂ¬  Prev")
        self.btn_prev.setToolTip("Find Previous  (Shift+F3)")
        self.btn_prev.clicked.connect(self.find_prev)
        self.btn_next = QPushButton("Next  ÃƒÂ¢Ã¢â‚¬â€œÃ‚Â¶")
        self.btn_next.setToolTip("Find Next  (F3)")
        self.btn_next.clicked.connect(self.find_next)
        self.btn_all  = QPushButton("Find All")
        self.btn_all.setObjectName("FindAll")
        self.btn_all.setToolTip("Find all matches and list them below")
        self.btn_all.clicked.connect(self.find_all)
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.close)

        for b in (self.btn_prev, self.btn_next, self.btn_all, btn_close):
            btn_row.addWidget(b)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ Divider ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #1f2233;")
        layout.addWidget(line)

        # ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ Results Table ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬
        results_header = QHBoxLayout()
        results_header.addWidget(QLabel("Search Results:"))
        self.status_label = QLabel("")
        self.status_label.setObjectName("status")
        results_header.addStretch()
        results_header.addWidget(self.status_label)
        layout.addLayout(results_header)

        self.results_table = QTableView()
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.results_table.verticalHeader().hide()
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.doubleClicked.connect(self._on_result_double_clicked)
        self.results_table.setAlternatingRowColors(True)
        layout.addWidget(self.results_table, 1)

        # Keyboard shortcuts
        QShortcut(QKeySequence("F3"),       self).activated.connect(self.find_next)
        QShortcut(QKeySequence("Shift+F3"), self).activated.connect(self.find_prev)
        QShortcut(QKeySequence("Return"),   self).activated.connect(self.find_all)

    def _update_placeholder(self):
        t = self.type_combo.currentText()
        if t == "Hex Values":
            self.search_input.lineEdit().setPlaceholderText("e.g.  55 AA FF 00")
        elif t == "ASCII Text":
            self.search_input.lineEdit().setPlaceholderText("e.g.  BIOS")
        else:
            self.search_input.lineEdit().setPlaceholderText("e.g.  Aptio")

    def _get_query_bytes(self):
        raw = self.search_input.currentText().strip()
        if not raw:
            return None
        stype = self.type_combo.currentText()
        try:
            if stype == "Hex Values":
                return bytes.fromhex(raw.replace(" ", "").replace("-", ""))
            elif stype == "ASCII Text":
                if self.case_check.isChecked():
                    return raw.encode("latin-1", errors="replace")
                else:
                    return raw.lower().encode("latin-1", errors="replace")
            else:  # Unicode
                return raw.encode("utf-16-le", errors="replace")
        except Exception:
            return None

    def _get_editor_tab(self):
        """Return the current HexEditorTab from the parent BiosServiceTool."""
        p = self.parent()
        if p and hasattr(p, 'hex_tabs') and p.hex_tabs.count() > 0:
            return p.hex_tabs.currentWidget()
        return None

    def find_all(self):
        query = self._get_query_bytes()
        if query is None:
            self.status_label.setText("ÃƒÂ¢Ã…Â¡Ã‚Â  Invalid query")
            return
        tab = self._get_editor_tab()
        if not tab:
            self.status_label.setText("ÃƒÂ¢Ã…Â¡Ã‚Â  No file loaded")
            return

        data = bytes(tab.hex_model.get_data())
        search_data = data.lower() if (self.type_combo.currentText() == "ASCII Text" and not self.case_check.isChecked()) else data

        # Build results
        self._results = []
        idx = search_data.find(query, 0)
        while idx != -1:
            chunk = data[idx:min(idx+16, len(data))]
            hex_str  = " ".join(f"{b:02X}" for b in chunk)
            text_str = "".join(tab.hex_model.CHARS_LOOKUP[b] for b in chunk)
            self._results.append({'offset': idx, 'hex': hex_str, 'text': text_str})
            idx = search_data.find(query, idx + 1)

        # Update history
        raw = self.search_input.currentText().strip()
        if raw and raw not in self._search_history:
            self._search_history.insert(0, raw)
            self.search_input.insertItem(0, raw)
            self._search_history = self._search_history[:20]

        count = len(self._results)
        if count == 0:
            self.status_label.setText("No matches found")
        else:
            self.status_label.setText(f"{count} match{'es' if count != 1 else ''} found")

        self._current_idx = 0 if self._results else -1
        mdl = SearchResultsModel(self._results)
        self.results_table.setModel(mdl)
        self.results_table.resizeColumnsToContents()
        if self._results:
            self._jump_to(0)

    def find_next(self):
        if not self._results:
            self.find_all()
            return
        self._current_idx = (self._current_idx + 1) % len(self._results)
        self._jump_to(self._current_idx)

    def find_prev(self):
        if not self._results:
            self.find_all()
            return
        self._current_idx = (self._current_idx - 1) % len(self._results)
        self._jump_to(self._current_idx)

    def _jump_to(self, result_idx):
        if result_idx < 0 or result_idx >= len(self._results):
            return
        res = self._results[result_idx]
        tab = self._get_editor_tab()
        if not tab:
            return
        offset = res['offset']
        row = offset // 16
        col = offset % 16
        idx = tab.hex_model.index(row, col)
        tab.hex_view.selectionModel().clearSelection()
        from PySide6.QtCore import QItemSelectionModel
        tab.hex_view.selectionModel().select(idx, QItemSelectionModel.SelectionFlag.Select)
        tab.hex_view.scrollTo(idx, QAbstractItemView.ScrollHint.PositionAtCenter)
        # Highlight current row in results table
        self.results_table.selectRow(result_idx)
        n = len(self._results)
        self.status_label.setText(f"{result_idx + 1} / {n} matches")

    def _on_result_double_clicked(self, index):
        self._current_idx = index.row()
        self._jump_to(self._current_idx)

    def get_search_params(self):
        """Legacy compat: returns dict for show_find_dialog to consume."""
        stype = self.type_combo.currentText()
        return {
            "query": self.search_input.currentText(),
            "type": "Hex-values" if stype == "Hex Values" else "Text-string",
            "direction": "All"
        }


class GotoOffsetDialog(QDialog):
    """Jump-to-Offset dialog: accepts HEX or DEC input."""

    _STYLE = """
        QDialog { background-color: #171a1d; color: #e2e8f0; font-family: 'Segoe UI', sans-serif; }
        QLabel  { color: #4cd3e3; font-weight: bold; font-size: 11px; }
        QLineEdit {
            background-color: #14171a; color: #ffffff;
            border: 1px solid #283038; border-radius: 6px; padding: 6px 10px;
            font-family: Consolas; font-size: 13px;
        }
        QLineEdit:focus { border-color: #2ac4db; }
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8fe3ea, stop:0.4 #3598a6, stop:1 #247d8a);
            color: #0d171c; border: 1px solid #0ef6fd; border-radius: 6px; padding: 6px 16px; font-weight: bold;
        }
        QPushButton:hover { background: #0ef6fd; color: #000; }
        QRadioButton { color: #94a3b8; font-weight: 600; }
        QRadioButton::indicator:checked { background: #2ac4db; border: 2px solid #0ef6fd; border-radius: 6px; }
    """

    def __init__(self, file_size=0, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Go To Offset")
        self.setFixedSize(340, 175)
        self.setStyleSheet(self._STYLE)
        self.file_size = file_size

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 14, 16, 12)

        layout.addWidget(QLabel("Jump to Offset:"))

        self.offset_input = QLineEdit()
        self.offset_input.setPlaceholderText("e.g.  0x1A2B3C  or  1721148")
        self.offset_input.returnPressed.connect(self.accept)
        layout.addWidget(self.offset_input)

        # Mode: HEX / DEC
        mode_row = QHBoxLayout()
        from PySide6.QtWidgets import QRadioButton, QButtonGroup
        self.rb_auto = QRadioButton("Auto-detect")
        self.rb_hex  = QRadioButton("Hex")
        self.rb_dec  = QRadioButton("Decimal")
        self.rb_auto.setChecked(True)
        self._mode_group = QButtonGroup(self)
        for i, rb in enumerate((self.rb_auto, self.rb_hex, self.rb_dec)):
            self._mode_group.addButton(rb, i)
            mode_row.addWidget(rb)
        layout.addLayout(mode_row)

        if file_size > 0:
            size_label = QLabel(f"File size: {file_size:,} bytes  (0x{file_size:X})")
            size_label.setStyleSheet("color: #555; font-size: 10px; font-weight: normal;")
            layout.addWidget(size_label)

        btn_row = QHBoxLayout()
        btn_go = QPushButton("Go")
        btn_go.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_go)
        layout.addLayout(btn_row)

    def get_offset(self):
        text = self.offset_input.text().strip()
        if not text:
            return None
        try:
            mode_id = self._mode_group.checkedId()
            if mode_id == 0:  # Auto
                if text.startswith("0x") or text.startswith("0X"):
                    return int(text, 16)
                elif all(c in "0123456789abcdefABCDEF" for c in text) and len(text) >= 4:
                    return int(text, 16)
                else:
                    return int(text)
            elif mode_id == 1:  # Hex
                return int(text.replace("0x", "").replace("0X", ""), 16)
            else:  # Dec
                return int(text)
        except ValueError:
            return None


class HexFillDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Advanced Fill")
        self.setFixedSize(340, 180)
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #252a2e, stop:1 #1c2024);
                border: 1px solid #2d363f;
                color: #e2e8f0;
                font-family: 'Segoe UI', sans-serif;
            }
            QLabel { color: #4cd3e3; font-weight: bold; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 12)
        layout.setSpacing(8)
        
        self.radio_00 = QRadioButton("Fill with 00 (Zeros)")
        self.radio_FF = QRadioButton("Fill with FF (Blank)")
        self.radio_custom = QRadioButton("Custom Hex:")
        self.radio_00.setChecked(True)
        
        radio_style = "color: #c8d6e0; font-weight: 600;"
        self.radio_00.setStyleSheet(radio_style)
        self.radio_FF.setStyleSheet(radio_style)
        self.radio_custom.setStyleSheet(radio_style)
        
        layout.addWidget(self.radio_00)
        layout.addWidget(self.radio_FF)
        
        h_custom = QHBoxLayout()
        h_custom.addWidget(self.radio_custom)
        self.custom_input = QLineEdit()
        self.custom_input.setPlaceholderText("e.g. 90 or AA 55")
        self.custom_input.setStyleSheet("background-color: #14171a; color: #ffffff; border: 1px solid #283038; border-radius: 4px; padding: 4px 8px; font-family: Consolas;")
        self.custom_input.setEnabled(False)
        self.radio_custom.toggled.connect(self.custom_input.setEnabled)
        h_custom.addWidget(self.custom_input)
        layout.addLayout(h_custom)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3c444a, stop:1 #2d3338);
                color: #c8d6e0;
                border: 1px solid #4a545c;
                border-radius: 6px;
                padding: 6px 16px;
                font-weight: 600;
            }
            QPushButton:hover { background: #47525a; color: #ffffff; }
        """)
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_ok = QPushButton("Fill")
        self.btn_ok.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8fe3ea, stop:0.4 #3598a6, stop:1 #247d8a);
                color: #0d171c;
                border: 1px solid #0ef6fd;
                border-radius: 6px;
                font-weight: bold;
                padding: 6px 18px;
            }
            QPushButton:hover { background: #0ef6fd; color: #000; }
        """)
        self.btn_ok.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_ok)
        layout.addLayout(btn_layout)

    def get_fill_bytes(self):
        if self.radio_00.isChecked():
            return b'\x00'
        if self.radio_FF.isChecked():
            return b'\xFF'
        try:
            hex_str = self.custom_input.text().replace(" ", "")
            if not hex_str: return None
            return bytes.fromhex(hex_str)
        except ValueError:
            return None

class AddBookmarkDialog(QDialog):
    def __init__(self, offset, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Bookmark")
        self.setFixedSize(320, 160)
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #252a2e, stop:1 #1c2024);
                border: 1px solid #2d363f;
                color: #e2e8f0;
                font-family: 'Segoe UI', sans-serif;
            }
            QLabel { color: #4cd3e3; font-weight: bold; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 12)
        layout.setSpacing(10)
        
        layout.addWidget(QLabel(f"Bookmark Offset: 0x{offset:08X}"))
        
        h_name = QHBoxLayout()
        h_name.addWidget(QLabel("Name:"))
        self.name_input = QLineEdit()
        self.name_input.setStyleSheet("background-color: #14171a; color: #ffffff; border: 1px solid #283038; border-radius: 4px; padding: 4px 8px; font-family: Consolas;")
        h_name.addWidget(self.name_input)
        layout.addLayout(h_name)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3c444a, stop:1 #2d3338);
                color: #c8d6e0;
                border: 1px solid #4a545c;
                border-radius: 6px;
                padding: 6px 16px;
                font-weight: 600;
            }
            QPushButton:hover { background: #47525a; color: #ffffff; }
        """)
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_ok = QPushButton("Add")
        self.btn_ok.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8fe3ea, stop:0.4 #3598a6, stop:1 #247d8a);
                color: #0d171c;
                border: 1px solid #0ef6fd;
                border-radius: 6px;
                font-weight: bold;
                padding: 6px 18px;
            }
            QPushButton:hover { background: #0ef6fd; color: #000; }
        """)
        self.btn_ok.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_ok)
        layout.addLayout(btn_layout)
        
    def get_name(self):
        return self.name_input.text().strip()


class HexSelectBlockDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Block")
        self.setFixedSize(330, 170)
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #252a2e, stop:1 #1c2024);
                border: 1px solid #2d363f;
                color: #e2e8f0;
                font-family: 'Segoe UI', sans-serif;
            }
            QLabel { color: #4cd3e3; font-weight: bold; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 12)
        layout.setSpacing(10)
        
        h_start = QHBoxLayout()
        h_start.addWidget(QLabel("Start Offset (hex):"))
        self.start_input = QLineEdit()
        self.start_input.setStyleSheet("background-color: #14171a; color: #ffffff; border: 1px solid #283038; border-radius: 4px; padding: 4px 8px; font-family: Consolas;")
        h_start.addWidget(self.start_input)
        layout.addLayout(h_start)
        
        h_end = QHBoxLayout()
        h_end.addWidget(QLabel("End Offset (hex):"))
        self.end_input = QLineEdit()
        self.end_input.setStyleSheet("background-color: #14171a; color: #ffffff; border: 1px solid #283038; border-radius: 4px; padding: 4px 8px; font-family: Consolas;")
        h_end.addWidget(self.end_input)
        layout.addLayout(h_end)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3c444a, stop:1 #2d3338);
                color: #c8d6e0;
                border: 1px solid #4a545c;
                border-radius: 6px;
                padding: 6px 16px;
                font-weight: 600;
            }
            QPushButton:hover { background: #47525a; color: #ffffff; }
        """)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def get_offsets(self):
        try:
            start = int(self.start_input.text(), 16)
            end = int(self.end_input.text(), 16)
            return start, end
        except ValueError:
            return None, None

class SearchResultsModel(QAbstractTableModel):
    def __init__(self, results, parent=None):
        super().__init__(parent)
        self.results = results # list of dicts: {'offset': int, 'hex': str, 'text': str}
        
    def rowCount(self, parent=QModelIndex()): return len(self.results)
    def columnCount(self, parent=QModelIndex()): return 3
    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid(): return None
        if role == Qt.ItemDataRole.DisplayRole:
            res = self.results[index.row()]
            col = index.column()
            if col == 0: return f"{res['offset']:08X}"
            elif col == 1: return res['hex']
            elif col == 2: return res['text']
        return None
    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole: return None
        if orientation == Qt.Orientation.Horizontal:
            return ["Offset", "Excerpt (hex)", "Excerpt (text)"][section]
        return str(section)

class HexMinimap(QWidget):
    def __init__(self, hex_view, hex_model, parent=None):
        super().__init__(parent)
        self.hex_view = hex_view
        self.hex_model = hex_model
        self.setFixedWidth(20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Click to jump to region")
        
        self.hex_model.layoutChanged.connect(self.update)
        self.hex_model.dataChanged.connect(lambda tl, br, roles=[]: self.update())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#12141d"))
        
        total_size = len(self.hex_model.get_data())
        if total_size == 0 or not self.hex_model.regions:
            return
            
        height = self.height()
        width = self.width()
        
        regions_sorted = sorted(self.hex_model.regions, key=lambda x: x[0])
        current_y = 0
        for start, end, color in regions_sorted:
            y_start = max(current_y, (start / total_size) * height)
            y_end = (end / total_size) * height
            rect_height = max(3, y_end - y_start) # at least 3 pixels tall
            
            painter.fillRect(QRectF(0, y_start, width, rect_height), color)
            current_y = y_start + rect_height
            
    def mousePressEvent(self, event):
        self._navigate_to_y(event.position().y())

    def mouseMoveEvent(self, event):
        self._navigate_to_y(event.position().y())
        
    def wheelEvent(self, event):
        self.hex_view.wheelEvent(event)

    def _navigate_to_y(self, y):
        total_size = len(self.hex_model.get_data())
        if total_size == 0: return
        
        y = max(0, min(y, self.height()))
        offset = int((y / max(1, self.height())) * (total_size - 1)) if total_size > 0 else 0
        
        row = offset // 16
        idx = self.hex_model.index(row, 0)
        
        self.hex_view.selectionModel().clearSelection()
        from PySide6.QtCore import QItemSelectionModel
        select_flag = QItemSelectionModel.SelectionFlag.Select if hasattr(QItemSelectionModel, 'SelectionFlag') else QItemSelectionModel.SelectionFlag.Select
        self.hex_view.selectionModel().select(idx, select_flag)
        self.hex_view.scrollTo(idx, QAbstractItemView.ScrollHint.PositionAtTop)

import struct
from core_workspace import event_bus

class AnalysisPanel(QWidget):
    """Professional side panel for data inspection and file information."""
    
    _STYLE = """
        QWidget { background-color: #171a1d; color: #e2e8f0; font-family: 'Segoe UI', sans-serif; font-size: 11px; }
        QLabel { color: #94a3b8; }
        QLabel.value { color: #4cd3e3; font-family: Consolas, monospace; font-weight: bold; }
        QGroupBox {
            border: 1px solid #283038; border-radius: 6px;
            margin-top: 1ex; font-weight: bold; color: #4cd3e3;
        }
        QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 4px; }
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(250)
        self.setMaximumWidth(350)
        self.setStyleSheet(self._STYLE)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(10)

        # ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ Data Inspector ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬
        self.grp_data = QGroupBox("Data Inspector (Little Endian)")
        data_layout = QFormLayout(self.grp_data)
        data_layout.setContentsMargins(10, 15, 10, 10)
        data_layout.setSpacing(5)
        
        self.val_offset = QLabel("-")
        self.val_hex    = QLabel("-")
        self.val_bin    = QLabel("-")
        self.val_int8   = QLabel("-")
        self.val_uint8  = QLabel("-")
        self.val_int16  = QLabel("-")
        self.val_uint16 = QLabel("-")
        self.val_int32  = QLabel("-")
        self.val_uint32 = QLabel("-")
        
        for lbl in (self.val_offset, self.val_hex, self.val_bin, self.val_int8, self.val_uint8, self.val_int16, self.val_uint16, self.val_int32, self.val_uint32):
            lbl.setProperty("class", "value")
            lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            
        data_layout.addRow("Offset:", self.val_offset)
        data_layout.addRow("Hex:", self.val_hex)
        data_layout.addRow("Binary:", self.val_bin)
        data_layout.addRow("Int8:", self.val_int8)
        data_layout.addRow("UInt8:", self.val_uint8)
        data_layout.addRow("Int16:", self.val_int16)
        data_layout.addRow("UInt16:", self.val_uint16)
        data_layout.addRow("Int32:", self.val_int32)
        data_layout.addRow("UInt32:", self.val_uint32)
        main_layout.addWidget(self.grp_data)

        # ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ Selection Info ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬
        self.grp_sel = QGroupBox("Selection Information")
        sel_layout = QFormLayout(self.grp_sel)
        sel_layout.setContentsMargins(10, 15, 10, 10)
        
        self.sel_start  = QLabel("-")
        self.sel_end    = QLabel("-")
        self.sel_length = QLabel("-")
        
        for lbl in (self.sel_start, self.sel_end, self.sel_length):
            lbl.setProperty("class", "value")
            lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            
        sel_layout.addRow("Start:", self.sel_start)
        sel_layout.addRow("End:", self.sel_end)
        sel_layout.addRow("Length:", self.sel_length)
        main_layout.addWidget(self.grp_sel)

        # ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ File Info ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬
        self.grp_file = QGroupBox("File Information")
        file_layout = QFormLayout(self.grp_file)
        file_layout.setContentsMargins(10, 15, 10, 10)
        
        self.file_name = QLabel("-")
        self.file_size = QLabel("-")
        self.file_crc  = QLabel("-")
        self.file_sha  = QLabel("-")
        self.file_sha.setWordWrap(True)
        
        for lbl in (self.file_name, self.file_size, self.file_crc, self.file_sha):
            lbl.setProperty("class", "value")
            lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            
        file_layout.addRow("Name:", self.file_name)
        file_layout.addRow("Size:", self.file_size)
        file_layout.addRow("CRC32:", self.file_crc)
        file_layout.addRow("SHA256:", self.file_sha)
        main_layout.addWidget(self.grp_file)

        # ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ Bookmarks ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬
        self.grp_bookmarks = QGroupBox("Bookmarks")
        bk_layout = QVBoxLayout(self.grp_bookmarks)
        bk_layout.setContentsMargins(5, 10, 5, 5)
        
        self.bookmarks_list = QListWidget()
        self.bookmarks_list.setStyleSheet("""
            QListWidget { background-color: #12141d; border: 1px solid #1f2233; color: #ffffff; }
            QListWidget::item { padding: 4px; }
            QListWidget::item:selected { background-color: #004488; }
        """)
        self.bookmarks_list.itemDoubleClicked.connect(self._on_bookmark_double_clicked)
        bk_layout.addWidget(self.bookmarks_list)
        
        self.btn_del_bookmark = QPushButton("Remove Selected Bookmark")
        self.btn_del_bookmark.setStyleSheet("background-color: #2a2d3d; color: #ff3131; border: 1px solid #ff3131; border-radius: 3px; padding: 3px;")
        self.btn_del_bookmark.clicked.connect(self._on_remove_bookmark_clicked)
        bk_layout.addWidget(self.btn_del_bookmark)
        main_layout.addWidget(self.grp_bookmarks)

        main_layout.addStretch()

        # Connections
        event_bus.cursor_moved.connect(self._on_cursor_moved)
        event_bus.selection_changed.connect(self._on_selection_changed)
        event_bus.document_modified.connect(self._on_document_modified)
        event_bus.bookmarks_changed.connect(self._on_bookmarks_changed)
        
        self._current_doc = None

    @Slot(object, int)
    def _on_cursor_moved(self, doc, offset):
        if doc != self._current_doc:
            self._current_doc = doc
            self._update_file_info(doc)
            self._on_bookmarks_changed(doc)
            
        if doc is None or offset < 0 or offset >= doc.size:
            self._clear_inspector()
            return
            
        self.val_offset.setText(f"0x{offset:08X} ({offset})")
        
        # Read up to 4 bytes for inspection
        data = doc.get_data_slice(offset, offset + 4)
        if not data: return
        
        b0 = data[0]
        self.val_hex.setText(f"{b0:02X}")
        self.val_bin.setText(f"{b0:08b}")
        self.val_int8.setText(str(struct.unpack('<b', bytes([b0]))[0]))
        self.val_uint8.setText(str(b0))
        
        if len(data) >= 2:
            self.val_int16.setText(str(struct.unpack('<h', data[:2])[0]))
            self.val_uint16.setText(str(struct.unpack('<H', data[:2])[0]))
        else:
            self.val_int16.setText("-")
            self.val_uint16.setText("-")
            
        if len(data) >= 4:
            self.val_int32.setText(str(struct.unpack('<i', data[:4])[0]))
            self.val_uint32.setText(str(struct.unpack('<I', data[:4])[0]))
        else:
            self.val_int32.setText("-")
            self.val_uint32.setText("-")

    @Slot(object, int, int)
    def _on_selection_changed(self, doc, start, length):
        if doc != self._current_doc:
            self._current_doc = doc
            self._update_file_info(doc)
            self._on_bookmarks_changed(doc)
            
        if length <= 1:
            self.sel_start.setText("-")
            self.sel_end.setText("-")
            self.sel_length.setText("-")
            return
            
        end = start + length - 1
        self.sel_start.setText(f"0x{start:08X}")
        self.sel_end.setText(f"0x{end:08X}")
        self.sel_length.setText(f"0x{length:X} ({length:,})")

    @Slot(object)
    def _on_document_modified(self, doc):
        if self._current_doc == doc:
            self._update_file_info(doc, force_hash=False) # hashes are invalidated

    def _update_file_info(self, doc, force_hash=False):
        if not doc:
            self.file_name.setText("-")
            self.file_size.setText("-")
            self.file_crc.setText("-")
            self.file_sha.setText("-")
            return
            
        self.file_name.setText(doc.file_name + (" *" if doc.is_modified else ""))
        self.file_size.setText(f"0x{doc.size:X} ({doc.size:,} bytes)")
        
        if not doc._crc32 or not doc._sha256:
            if force_hash:
                doc.calculate_hashes()
                self.file_crc.setText(doc._crc32)
                self.file_sha.setText(doc._sha256)
            else:
                self.file_crc.setText("Not calculated")
                self.file_sha.setText("Not calculated")
        else:
            self.file_crc.setText(doc._crc32)
            self.file_sha.setText(doc._sha256)

    def _clear_inspector(self):
        self.val_offset.setText("-")
        self.val_hex.setText("-")
        self.val_bin.setText("-")
        self.val_int8.setText("-")
        self.val_uint8.setText("-")
        self.val_int16.setText("-")
        self.val_uint16.setText("-")
        self.val_int32.setText("-")
        self.val_uint32.setText("-")

    @Slot(object)
    def _on_bookmarks_changed(self, doc):
        if doc != self._current_doc:
            return
        self.bookmarks_list.clear()
        if not doc: return
        for offset in sorted(doc.bookmarks.keys()):
            bm = doc.bookmarks[offset]
            item = QListWidgetItem(f"0x{offset:08X} - {bm['name']}")
            item.setData(Qt.ItemDataRole.UserRole, offset)
            self.bookmarks_list.addItem(item)
            
    def _on_bookmark_double_clicked(self, item):
        offset = item.data(Qt.ItemDataRole.UserRole)
        # Find active HexEditorTab and scroll to it
        main_win = self.window()
        if hasattr(main_win, 'hex_tabs'):
            current_tab = main_win.hex_tabs.currentWidget()
            if current_tab and hasattr(current_tab, 'hex_view'):
                current_tab.hex_view.clearSelection()
                row = offset // 16
                col = offset % 16
                idx = current_tab.hex_model.index(row, col)
                from PySide6.QtCore import QItemSelectionModel
                select_flag = QItemSelectionModel.SelectionFlag.Select if hasattr(QItemSelectionModel, 'SelectionFlag') else QItemSelectionModel.SelectionFlag.Select
                current_tab.hex_view.selectionModel().select(idx, select_flag)
                current_tab.hex_view.scrollTo(idx, QAbstractItemView.ScrollHint.PositionAtCenter)

    def _on_remove_bookmark_clicked(self):
        item = self.bookmarks_list.currentItem()
        if item and self._current_doc:
            offset = item.data(Qt.ItemDataRole.UserRole)
            self._current_doc.remove_bookmark(offset)

class HexSearchBar(QFrame):
    def __init__(self, hex_view, hex_model, parent=None):
        super().__init__(parent)
        self.hex_view = hex_view
        self.hex_model = hex_model
        self._results = []
        self._current_idx = -1
        
        self.setObjectName("HexSearchBar")
        self.setStyleSheet("""
            QFrame#HexSearchBar {
                background-color: #1a1d2e;
                border: 1px solid #00f3ff;
                border-radius: 4px;
            }
            QLabel { color: #00f3ff; font-weight: bold; font-size: 11px; }
            QLineEdit {
                background-color: #12141d; color: #ffffff;
                border: 1px solid #1f2233; border-radius: 2px; padding: 2px 4px;
                font-family: Consolas, monospace; font-size: 11px;
            }
            QLineEdit:focus { border-color: #00f3ff; }
            QComboBox {
                background-color: #12141d; color: #ffffff;
                border: 1px solid #1f2233; border-radius: 2px; padding: 2px 4px;
                font-size: 11px;
            }
            QPushButton {
                background-color: #1a1d2e; color: #00f3ff;
                border: 1px solid #1f2233; border-radius: 2px;
                padding: 2px 6px; font-weight: bold; font-size: 11px;
            }
            QPushButton:hover { background-color: #00f3ff; color: #000000; }
            QPushButton#btnClose { border: none; color: #ff5555; font-size: 12px; font-weight: bold; }
            QPushButton#btnClose:hover { background-color: #ff5555; color: #ffffff; }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(6)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Find...")
        self.search_input.setMinimumWidth(150)
        self.search_input.returnPressed.connect(self._on_enter_pressed)
        
        self.btn_find = QPushButton("Find")
        self.btn_find.setToolTip("Run Search")
        self.btn_find.clicked.connect(self._run_search)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Hex Value", "Text"])
        
        self.lbl_count = QLabel("0 of 0")
        self.lbl_count.setMinimumWidth(50)
        self.lbl_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.btn_prev = QPushButton("ÃƒÂ¢Ã¢â‚¬â€œÃ‚Â²")
        self.btn_prev.setToolTip("Previous (Shift+F3)")
        self.btn_prev.clicked.connect(self._go_prev)
        
        self.btn_next = QPushButton("ÃƒÂ¢Ã¢â‚¬â€œÃ‚Â¼")
        self.btn_next.setToolTip("Next (F3)")
        self.btn_next.clicked.connect(self._go_next)
        
        self.btn_close = QPushButton("ÃƒÂ¢Ã…â€œÃ¢â‚¬Â¢")
        self.btn_close.setObjectName("btnClose")
        self.btn_close.clicked.connect(self.hide)
        
        layout.addWidget(self.type_combo)
        layout.addWidget(self.search_input)
        layout.addWidget(self.btn_find)
        layout.addWidget(self.lbl_count)
        layout.addWidget(self.btn_prev)
        layout.addWidget(self.btn_next)
        layout.addWidget(self.btn_close)
        
        self.search_input.textChanged.connect(self._on_query_changed)
        self.type_combo.currentIndexChanged.connect(self._on_query_changed)
        
    def _on_query_changed(self):
        """Reset results when query changes so next Enter/Find does a fresh search."""
        self._results.clear()
        self._current_idx = -1
        self.lbl_count.setText("0 of 0")

    def _on_enter_pressed(self):
        """On Enter: run search if no results yet, otherwise go next."""
        if not self._results:
            self._run_search()
        else:
            self._go_next()

    def _run_search(self):
        query = self.search_input.text().strip()
        self._results.clear()
        self._current_idx = -1
        
        if not query:
            self.lbl_count.setText("0 of 0")
            self.hex_view.clearSelection()
            return
            
        try:
            data = bytes(self.hex_model.get_data())
        except Exception as e:
            self.lbl_count.setText("Err: data")
            return
            
        search_bytes = b""
        
        if self.type_combo.currentIndex() == 0:
            try:
                hex_str = query.replace(" ", "").replace(",", "")
                if len(hex_str) % 2 != 0:
                    self.lbl_count.setText("Odd hex len")
                    return
                search_bytes = bytes.fromhex(hex_str)
            except ValueError:
                self.lbl_count.setText("Invalid hex")
                return
        else:
            search_bytes = query.encode('ascii', errors='ignore')
            
        if not search_bytes:
            self.lbl_count.setText("Empty bytes")
            return
            
        offset = 0
        while True:
            idx = data.find(search_bytes, offset)
            if idx == -1:
                break
            self._results.append(idx)
            offset = idx + len(search_bytes)
            
        if self._results:
            self._current_idx = 0
            self._update_ui_and_selection()
        else:
            self.lbl_count.setText("0 found")
            self.hex_view.clearSelection()
            
    def _go_next(self):
        if not self._results:
            self._run_search()
        if not self._results: return
        self._current_idx = (self._current_idx + 1) % len(self._results)
        self._update_ui_and_selection()
        
    def _go_prev(self):
        if not self._results: return
        self._current_idx = (self._current_idx - 1) % len(self._results)
        self._update_ui_and_selection()
        
    def _update_ui_and_selection(self):
        if not self._results: return
        self.lbl_count.setText(f"{self._current_idx + 1} of {len(self._results)}")
        
        offset = self._results[self._current_idx]
        
        query = self.search_input.text().strip()
        if self.type_combo.currentIndex() == 0:
            hex_str = query.replace(" ", "").replace(",", "")
            length = len(hex_str) // 2
        else:
            length = len(query.encode('ascii', errors='ignore'))
        
        if length <= 0:
            return
            
        from PySide6.QtCore import QItemSelectionModel, QItemSelection, QItemSelectionRange
        from PySide6.QtWidgets import QAbstractItemView
        model = self.hex_view.model()
        sel_model = self.hex_view.selectionModel()
        
        start = offset
        end = offset + length - 1
        
        selection = QItemSelection()
        
        # Build selection row by row using QItemSelectionRange (correct PySide6 API)
        curr = start
        while curr <= end:
            row = curr // 16
            start_col = curr % 16
            end_offset_this_row = min(end, (row + 1) * 16 - 1)
            end_col = end_offset_this_row % 16
            top_left = model.index(row, start_col)
            bottom_right = model.index(row, end_col)
            if top_left.isValid() and bottom_right.isValid():
                selection.append(QItemSelectionRange(top_left, bottom_right))
            curr = end_offset_this_row + 1
            
        sel_model.select(selection, QItemSelectionModel.SelectionFlag.ClearAndSelect)
        self.hex_view.scrollTo(model.index(start // 16, 0),
                               QAbstractItemView.ScrollHint.PositionAtCenter)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            self.hex_view.setFocus()
        else:
            super().keyPressEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        self._reposition()

    def _reposition(self):
        """Move the bar to the top-right corner of the parent hex_view."""
        pv = self.parentWidget()  # parent is hex_view
        if pv:
            hint = self.sizeHint()
            sb_w = max(hint.width(), 430)
            sb_h = max(hint.height(), 32)
            margin_right = 20
            margin_top = 10
            x = pv.width() - sb_w - margin_right
            self.setGeometry(x, margin_top, sb_w, sb_h)

class HexEditorTab(QWidget):
    log_signal = Signal(str)
    modified_signal = Signal()  # Emitted when document is modified

    def __init__(self, data=b"", parent=None):
        super().__init__(parent)
        self.file_path = None   # Track the source file path
        self._base_title = "Untitled"  # Base tab title without '*'
        self._is_modified = False
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.setHandleWidth(4)
        
        self.hex_view = QTableView()
        self.hex_view.setObjectName("HexView")
        self.hex_model = HexTableModel(data)
        self.hex_view.setModel(self.hex_model)
        
        self.hex_view.setShowGrid(False)
        self.hex_view.setWordWrap(False)
        self.hex_view.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.hex_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        font = QFont("Consolas", 11)
        self.hex_view.setFont(font)
        for i in range(16):
            self.hex_view.setColumnWidth(i, 26)
        self.hex_view.setColumnWidth(16, 160)
        self.hex_view.horizontalHeader().setMinimumSectionSize(20)
        self.hex_view.verticalHeader().setDefaultSectionSize(20)
        self.hex_view.verticalHeader().setMinimumSectionSize(20)
        self.hex_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.hex_view.verticalHeader().setFixedWidth(85)
        self.hex_view.verticalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.hex_view.horizontalHeader().setStretchLastSection(True)
        self.hex_view.horizontalHeader().setFixedHeight(25)
        
        # Normal scroll speed for the hex view viewport
        def normal_wheel_event(event):
            scroll_bar = self.hex_view.verticalScrollBar()
            delta = event.angleDelta().y()
            if delta != 0:
                step = 15 if delta > 0 else -15  # 15 rows per tick (normal reading speed)
                new_val = max(scroll_bar.minimum(), min(scroll_bar.maximum(), scroll_bar.value() - step))
                scroll_bar.setValue(new_val)
                event.accept()
        self.hex_view.wheelEvent = normal_wheel_event
        
        # Super-fast jump scroll speed for the scrollbar itself
        scroll_bar = self.hex_view.verticalScrollBar()
        from PySide6.QtCore import QObject, QEvent
        class ScrollBarFilter(QObject):
            def eventFilter(self, obj, event):
                if event.type() == QEvent.Type.Wheel:
                    delta = event.angleDelta().y()
                    if delta != 0:
                        # Scroll 0.15% of the file or at least 1500 rows per tick
                        total_range = obj.maximum() - obj.minimum()
                        step = max(1500, int(total_range * 0.0015)) if delta > 0 else -max(1500, int(total_range * 0.0015))
                        new_val = max(obj.minimum(), min(obj.maximum(), obj.value() - step))
                        obj.setValue(new_val)
                        return True
                return False
        
        self.sb_filter = ScrollBarFilter(scroll_bar)
        scroll_bar.installEventFilter(self.sb_filter)
        
        self.corner_label = QLabel("Offset (h)", self.hex_view)
        self.corner_label.setStyleSheet("color: #4cd3e3; font-weight: bold; font-family: 'Consolas', monospace; font-size: 12px; background-color: #171a1d; padding-left: 5px;")
        self.corner_label.setGeometry(1, 1, 84, 23)
        self.corner_label.show()
        
        self.hex_container = QWidget()
        self.hex_hlayout = QHBoxLayout(self.hex_container)
        self.hex_hlayout.setContentsMargins(0, 0, 0, 0)
        self.hex_hlayout.setSpacing(0)
        
        self.hex_minimap = HexMinimap(self.hex_view, self.hex_model)
        
        self.hex_hlayout.addWidget(self.hex_view)
        self.hex_hlayout.addWidget(self.hex_minimap)
        
        self.splitter.addWidget(self.hex_container)
        
        self.main_layout.addWidget(self.splitter)
        
        # Instantiate the floating search bar overlay
        self.search_bar = HexSearchBar(self.hex_view, self.hex_model, self.hex_view)
        self.search_bar.hide()
        
        self.setup_shortcuts()
        self.hex_view.customContextMenuRequested.connect(self.show_hex_context_menu)

        # Connect document modification signal for modified indicator
        from core_workspace import event_bus
        event_bus.document_modified.connect(self._on_document_modified)
        
        # Connect selection and cursor signals
        self.hex_view.selectionModel().selectionChanged.connect(self._emit_selection)
        self.hex_view.selectionModel().currentChanged.connect(self._emit_cursor)

        # ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ Linear (Sequential) Selection ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬
        # Override mouse events so dragging selects row-by-row (linear),
        # not a rectangular block.
        self._sel_anchor_offset = None   # byte offset where drag started

        def _linear_select(start_offset, end_offset):
            """Select all bytes between start_offset and end_offset linearly."""
            from PySide6.QtCore import QItemSelection, QItemSelectionRange, QItemSelectionModel
            if start_offset > end_offset:
                start_offset, end_offset = end_offset, start_offset
            selection = QItemSelection()
            curr = start_offset
            while curr <= end_offset:
                row = curr // 16
                start_col = curr % 16
                end_this_row = min(end_offset, (row + 1) * 16 - 1)
                end_col = end_this_row % 16
                tl = self.hex_model.index(row, start_col)
                br = self.hex_model.index(row, end_col)
                selection.append(QItemSelectionRange(tl, br))
                curr = end_this_row + 1
            self.hex_view.selectionModel().select(
                selection, QItemSelectionModel.SelectionFlag.ClearAndSelect
            )

        def _hex_mouse_press(event):
            from PySide6.QtCore import Qt as _Qt
            idx = self.hex_view.indexAt(event.pos())
            if idx.isValid() and idx.column() < 16:
                offset = idx.row() * 16 + idx.column()
                self._sel_anchor_offset = offset
                _linear_select(offset, offset)
                event.accept()
            else:
                self._sel_anchor_offset = None
                type(self.hex_view).mousePressEvent(self.hex_view, event)

        def _hex_mouse_move(event):
            from PySide6.QtCore import Qt as _Qt
            if (event.buttons() & _Qt.MouseButton.LeftButton) and self._sel_anchor_offset is not None:
                idx = self.hex_view.indexAt(event.pos())
                if idx.isValid() and idx.column() < 16:
                    curr_offset = idx.row() * 16 + idx.column()
                    _linear_select(self._sel_anchor_offset, curr_offset)
                    event.accept()
                    return
            type(self.hex_view).mouseMoveEvent(self.hex_view, event)

        def _hex_mouse_release(event):
            self._sel_anchor_offset = None
            type(self.hex_view).mouseReleaseEvent(self.hex_view, event)

        self.hex_view.mousePressEvent   = _hex_mouse_press
        self.hex_view.mouseMoveEvent    = _hex_mouse_move
        self.hex_view.mouseReleaseEvent = _hex_mouse_release

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'search_bar') and self.search_bar and self.search_bar.isVisible():
            self.search_bar._reposition()

    def _emit_selection(self, selected, deselected):
        start, count = self.get_selected_range()
        from core_workspace import event_bus
        if start is not None and count is not None:
            event_bus.selection_changed.emit(self.hex_model.document, start, count)
        else:
            event_bus.selection_changed.emit(self.hex_model.document, -1, 0)

    def _emit_cursor(self, current, previous):
        if current.isValid():
            offset = current.row() * 16 + current.column()
            from core_workspace import event_bus
            event_bus.cursor_moved.emit(self.hex_model.document, offset)

    def _on_document_modified(self, doc):
        """Mark the tab as modified when its document changes."""
        if hasattr(self, 'hex_model') and doc == self.hex_model.document:
            if not self._is_modified:
                self._is_modified = True
                self.modified_signal.emit()

    def set_base_title(self, title):
        """Set the base title (without '*') for this tab."""
        self._base_title = title
        self._refresh_tab_title()

    def _refresh_tab_title(self):
        """Update parent QTabWidget tab text with modified indicator."""
        parent = self.parent()
        if isinstance(parent, QTabWidget):
            idx = parent.indexOf(self)
        else:
            # Walk up to find QTabWidget
            p = self.parent()
            while p and not isinstance(p, QTabWidget):
                p = p.parent()
            if p:
                idx = p.indexOf(self)
                parent = p
            else:
                return
        if idx >= 0:
            title = ("* " if self._is_modified else "") + self._base_title
            parent.setTabText(idx, title)

    def mark_clean(self):
        """Mark the tab as clean (saved)."""
        self._is_modified = False
        self._refresh_tab_title()

    def do_undo(self):
        doc = self.hex_model.document
        if not doc.undo_stack:
            self.log_signal.emit("[INFO] Nothing to undo.")
            return
        action = doc.undo_stack.pop()
        doc.redo_stack.append(action)
        atype = action['type']
        # Temporarily mark not modified during undo to avoid double-trigger
        if atype == 'edit':
            doc._data[action['offset']] = action['old_val']
        elif atype == 'edit_block':
            off = action['offset']
            doc._data[off:off+len(action['old_val'])] = action['old_val']
        elif atype == 'insert':
            off = action['offset']
            del doc._data[off:off+action['length']]
        elif atype == 'remove':
            off = action['offset']
            doc._data[off:off] = action['old_val']
        self.hex_model.layoutChanged.emit()
        self.log_signal.emit(f"[INFO] Undo: {atype}")

    def do_redo(self):
        doc = self.hex_model.document
        if not doc.redo_stack:
            self.log_signal.emit("[INFO] Nothing to redo.")
            return
        action = doc.redo_stack.pop()
        doc.undo_stack.append(action)
        atype = action['type']
        if atype == 'edit':
            doc._data[action['offset']] = action['new_val']
        elif atype == 'edit_block':
            off = action['offset']
            doc._data[off:off+len(action['new_val'])] = action['new_val']
        elif atype == 'insert':
            off = action['offset']
            doc._data[off:off] = b'\x00' * action['length']
        elif atype == 'remove':
            off = action['offset']
            old = action['old_val']
            del doc._data[off:off+len(old)]
        self.hex_model.layoutChanged.emit()
        self.log_signal.emit(f"[INFO] Redo: {atype}")

    def setup_shortcuts(self):
        self.shortcut_delete = QShortcut(QKeySequence(Qt.Key.Key_Delete), self.hex_view)
        self.shortcut_delete.activated.connect(self.delete_selected_data)
        
        self.shortcut_backspace = QShortcut(QKeySequence(Qt.Key.Key_Backspace), self.hex_view)
        self.shortcut_backspace.activated.connect(self.delete_selected_data)
        
        self.shortcut_find = QShortcut(QKeySequence("Ctrl+F"), self)
        self.shortcut_find.activated.connect(self.show_find_dialog)
        
        self.shortcut_find_next = QShortcut(QKeySequence("F3"), self)
        self.shortcut_find_next.activated.connect(self._find_next)
        
        self.shortcut_find_prev = QShortcut(QKeySequence("Shift+F3"), self)
        self.shortcut_find_prev.activated.connect(self._find_prev)
        
        self.shortcut_select_block = QShortcut(QKeySequence("Ctrl+E"), self.hex_view)
        self.shortcut_select_block.activated.connect(self.show_select_block_dialog)
        
        self.shortcut_goto = QShortcut(QKeySequence("Ctrl+G"), self.hex_view)
        self.shortcut_goto.activated.connect(self.show_goto_dialog)
        
        self.shortcut_copy = QShortcut(QKeySequence("Ctrl+C"), self.hex_view)
        self.shortcut_copy.activated.connect(self.copy_hex_data)
        
        self.shortcut_cut = QShortcut(QKeySequence("Ctrl+X"), self.hex_view)
        self.shortcut_cut.activated.connect(self.cut_selected_data)
        
        self.shortcut_paste_insert = QShortcut(QKeySequence("Ctrl+V"), self.hex_view)
        self.shortcut_paste_insert.activated.connect(self.paste_insert_data)
        
        self.shortcut_paste_write = QShortcut(QKeySequence("Ctrl+B"), self.hex_view)
        self.shortcut_paste_write.activated.connect(self.paste_write_data)

        self.shortcut_undo = QShortcut(QKeySequence("Ctrl+Z"), self.hex_view)
        self.shortcut_undo.activated.connect(self.do_undo)

        self.shortcut_redo = QShortcut(QKeySequence("Ctrl+Y"), self.hex_view)
        self.shortcut_redo.activated.connect(self.do_redo)

    def get_selected_range(self):
        selection = self.hex_view.selectionModel().selectedIndexes()
        if not selection: return None, None
        offsets = []
        for index in selection:
            col = index.column()
            if col < 16: offsets.append(index.row() * 16 + col)
            else:
                for c in range(16): offsets.append(index.row() * 16 + c)
        if not offsets: return None, None
        return min(offsets), max(offsets) - min(offsets) + 1

    def copy_hex_data(self):
        start, count = self.get_selected_range()
        if start is not None:
            data = self.hex_model.get_data()[start:start+count]
            hex_str = " ".join(f"{b:02X}" for b in data)
            QApplication.clipboard().setText(hex_str)
            self.log_signal.emit(f"[INFO] Copied {count} bytes as HEX")

    def copy_text_data(self):
        start, count = self.get_selected_range()
        if start is not None:
            data = self.hex_model.get_data()[start:start+count]
            ascii_text = "".join(self.hex_model.CHARS_LOOKUP[b] for b in data)
            QApplication.clipboard().setText(ascii_text)
            self.log_signal.emit(f"[INFO] Copied {count} bytes as TEXT")

    def delete_selected_data(self):
        start, count = self.get_selected_range()
        if start is not None:
            self.hex_model.remove_bytes(start, count)
            self.log_signal.emit(f"[INFO] Deleted {count} bytes at 0x{start:08X}")

    def cut_selected_data(self):
        start, count = self.get_selected_range()
        if start is not None:
            self.copy_hex_data()
            self.hex_model.remove_bytes(start, count)
            self.log_signal.emit(f"[INFO] Cut {count} bytes at 0x{start:08X}")

    def get_clipboard_bytes(self):
        text = QApplication.clipboard().text().strip()
        try:
            clean_hex = text.replace(" ", "").replace("\n", "").replace("\r", "")
            return bytes.fromhex(clean_hex)
        except ValueError:
            return None

    def paste_insert_data(self):
        start, _ = self.get_selected_range()
        if start is None: return
        data = self.get_clipboard_bytes()
        if data:
            self.hex_model.insert_bytes(start, len(data), data)
            self.log_signal.emit(f"[INFO] Pasted (Insert) {len(data)} bytes at 0x{start:08X}")

    def paste_write_data(self):
        start, _ = self.get_selected_range()
        if start is None: return
        data = self.get_clipboard_bytes()
        if data:
            self.hex_model.replace_bytes(start, data)
            self.log_signal.emit(f"[INFO] Pasted (Write) {len(data)} bytes at 0x{start:08X}")

    def fill_selection(self):
        start, count = self.get_selected_range()
        if start is None or count == 0:
            self.log_signal.emit("[ERROR] No selection to fill.")
            return
            
        dialog = HexFillDialog(self)
        if dialog.exec():
            fill_bytes = dialog.get_fill_bytes()
            if not fill_bytes:
                self.log_signal.emit("[ERROR] Invalid fill hex.")
                return
                
            # If fill_bytes is a pattern (e.g., 2 bytes), repeat it to fill 'count' bytes
            repeats = (count // len(fill_bytes)) + 1
            full_fill = (fill_bytes * repeats)[:count]
            
            self.hex_model.replace_bytes(start, full_fill)
            self.log_signal.emit(f"[INFO] Filled {count} bytes at 0x{start:X}")

    def add_bookmark_dialog(self, offset):
        dialog = AddBookmarkDialog(offset, self)
        if dialog.exec():
            name = dialog.get_name()
            if name:
                self.hex_model.document.add_bookmark(offset, name)
                self.log_signal.emit(f"[INFO] Bookmark '{name}' added at 0x{offset:X}")

    def show_select_block_dialog(self):
        dialog = HexSelectBlockDialog(self)
        if dialog.exec():
            start, end = dialog.get_offsets()
            if start is not None and end is not None and end >= start:
                self.hex_view.clearSelection()
                model = self.hex_model
                sel_model = self.hex_view.selectionModel()
                
                # Create a selection block
                from PySide6.QtCore import QItemSelection, QItemSelectionRange
                selection = QItemSelection()
                
                curr_offset = start
                while curr_offset <= end:
                    row = curr_offset // 16
                    start_col = curr_offset % 16
                    end_offset_this_row = min(end, (row + 1) * 16 - 1)
                    end_col = end_offset_this_row % 16
                    
                    top_left = model.index(row, start_col)
                    bottom_right = model.index(row, end_col)
                    selection.append(QItemSelectionRange(top_left, bottom_right))
                    
                    curr_offset = end_offset_this_row + 1
                    
                from PySide6.QtCore import QItemSelectionModel
                select_flag = QItemSelectionModel.SelectionFlag.Select if hasattr(QItemSelectionModel, 'SelectionFlag') else QItemSelectionModel.SelectionFlag.Select
                sel_model.select(selection, select_flag)
                self.hex_view.scrollTo(model.index(start // 16, 0))

    def show_find_dialog(self):
        if hasattr(self, 'search_bar') and self.search_bar:
            if self.search_bar.isVisible():
                self.search_bar.search_input.setFocus()
                self.search_bar.search_input.selectAll()
            else:
                self.search_bar.show()
                self.search_bar.raise_()
                self.search_bar.search_input.setFocus()
                self.search_bar.search_input.selectAll()

    def _find_next(self):
        if hasattr(self, 'search_bar'):
            self.search_bar._go_next()

    def _find_prev(self):
        if hasattr(self, 'search_bar'):
            self.search_bar._go_prev()

    def show_goto_dialog(self):
        doc_size = self.hex_model.document.size if hasattr(self.hex_model, 'document') else len(self.hex_model.get_data())
        dialog = GotoOffsetDialog(doc_size, self)
        if dialog.exec():
            offset = dialog.get_offset()
            if offset is not None and 0 <= offset < doc_size:
                self.hex_view.clearSelection()
                row = offset // 16
                col = offset % 16
                idx = self.hex_model.index(row, col)
                from PySide6.QtCore import QItemSelectionModel
                select_flag = QItemSelectionModel.SelectionFlag.Select if hasattr(QItemSelectionModel, 'SelectionFlag') else QItemSelectionModel.SelectionFlag.Select
                self.hex_view.selectionModel().select(idx, select_flag)
                self.hex_view.scrollTo(idx, QAbstractItemView.ScrollHint.PositionAtCenter)
            else:
                self.log_signal.emit(f"[ERROR] Invalid offset.")

    def extract_selection_to_file(self):
        start, count = self.get_selected_range()
        if start is None or count == 0: return
        from PySide6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getSaveFileName(self, "Extract to File", "", "Binary Files (*.bin);;All Files (*)")
        if file_path:
            data = bytes(self.hex_model.get_data()[start:start+count])
            with open(file_path, 'wb') as f:
                f.write(data)
            self.log_signal.emit(f"[INFO] Extracted {count} bytes to {file_path}")

    def replace_selection_from_file(self):
        start, count = self.get_selected_range()
        if start is None: return
        from PySide6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(self, "Replace from File", "", "All Files (*)")
        if file_path:
            with open(file_path, 'rb') as f:
                new_data = f.read()
            self.hex_model.replace_bytes(start, new_data)
            self.log_signal.emit(f"[INFO] Replaced bytes from {file_path}")

    def copy_offset_hex(self):
        index = self.hex_view.currentIndex()
        if not index.isValid(): return
        offset = index.row() * 16 + index.column()
        QApplication.clipboard().setText(f"0x{offset:08X}")
        self.log_signal.emit(f"[INFO] Offset copied: 0x{offset:08X}")

    def compute_selection_hashes(self):
        import hashlib, binascii
        start, count = self.get_selected_range()
        if start is None or count == 0:
            # Hash entire file
            data = bytes(self.hex_model.get_data())
            start = 0
            count = len(data)
        else:
            data = bytes(self.hex_model.get_data()[start:start+count])
        crc = binascii.crc32(data) & 0xFFFFFFFF
        sha = hashlib.sha256(data).hexdigest()
        msg = f"Selection: 0x{start:08X} ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ 0x{start+count-1:08X} ({count} bytes)\nCRC32:  {crc:#010X}\nSHA256: {sha}"
        from PySide6.QtWidgets import QMessageBox
        box = QMessageBox(self)
        box.setWindowTitle("Hash / Checksum")
        box.setText(msg)
        box.setStandardButtons(QMessageBox.StandardButton.Ok)
        box.exec()
        self.log_signal.emit(f"[INFO] CRC32={crc:#010X}  SHA256={sha[:16]}...")

    def show_hex_context_menu(self, pos):
        index = self.hex_view.indexAt(pos)
        if not index.isValid() or index.column() >= 16: return
        
        menu = QMenu(self)

        # -------------------- Edit --------------------
        menu.addAction("Fill Selection...", self.fill_selection)
        menu.addAction("Delete Selection", self.delete_selected_data)
        menu.addAction("Extract Selection -> File", self.extract_selection_to_file)
        menu.addAction("Replace Selection <- File", self.replace_selection_from_file)
        menu.addSeparator()
        menu.addAction("CRC32 / SHA256...", self.compute_selection_hashes)
        menu.addSeparator()
        menu.addAction("Select Block...", self.show_select_block_dialog)
        menu.addAction("Find...", self.show_find_dialog)
        menu.addSeparator()
        
        # -------------------- Read-Only --------------------
        doc = self.hex_model.document
        ro_text = "Read-Only Mode (ON) - Click to Disable" if doc.is_read_only else "Read-Only Mode (OFF) - Click to Enable"
        def _toggle_ro():
            main_win = self.window()
            if hasattr(main_win, 'toggle_tab_read_only'):
                main_win.toggle_tab_read_only(self)
        menu.addAction(ro_text, _toggle_ro)
        
        menu.exec(self.hex_view.viewport().mapToGlobal(pos))

class ShortcutsReferenceDialog(QDialog):
    """Quick-reference card for all keyboard shortcuts."""
    
    _SHORTCUTS = [
        ("ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ Global ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬", ""),
        ("Ctrl+O", "Open BIOS File"),
        ("Ctrl+W", "Close Current Hex Tab"),
        ("Ctrl+Tab", "Next Tab"),
        ("Ctrl+Shift+Tab", "Previous Tab"),
        ("Insert", "Toggle INS / OVR Mode"),
        ("F1", "Show This Help"),
        ("", ""),
        ("ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ Hex Editor ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬", ""),
        ("Ctrl+F", "Advanced Search"),
        ("Ctrl+G", "Go to Offset"),
        ("Ctrl+E", "Select Block"),
        ("Ctrl+Z", "Undo"),
        ("Ctrl+Y", "Redo"),
        ("Ctrl+C", "Copy Hex Selection"),
        ("Ctrl+X", "Cut Selection"),
        ("Ctrl+V", "Paste (Insert)"),
        ("Delete / Backspace", "Delete Selection"),
        ("", ""),
        ("ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ Right-Click Menu ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬", ""),
        ("Right-Click ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ Add Bookmark...", "Add a named bookmark at cursor"),
        ("Right-Click ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ Fill Selection...", "Fill with 00 / FF / Custom"),
        ("Right-Click ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ Go to Offset...", "Jump to any HEX/DEC offset"),
        ("Right-Click ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ Read-Only Mode", "Toggle safe read-only mode"),
        ("Right-Click ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ CRC32 / SHA256", "Hash current selection or file"),
        ("Right-Click ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ Extract Selection", "Save selection to binary file"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Keyboard Shortcuts Reference")
        self.setMinimumSize(520, 480)
        self.setStyleSheet("""
            QDialog { background-color: #171a1d; color: #e2e8f0; }
            QTableWidget { background-color: #121518; color: #e2e8f0; gridline-color: #283038;
                           font-family: Consolas, monospace; font-size: 11px; border: 1px solid #283038; border-radius: 6px; }
            QTableWidget::item { padding: 5px 8px; }
            QTableWidget::item:selected { background-color: #3598a6; color: #ffffff; }
            QHeaderView::section { background-color: #1c2024; color: #4cd3e3; padding: 6px;
                                   font-weight: bold; border: 1px solid #283038; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 8)
        
        title = QLabel("ÃƒÂ¢Ã…â€™Ã‚Â¨  Keyboard Shortcuts")
        title.setStyleSheet("color: #00f3ff; font-size: 14px; font-weight: bold; margin-bottom: 6px;")
        layout.addWidget(title)
        
        table = QTableWidget(len(self._SHORTCUTS), 2, self)
        table.setHorizontalHeaderLabels(["Shortcut", "Action"])
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        table.verticalHeader().hide()
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        
        for i, (key, action) in enumerate(self._SHORTCUTS):
            k_item = QTableWidgetItem(key)
            a_item = QTableWidgetItem(action)
            if not action:  # section header row
                k_item.setForeground(QColor("#4CAF50"))
                k_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                a_item.setForeground(QColor("#4CAF50"))
                for col in (0, 1):
                    table.item(i, col) if table.item(i, col) else None
            else:
                k_item.setForeground(QColor("#00f3ff"))
            table.setItem(i, 0, k_item)
            table.setItem(i, 1, a_item)
        
        layout.addWidget(table)
        
        btn_close = QPushButton("Close")
        btn_close.setStyleSheet("background-color: #1a1d2e; color: #fff; padding: 6px 20px; border: 1px solid #00f3ff; border-radius: 3px;")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)

class WatermarkTerminal(QTextBrowser):
    """
    Terminal Log widget featuring a 50% opacity centered watermark
    of the R1 AI LAB logo/icon in the background.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLineWrapMode(QTextBrowser.LineWrapMode.NoWrap)
        self.setOpenExternalLinks(False)
        self.setOpenLinks(False)
        self.setReadOnly(True)
        self.setObjectName("Terminal")
        self.setPlaceholderText("Ready for input...")
        self._watermark_pixmap = None
        self._load_watermark()

    def _load_watermark(self):
        icon_path = get_resource_path(os.path.join("assets", "R1AILAB.png"))
        if not os.path.exists(icon_path):
            icon_path = get_resource_path(os.path.join("assets", "icon.ico"))
        if os.path.exists(icon_path):
            self._watermark_pixmap = QPixmap(icon_path)

    def paintEvent(self, event):
        vp = self.viewport()
        if self._watermark_pixmap and not self._watermark_pixmap.isNull() and vp.width() > 60 and vp.height() > 60:
            painter = QPainter(vp)
            painter.save()
            painter.setOpacity(0.125)  # 12.5% opacity watermark (reduced by 50% again)
            
            vp_w = vp.width()
            vp_h = vp.height()
            # Scale to full terminal size
            scaled = self._watermark_pixmap.scaled(
                vp.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            x = (vp_w - scaled.width()) // 2
            y = (vp_h - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
            painter.restore()
            painter.end()

        super().paintEvent(event)

class LogViewerDialog(QDialog):
    def __init__(self, parent=None):
        super(LogViewerDialog, self).__init__(parent)
        self.setWindowTitle("System Activity Logs")
        self.setMinimumSize(680, 460)
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #252a2e, stop:1 #1c2024);
                border: 1px solid #2d363f;
                color: #e2e8f0;
                font-family: 'Segoe UI', sans-serif;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(10)

        title = QLabel("📋 SYSTEM ACTIVITY & ERROR LOGS")
        title.setStyleSheet("font-weight: 800; font-size: 13px; color: #4cd3e3; letter-spacing: 1px;")
        layout.addWidget(title)

        self.text_area = WatermarkTerminal()
        self.text_area.setReadOnly(True)
        self.text_area.setStyleSheet("background-color: #121518; color: #38bdf8; font-family: Consolas, monospace; border: 1px solid #283039; border-radius: 8px; padding: 10px; font-size: 12px;")
        layout.addWidget(self.text_area)
        
        # Load content
        if os.path.exists("app.log"):
            with open("app.log", "r", encoding="utf-8") as f:
                self.text_area.setPlainText(f.read())
        else:
            self.text_area.setPlainText("No logs found.")

        btn_close = QPushButton("Close")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3c444a, stop:1 #2d3338);
                color: #c8d6e0; border: 1px solid #4a545c; border-radius: 6px; padding: 6px 22px; font-weight: bold; font-size: 12px;
            }
            QPushButton:hover { background: #47525a; color: #ffffff; }
        """)
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)

class LoadingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.hide()
        
        self.angle = 0
        self.target_percentage = 0
        self.displayed_percentage = 0.0
        self.status_text = "Processing..."
        self.elapsed_time = 0.0
        self.estimated_time = 0.0
        self.logs = [] # Store last 3-4 log lines
        
        # Rotation animation for the scanner
        self.anim = QPropertyAnimation(self, b"rotation_angle")
        self.anim.setDuration(1200)
        self.anim.setStartValue(0)
        self.anim.setEndValue(360)
        self.anim.setLoopCount(-1)
        self.anim.setEasingCurve(QEasingCurve.Type.Linear)
        
        # Timer for elapsed time
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_time)
        self.start_timestamp = 0.0

    @Property(int)
    def rotation_angle(self):
        return self.angle

    @rotation_angle.setter
    def rotation_angle(self, value):
        self.angle = value
        self.update()

    def _update_time(self):
        if self.start_timestamp > 0:
            import time
            self.elapsed_time = time.perf_counter() - self.start_timestamp
            
            # CALIBRATED PROGRESS LOGIC (Target 10-15s)
            # 50ms interval = 20 FPS. 
            # 0.45 step = 9% per sec (~11s total)
            # 0.65 step = 13% per sec (~7s total)
            
            if self.displayed_percentage < self.target_percentage:
                diff = self.target_percentage - self.displayed_percentage
                # Dynamic adaptive speed: glides smoothly without lag or freezing
                speed = max(1.5, diff * 0.25)
                self.displayed_percentage += speed
            elif self.target_percentage == 100 and self.displayed_percentage < 100:
                # Final dash when analysis is complete
                self.displayed_percentage += 3.0 
            elif self.displayed_percentage < 99:
                # Steady, active crawl (never stops or looks frozen)
                self.displayed_percentage += 0.6
            
            if self.displayed_percentage > 100:
                self.displayed_percentage = 100
                
            self.update()

    def add_log(self, text):
        # Keep only the last 4 informative lines
        # Strip potential HTML for the overlay
        import re
        clean_text = re.sub(r'<[^>]+>', '', text)
        clean_text = clean_text.replace("[INFO]", "").replace("[SUCCESS]", "ÃƒÂ¢Ã…â€œÃ¢â‚¬Â").replace("[ERROR]", "ÃƒÂ¢Ã…â€œÃ‹Å“").strip()
        if clean_text:
            self.logs.append(clean_text)
            if len(self.logs) > 4:
                self.logs.pop(0)
            self.update()

    def set_progress(self, value):
        self.target_percentage = max(0, min(100, value))
        self.update()

    def set_status_text(self, text):
        self.status_text = text
        self.update()

    def start(self, text="Processing...", estimate=0.0):
        import time
        self.status_text = text
        self.target_percentage = 0
        self.displayed_percentage = 0.0
        self.elapsed_time = 0.0
        self.estimated_time = estimate
        self.start_timestamp = time.perf_counter()
        self.logs = []
        self.show()
        self.anim.start()
        self.timer.start(50) # Faster updates for smoother progress
        
        self.update_geometry()
        self.raise_()

    def update_geometry(self):
        parent_widget = self.parentWidget()
        if parent_widget:
            parent_rect = parent_widget.rect()
            w = parent_rect.width() * 0.6 # Use 60% for better readability, or 50% as requested
            h = parent_rect.height() * 0.6
            x = (parent_rect.width() - w) / 2
            y = (parent_rect.height() - h) / 2
            self.setGeometry(int(x), int(y), int(w), int(h))

    def stop(self):
        self.anim.stop()
        self.timer.stop()
        self.start_timestamp = 0.0
        self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 1. Cyberpunk Dark Dim with Border
        # Create a rounded rectangle for the 50% view
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(self.rect(), 20, 20)
        painter.fillPath(path, QBrush(QColor(5, 6, 12, 245)))
        
        # Border Glow
        painter.setPen(QPen(QColor(0, 243, 255, 100), 2))
        painter.drawPath(path)
        
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        
        # 2. Scanning Beam Effect (Constrained to localized box)
        import math
        import time
        beam_y = (math.sin(time.time() * 3) + 1) / 2 * h
        painter.setPen(Qt.PenStyle.NoPen)
        beam_color = QColor(0, 243, 255, 30)
        painter.fillRect(5, int(beam_y - 15), w-10, 30, beam_color)
        painter.setPen(QPen(QColor(0, 243, 255, 60), 1))
        painter.drawLine(10, int(beam_y), w-10, int(beam_y))
        
        # 3. Draw Digital Circuit Ring (Decorative)
        pen_ring = QPen(QColor(31, 34, 51, 100), 1)
        painter.setPen(pen_ring)
        painter.drawEllipse(QRectF(cx - 120, cy - 120, 240, 240))
        painter.drawEllipse(QRectF(cx - 100, cy - 100, 200, 200))
        
        # 4. Animated Scanning Arc
        pen_arc = QPen(QColor(0, 243, 255), 4)
        pen_arc.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_arc)
        
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self.angle)
        rect_arc = QRectF(-110, -110, 220, 220)
        painter.drawArc(rect_arc, 0, 90 * 16)
        painter.drawArc(rect_arc, 180 * 16, 45 * 16)
        painter.restore()
        
        # 5. Percentage Central Data
        painter.setPen(QColor(255, 255, 255))
        font_pct = QFont("Consolas", 28, QFont.Weight.Bold)
        painter.setFont(font_pct)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, f"{int(self.displayed_percentage)}%")
        
        # 6. Timer & Estimate (Top Right, slightly offset for small box)
        timer_font = QFont("Consolas", 9)
        painter.setFont(timer_font)
        painter.setPen(QColor(0, 243, 255, 180))
        timer_text = f"ELAPSED: {self.elapsed_time:.1f}s"
        if self.estimated_time > 0:
            remain = max(0, self.estimated_time - self.elapsed_time)
            timer_text += f"\nEST: {remain:.1f}s"
        painter.drawText(w - 140, 20, 120, 50, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop, timer_text)
        
        # 7. Status Text (Cyberpunk Glitch Header)
        status_font = QFont("Orbitron", 11, QFont.Weight.Bold)
        painter.setFont(status_font)
        painter.setPen(QColor(0, 255, 65)) # Matrix Green
        painter.drawText(int(cx - 150), int(cy + 100), 300, 30, Qt.AlignmentFlag.AlignCenter, ">>> " + self.status_text.upper())
        
        # 8. Activity Log Feed (Bottom Center)
        log_font = QFont("Consolas", 8)
        painter.setFont(log_font)
        painter.setPen(QColor(0, 243, 255, 120))
        log_y = h - 70
        for log in self.logs:
            painter.drawText(20, int(log_y), w - 40, 15, Qt.AlignmentFlag.AlignCenter, f"PROC: {log}")
            log_y += 14
        
        # 9. Smaller Corner Accents for the Box
        painter.setPen(QPen(QColor(0, 243, 255), 2))
        L = 15
        # TL
        painter.drawLine(5, 5, 5+L, 5); painter.drawLine(5, 5, 5, 5+L)
        # TR
        painter.drawLine(w-5, 5, w-5-L, 5); painter.drawLine(w-5, 5, w-5, 5+L)
        # BL
        painter.drawLine(5, h-5, 5+L, h-5); painter.drawLine(5, h-5, 5, h-5-L)
        # BR
        painter.drawLine(w-5, h-5, w-5-L, h-5); painter.drawLine(w-5, h-5, w-5, h-5-L)

    def resizeEvent(self, event):
        self.update_geometry()

class FileDropWidget(QFrame):
    def __init__(self, placeholder_text="Drag and drop file here or click to browse", parent=None):
        super().__init__(parent)
        from PySide6.QtWidgets import QVBoxLayout, QLabel, QFileDialog
        from PySide6.QtCore import Qt
        
        self.setAcceptDrops(True)
        self.setStyleSheet("""
            QFrame {
                border: 2px dashed #2ac4db;
                border-radius: 8px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1a1e22, stop:1 #14171a);
            }
            QFrame:hover {
                border-color: #0ef6fd;
                background-color: #20262c;
            }
        """)
        self.file_path = ""
        
        layout = QVBoxLayout(self)
        self.label = QLabel(placeholder_text)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("color: #94a3b8; font-family: 'Segoe UI', sans-serif; font-size: 11px; border: none; background: transparent;")
        layout.addWidget(self.label)
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
            
    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            self.file_path = urls[0].toLocalFile()
            self.label.setText(self.file_path)
            self.label.setStyleSheet("color: #4cd3e3; font-weight: bold; border: none; background: transparent;")
            
    def mousePressEvent(self, event):
        from PySide6.QtWidgets import QFileDialog
        from PySide6.QtCore import Qt
        if event.button() == Qt.MouseButton.LeftButton:
            file, _ = QFileDialog.getOpenFileName(self, "Select File", "", "All Files (*.*)")
            if file:
                self.file_path = file
                self.label.setText(self.file_path)
                self.label.setStyleSheet("color: #4cd3e3; font-weight: bold; border: none; background: transparent;")

class LicenseKeyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        from PySide6.QtWidgets import QVBoxLayout, QPushButton, QLabel, QLineEdit, QMessageBox, QHBoxLayout
        from PySide6.QtCore import Qt
        
        self.setWindowTitle("🔐 Software License Activation")
        self.setFixedSize(480, 310)
        
        layout = QVBoxLayout(self)
        
        self.lbl_status = QLabel("Status: Checking...")
        self.lbl_status.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self.lbl_status)
        
        self.lbl_info = QLabel("")
        self.lbl_info.setStyleSheet("color: #aaa;")
        layout.addWidget(self.lbl_info)
        
        layout.addSpacing(6)

        # Hardware ID Display
        hwid_box = QHBoxLayout()
        hwid_lbl = QLabel("Your Hardware ID:")
        hwid_lbl.setStyleSheet("font-weight: bold; color: #d0d0d8; font-size: 11px;")
        hwid_box.addWidget(hwid_lbl)
        
        import license_manager
        my_hwid = license_manager.get_hardware_id()
        self.txt_my_hwid = QLineEdit(my_hwid)
        self.txt_my_hwid.setReadOnly(True)
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #252a2e, stop:1 #1c2024);
                border: 1px solid #2d363f;
                color: #e2e8f0;
                font-family: 'Segoe UI', sans-serif;
            }
        """)
        self.txt_my_hwid.setStyleSheet("background-color: #14171a; border: 1px solid #283038; border-radius: 6px; padding: 5px 8px; color: #4cd3e3; font-family: 'Consolas', monospace; font-weight: bold; font-size: 12px;")
        hwid_box.addWidget(self.txt_my_hwid)
        
        self.btn_copy_hwid = QPushButton("Copy HWID")
        self.btn_copy_hwid.setStyleSheet("background-color: #2e2e3e; color: #ffffff; padding: 5px 10px; border-radius: 4px; font-size: 11px; font-weight: bold;")
        self.btn_copy_hwid.clicked.connect(self.copy_hwid)
        hwid_box.addWidget(self.btn_copy_hwid)
        layout.addLayout(hwid_box)

        layout.addSpacing(8)
        
        layout.addWidget(QLabel("Enter 25-Character Product Key:"))
        self.txt_key = QLineEdit()
        self.txt_key.setPlaceholderText("KQGX3-B6NBY-CT79F-G473H-G6PHD")
        self.txt_key.setStyleSheet("font-family: 'Consolas', 'Courier New', monospace; font-size: 13px; font-weight: bold; padding: 6px;")
        self.txt_key.textChanged.connect(self._auto_format_key)
        layout.addWidget(self.txt_key)

        lbl_hint = QLabel("💡 This license will automatically register & lock to this computer upon first activation.")
        lbl_hint.setStyleSheet("color: #8a8a9e; font-size: 11px; margin-top: 2px;")
        layout.addWidget(lbl_hint)
        
        layout.addStretch()
        
        btn_layout = QHBoxLayout()
        self.btn_activate = QPushButton("ACTIVATE")
        self.btn_activate.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8fe3ea, stop:0.4 #3598a6, stop:1 #247d8a);
                color: #0d171c;
                border: 1px solid #0ef6fd;
                border-radius: 6px;
                font-weight: 800;
                padding: 8px 24px;
                font-family: 'Segoe UI', sans-serif;
            }
            QPushButton:hover { background: #0ef6fd; color: #000000; }
        """)
        self.btn_activate.clicked.connect(self.do_activate)
        
        self.btn_clear = QPushButton("Clear License")
        self.btn_clear.setStyleSheet("background-color: #ff3131; color: white; font-weight: bold; padding: 8px;")
        self.btn_clear.clicked.connect(self.do_clear)
        
        btn_layout.addWidget(self.btn_activate)
        btn_layout.addWidget(self.btn_clear)
        layout.addLayout(btn_layout)
        
        self.refresh_status()

    def _auto_format_key(self, text):
        if getattr(self, '_formatting', False):
            return
        self._formatting = True
        try:
            # If pasting legacy key, don't format
            if text.startswith("R1BT-"):
                return
            clean = "".join(c for c in text.upper() if c.isalnum())
            if len(clean) > 25:
                clean = clean[:25]
            formatted = "-".join(clean[i:i+5] for i in range(0, len(clean), 5))
            if formatted != text:
                self.txt_key.setText(formatted)
                self.txt_key.setCursorPosition(len(formatted))
        finally:
            self._formatting = False

    def copy_hwid(self):
        from PySide6.QtWidgets import QApplication, QMessageBox
        import license_manager
        hwid = license_manager.get_hardware_id()
        QApplication.clipboard().setText(hwid)
        QMessageBox.information(self, "Copied", f"Hardware ID copied to clipboard:\n\n{hwid}\n\nSend this Hardware ID to the software provider.")

    def refresh_status(self):
        import license_manager
        import datetime
        active = license_manager.get_active_license()
        if active:
            company = active.get('company', 'Unknown')
            expiry = float(active.get('expiry_ts', 0))
            expiry_str = datetime.datetime.fromtimestamp(expiry).strftime('%d %B %Y, %I:%M %p')
            self.lbl_status.setText("Status: ● ACTIVATED")
            self.lbl_status.setStyleSheet("color: #00ff41; font-size: 14px; font-weight: bold;")
            self.lbl_info.setText(f"License Holder: {company}\nValid until: {expiry_str}")
        else:
            self.lbl_status.setText("Status: ○ NOT ACTIVATED")
            self.lbl_status.setStyleSheet("color: #ff3131; font-size: 14px; font-weight: bold;")
            self.lbl_info.setText("Enter a valid secret key below to activate the software without a device.")

    def do_activate(self):
        import license_manager
        from PySide6.QtWidgets import QMessageBox
        from PySide6.QtWidgets import QApplication
        key = self.txt_key.text().strip()
        if not key:
            QMessageBox.warning(self, "Error", "Please enter a key!")
            return
            
        self.lbl_status.setText("Verifying online...")
        self.lbl_status.setStyleSheet("color: #FFD600; font-size: 14px; font-weight: bold;")
        QApplication.processEvents() # Force UI update
        
        success, msg = license_manager.verify_and_activate(key)
        if success:
            QMessageBox.information(self, "Success", msg)
            self.txt_key.clear()
            self.refresh_status()
        else:
            QMessageBox.critical(self, "Failed", msg)
            self.refresh_status()

    def do_clear(self):
        import license_manager
        from PySide6.QtWidgets import QMessageBox
        license_manager.clear_cache()
        QMessageBox.information(self, "Cleared", "License key removed from this computer.")
        self.refresh_status()

def get_ecfinder_path(parent=None, prompt_if_missing=False) -> str:
    """Finds ECFinder.exe dynamically from config, external directory, or prompts user."""
    import json
    app_root = str(get_app_root())
    cfg_file = os.path.join(app_root, "config", "tools_config.json")
    
    # 1. Check saved config
    if os.path.exists(cfg_file):
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                p = cfg.get("ecfinder_path", "")
                if p and os.path.exists(p):
                    return p
        except Exception:
            pass

    # 2. Check standard external & common directories
    candidates = [
        os.path.join(app_root, "external", "ECFinder", "ECFinder.exe"),
        os.path.join(app_root, "external", "ECFinder_0.7.0", "ECFinder.exe"),
        os.path.join(app_root, "external", "ECFinder.exe"),
        r"C:\Users\R1 LAB\Downloads\ECFinder_0.7.0\ECFinder.exe",
        os.path.join(os.path.expanduser("~"), "Downloads", "ECFinder_0.7.0", "ECFinder.exe"),
        os.path.join(os.path.expanduser("~"), "Downloads", "ECFinder.exe"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c

    # 3. Prompt user if requested
    if prompt_if_missing:
        from PySide6.QtWidgets import QMessageBox
        ret = QMessageBox.question(
            parent,
            "ECFinder Not Found",
            "ECFinder executable (ECFinder.exe) was not found in 'external/ECFinder/'.\n\n"
            "Would you like to locate ECFinder.exe on your computer?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if ret == QMessageBox.StandardButton.Yes:
            return set_ecfinder_path(parent)

    return None

def set_ecfinder_path(parent=None) -> str:
    """Prompts user to select ECFinder.exe and saves it in config/tools_config.json."""
    import json
    from PySide6.QtWidgets import QFileDialog
    app_root = str(get_app_root())
    cfg_file = os.path.join(app_root, "config", "tools_config.json")
    
    file_path, _ = QFileDialog.getOpenFileName(
        parent,
        "Locate ECFinder.exe",
        "",
        "Executable Files (*.exe);;All Files (*.*)"
    )
    if file_path and os.path.exists(file_path):
        try:
            os.makedirs(os.path.dirname(cfg_file), exist_ok=True)
            existing = {}
            if os.path.exists(cfg_file):
                with open(cfg_file, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            existing["ecfinder_path"] = file_path
            with open(cfg_file, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=4)
        except Exception:
            pass
        if parent and hasattr(parent, "log_to_terminal"):
            parent.log_to_terminal(f"[SUCCESS] ECFinder path saved: {file_path}")
        return file_path
    return None

class AutoECFinderDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox
        self.setWindowTitle("AUTO EC FINDER")
        self.setFixedSize(540, 310)
        self.parent_tool = parent
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Tool status bar at top
        status_bar = QHBoxLayout()
        current_tool = get_ecfinder_path(prompt_if_missing=False)
        self.lbl_tool_status = QLabel()
        if current_tool:
            self.lbl_tool_status.setText(f"Tool: {os.path.basename(current_tool)}")
            self.lbl_tool_status.setStyleSheet("color: #00ff41; font-size: 11px;")
        else:
            self.lbl_tool_status.setText("[!] Tool: ECFinder.exe not located")
            self.lbl_tool_status.setStyleSheet("color: #ffaa00; font-size: 11px;")
        status_bar.addWidget(self.lbl_tool_status)
        
        btn_set_path = QPushButton("Locate Tool...")
        btn_set_path.setStyleSheet("background-color: #222; color: #00f3ff; border: 1px solid #00f3ff; border-radius: 3px; font-size: 11px; padding: 3px 8px;")
        btn_set_path.clicked.connect(self._change_tool_path)
        status_bar.addWidget(btn_set_path)
        layout.addLayout(status_bar)
        
        lbl_donor = QLabel("Donor File (Drop BIOS file here):")
        lbl_donor.setStyleSheet("color: white; font-weight: bold; font-size: 12px;")
        layout.addWidget(lbl_donor)
        
        self.donor_drop = FileDropWidget("Drag and Drop Donor File Here\nor Click to Browse")
        
        # Pre-fill if parent has a file loaded
        if parent and hasattr(parent, 'current_bios_file') and parent.current_bios_file and os.path.exists(parent.current_bios_file):
            self.donor_drop.file_path = parent.current_bios_file
            self.donor_drop.label.setText(f"Loaded: {os.path.basename(parent.current_bios_file)}")
            self.donor_drop.label.setStyleSheet("color: #00ff41; font-weight: bold; border: none; background: transparent;")
            
        layout.addWidget(self.donor_drop)
        
        btn_run = QPushButton("LAUNCH ECFINDER")
        btn_run.setMinimumHeight(42)
        btn_run.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_run.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8fe3ea, stop:0.4 #3598a6, stop:1 #247d8a);
                color: #0d171c;
                font-weight: 800;
                border: 1px solid #0ef6fd;
                border-radius: 6px;
                font-size: 13px;
                letter-spacing: 0.8px;
            }
            QPushButton:hover {
                background: #0ef6fd;
                color: #000000;
            }
        """)
        btn_run.clicked.connect(self.run_tool)
        
        layout.addWidget(btn_run)
        
    def _change_tool_path(self):
        new_path = set_ecfinder_path(self)
        if new_path:
            self.lbl_tool_status.setText(f"Tool: {os.path.basename(new_path)}")
            self.lbl_tool_status.setStyleSheet("color: #00ff41; font-size: 11px;")
        
    def run_tool(self):
        import os, subprocess
        from PySide6.QtWidgets import QMessageBox
        donor_file = self.donor_drop.file_path
        
        if not donor_file or not os.path.exists(donor_file):
            QMessageBox.warning(self, "Error", "Please select or drop a valid Donor/BIOS file first!")
            return
            
        tool_path = get_ecfinder_path(self, prompt_if_missing=True)
        if not tool_path or not os.path.exists(tool_path):
            if self.parent_tool:
                self.parent_tool.log_to_terminal("[WARNING] ECFinder launch cancelled: Tool executable not selected.")
            return
            
        tool_dir = os.path.dirname(tool_path)
        if self.parent_tool:
            self.parent_tool.log_to_terminal(
                f"[ACTION] Launching ECFinder (Auto Mode) for: {os.path.basename(donor_file)}"
            )
        try:
            subprocess.Popen(
                [tool_path, donor_file],
                cwd=tool_dir,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            if self.parent_tool:
                self.parent_tool.log_to_terminal("[SUCCESS] ECFinder launched with file. ✅")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to launch ECFinder: {e}")
            if self.parent_tool:
                self.parent_tool.log_to_terminal(f"[ERROR] Failed to launch ECFinder: {e}")

def smart_find_and_extract_ec(target_data: bytes, official_data: bytes):
    """
    Intelligently locates the EC / BIOS firmware block in the official payload
    based on target dump characteristics (size, tail reset vectors, fingerprints, headers).
    
    Returns (cand_start, cand_end, method_name, log_messages)
    """
    import collections
    log = []
    target_size = len(target_data)
    official_size = len(official_data)
    log.append(f"Target Dump Size   : {target_size:,} bytes (0x{target_size:X} / {target_size/(1024*1024):.2f} MB)")
    log.append(f"Official File Size : {official_size:,} bytes (0x{official_size:X} / {official_size/(1024*1024):.2f} MB)")
    
    if target_size > official_size:
        log.append("[ERROR] Target file cannot be larger than the official file!")
        return None, None, "Size Error", log

    # Strategy 1: Tail Reset Vector / High-Memory Alignment
    log.append("[INFO] Strategy 1: Searching for Reset Vector / Tail alignment...")
    for chunk_len in [64, 48, 32, 16]:
        tail_chunk = None
        tail_rel_pos = None
        for i in range(target_size - chunk_len, max(0, target_size - 0x10000), -4):
            c = target_data[i:i+chunk_len]
            if c != b'\xff'*chunk_len and c != b'\x00'*chunk_len:
                tail_chunk = c
                tail_rel_pos = i
                break
        if tail_chunk:
            pos = 0
            while True:
                idx = official_data.find(tail_chunk, pos)
                if idx == -1: break
                cand_start = idx - tail_rel_pos
                cand_end = cand_start + target_size
                if cand_start >= 0 and cand_end <= official_size:
                    log.append(f"[SUCCESS] Tail Reset Vector matched at offset 0x{cand_start:X} (Official pos: 0x{idx:X})")
                    return cand_start, cand_end, f"Tail Reset Vector Alignment ({chunk_len}b)", log
                pos = idx + 1

    # Strategy 2: Multi-Fingerprint Sliding Delta
    log.append("[INFO] Strategy 2: Analyzing multi-block structural fingerprints...")
    step = max(2048, target_size // 300)
    deltas = collections.Counter()
    for off in range(0, target_size - 32, step):
        chunk = target_data[off:off+32]
        if chunk == b'\xff'*32 or chunk == b'\x00'*32: continue
        idx = official_data.find(chunk)
        if idx != -1:
            deltas[idx - off] += 1
            
    if deltas:
        best_delta, count = deltas.most_common(1)[0]
        if count >= 2:
            cand_start = best_delta
            cand_end = best_delta + target_size
            if cand_start >= 0 and cand_end <= official_size:
                log.append(f"[SUCCESS] Fingerprint consensus matched at offset 0x{cand_start:X} ({count} block votes)")
                return cand_start, cand_end, f"Fingerprint Consensus ({count} votes)", log

    # Strategy 3: Head Signature Matching (for discrete EC chips: 128KB/256KB/512KB)
    log.append("[INFO] Strategy 3: Searching for Head Signature / eFlash entry point...")
    for chunk_len in [64, 32, 16]:
        for i in range(0, min(target_size - chunk_len, 0x20000), 16):
            c = target_data[i:i+chunk_len]
            if c != b'\xff'*chunk_len and c != b'\x00'*chunk_len:
                idx = official_data.find(c)
                if idx != -1:
                    cand_start = idx - i
                    cand_end = cand_start + target_size
                    if cand_start >= 0 and cand_end <= official_size:
                        log.append(f"[SUCCESS] Head signature matched at offset 0x{cand_start:X}")
                        return cand_start, cand_end, f"Head Signature ({chunk_len}b)", log
                break

    # Strategy 4: Vendor Header Known Offsets (HP 0x220, Insyde 0x1000, etc.)
    log.append("[INFO] Strategy 4: Checking standard vendor offsets (0x220, 0x1000)...")
    for hdr_off in [0x220, 0x1000, 0x100, 0x800]:
        if hdr_off + target_size <= official_size:
            log.append(f"[INFO] Evaluating vendor offset 0x{hdr_off:X}...")
            return hdr_off, hdr_off + target_size, f"Vendor Header Offset (0x{hdr_off:X})", log

    log.append("[ERROR] Could not automatically locate EC block!")
    return None, None, "Failed", log

class SmartECFinderDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                                     QMessageBox, QTextBrowser, QFileDialog)
        self.setWindowTitle("2 EC FINDER - SMART CARVER")
        self.setFixedSize(660, 640)
        self.parent_tool = parent
        self.carved_bytes = None
        self.suggested_name = "CARVED_EC_CLEAN.bin"
        self.last_saved_path = None
        
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        
        # Title Banner
        lbl_title = QLabel("2 EC FINDER  —  SMART CARVER")
        lbl_title.setStyleSheet("color: #00f3ff; font-weight: 900; font-size: 15px; letter-spacing: 1px;")
        layout.addWidget(lbl_title)
        
        lbl_sub = QLabel("Intelligently detect, align, and carve clean EC/BIOS region from Official update binaries.")
        lbl_sub.setStyleSheet("color: #888; font-size: 11px; margin-bottom: 4px;")
        layout.addWidget(lbl_sub)
        
        # 1. Target Drop Zone
        lbl_target = QLabel("1. TARGET FILE  (Old / Corrupt EC Dump to Match):")
        lbl_target.setStyleSheet("color: #00ff41; font-weight: bold; font-size: 11px;")
        layout.addWidget(lbl_target)
        
        self.target_drop = FileDropWidget("Drag and Drop Old / Corrupt EC Dump Here (or Click to Browse)")
        if parent and hasattr(parent, 'current_bios_file') and parent.current_bios_file and os.path.exists(parent.current_bios_file):
            self.target_drop.file_path = parent.current_bios_file
            self.target_drop.label.setText(f"Loaded: {os.path.basename(parent.current_bios_file)} ({os.path.getsize(parent.current_bios_file)/(1024*1024):.2f} MB)")
            self.target_drop.label.setStyleSheet("color: #00ff41; font-weight: bold; border: none; background: transparent;")
        layout.addWidget(self.target_drop)
        
        # 2. Official Drop Zone
        lbl_official = QLabel("2. OFFICIAL FILE  (Official Update Binary / Donor Payload):")
        lbl_official.setStyleSheet("color: #00f3ff; font-weight: bold; font-size: 11px;")
        layout.addWidget(lbl_official)
        
        self.official_drop = FileDropWidget("Drag and Drop Official Update / Donor BIOS Here (or Click to Browse)")
        layout.addWidget(self.official_drop)
        
        # Action Button
        self.btn_carve = QPushButton("SEARCH AND CARVE CLEAN EC")
        self.btn_carve.setMinimumHeight(42)
        self.btn_carve.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_carve.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8fe3ea, stop:0.4 #3598a6, stop:1 #247d8a);
                color: #0d171c;
                font-weight: 800;
                font-size: 13px;
                border: 1px solid #0ef6fd;
                border-radius: 6px;
                letter-spacing: 0.8px;
            }
            QPushButton:hover {
                background: #0ef6fd;
                color: #000000;
            }
        """)
        self.btn_carve.clicked.connect(self.perform_carve)
        layout.addWidget(self.btn_carve)
        
        # Log Console
        self.txt_log = QTextBrowser()
        self.txt_log.setMinimumHeight(140)
        self.txt_log.setStyleSheet("""
            QTextBrowser {
                background-color: #0d1117;
                color: #58a6ff;
                font-family: Consolas, monospace;
                font-size: 11px;
                border: 1px solid #30363d;
                border-radius: 4px;
                padding: 6px;
            }
        """)
        self.txt_log.setHtml("<span style='color:#666;'>Drop both files above and click 'SEARCH AND CARVE CLEAN EC'...</span>")
        layout.addWidget(self.txt_log)
        
        # Output Action Buttons Bar
        btn_bar = QHBoxLayout()
        self.btn_save = QPushButton("SAVE CARVED EC...")
        self.btn_save.setEnabled(False)
        self.btn_save.setStyleSheet("""
            QPushButton {
                background-color: #1f6feb;
                color: #ffffff;
                font-weight: bold;
                padding: 8px;
                border-radius: 3px;
            }
            QPushButton:hover { background-color: #388bfd; }
            QPushButton:disabled { background-color: #21262d; color: #484f58; }
        """)
        self.btn_save.clicked.connect(self.save_carved_file)
        btn_bar.addWidget(self.btn_save)
        
        self.btn_hex = QPushButton("LOAD TO HEX VIEWER")
        self.btn_hex.setEnabled(False)
        self.btn_hex.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                color: #ffffff;
                font-weight: bold;
                padding: 8px;
                border-radius: 3px;
            }
            QPushButton:hover { background-color: #2ea043; }
            QPushButton:disabled { background-color: #21262d; color: #484f58; }
        """)
        self.btn_hex.clicked.connect(self.load_to_hex_viewer)
        btn_bar.addWidget(self.btn_hex)
        
        layout.addLayout(btn_bar)

    def perform_carve(self):
        target_path = self.target_drop.file_path
        official_path = self.official_drop.file_path
        
        if not target_path or not os.path.exists(target_path):
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Missing File", "Please select or drop the Target (old dump) file first!")
            return
        if not official_path or not os.path.exists(official_path):
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Missing File", "Please select or drop the Official (update payload) file first!")
            return
            
        try:
            with open(target_path, "rb") as f:
                target_data = f.read()
            with open(official_path, "rb") as f:
                official_data = f.read()
                
            start, end, method, logs = smart_find_and_extract_ec(target_data, official_data)
            
            html = "<div style='line-height: 1.4;'>"
            for line in logs:
                if "[SUCCESS]" in line:
                    html += f"<span style='color: #00ff41; font-weight: bold;'>{line}</span><br>"
                elif "[ERROR]" in line:
                    html += f"<span style='color: #ff3131; font-weight: bold;'>{line}</span><br>"
                elif "[INFO]" in line:
                    html += f"<span style='color: #8b949e;'>{line}</span><br>"
                else:
                    html += f"<span style='color: #c9d1d9;'>{line}</span><br>"
                    
            if start is not None and end is not None:
                self.carved_bytes = official_data[start:end]
                carved_size = len(self.carved_bytes)
                
                html += "<br><span style='color: #00f3ff; font-weight: bold;'>═══════════════════════════════════════════</span><br>"
                html += f"<span style='color: #00f3ff; font-weight: bold;'>CARVE SUCCESSFUL</span><br>"
                html += f"<b>Start Offset:</b> 0x{start:08X} ({start:,})<br>"
                html += f"<b>End Offset:</b>   0x{end:08X} ({end:,})<br>"
                html += f"<b>Carved Size:</b>  {carved_size:,} bytes ({carved_size/(1024*1024):.2f} MB)<br>"
                html += f"<b>Method:</b>       {method}<br>"
                html += "<span style='color: #00f3ff; font-weight: bold;'>═══════════════════════════════════════════</span><br>"
                
                base_off = os.path.splitext(os.path.basename(official_path))[0]
                self.suggested_name = f"{base_off}_CLEAN_EC.bin"
                
                self.btn_save.setEnabled(True)
                self.btn_hex.setEnabled(True)
                
                if self.parent_tool and hasattr(self.parent_tool, "log_to_terminal"):
                    self.parent_tool.log_to_terminal(f"[SUCCESS] 2 EC Finder: Carved {carved_size:,} bytes from offset 0x{start:X} via {method} ✅")
            else:
                html += "<br><span style='color: #ff3131; font-weight: bold;'>[FAILED] MATCH FAILED: Could not identify exact EC boundaries.</span>"
                self.btn_save.setEnabled(False)
                self.btn_hex.setEnabled(False)
                if self.parent_tool and hasattr(self.parent_tool, "log_to_terminal"):
                    self.parent_tool.log_to_terminal(f"[ERROR] 2 EC Finder: Failed to locate EC block in official file.")
                    
            html += "</div>"
            self.txt_log.setHtml(html)
            
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"An error occurred during extraction: {e}")

    def save_carved_file(self):
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        if not self.carved_bytes:
            return
            
        default_dir = os.path.dirname(self.official_drop.file_path) if self.official_drop.file_path else ""
        save_path = os.path.join(default_dir, self.suggested_name)
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Extracted EC Firmware",
            save_path,
            "Binary Files (*.bin *.rom);;All Files (*.*)"
        )
        if file_path:
            try:
                with open(file_path, "wb") as f:
                    f.write(self.carved_bytes)
                self.last_saved_path = file_path
                QMessageBox.information(self, "Saved", f"Clean EC firmware saved successfully to:\n{file_path}")
                if self.parent_tool and hasattr(self.parent_tool, "log_to_terminal"):
                    self.parent_tool.log_to_terminal(f"[SUCCESS] Carved EC saved to: {file_path} ✅")
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Failed to write file: {e}")

    def load_to_hex_viewer(self):
        if not self.carved_bytes:
            return
            
        if not self.last_saved_path:
            app_root = str(get_app_root())
            out_dir = os.path.join(app_root, "REPAIRED_BIOS")
            os.makedirs(out_dir, exist_ok=True)
            self.last_saved_path = os.path.join(out_dir, self.suggested_name)
            with open(self.last_saved_path, "wb") as f:
                f.write(self.carved_bytes)
                
        if self.parent_tool:
            self.parent_tool.current_bios_file = self.last_saved_path
            if hasattr(self.parent_tool, 'hex_data_signal'):
                self.parent_tool.hex_data_signal.emit(self.carved_bytes)
            if hasattr(self.parent_tool, 'switch_display_tab'):
                self.parent_tool.switch_display_tab("HEX")
            self.parent_tool.log_to_terminal(f"[ACTION] Loaded carved EC into Hex Viewer ({os.path.basename(self.last_saved_path)}).")
            self.accept()

class LanguageDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("btn_language", "Language"))
        self.setFixedSize(340, 480)
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #252a2e, stop:1 #1c2024);
                border: 1px solid #2d363f;
                font-family: 'Segoe UI', sans-serif;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(12)
        
        title = QLabel("🌐 SELECT LANGUAGE")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-weight: 800; font-size: 14px; color: #4cd3e3; letter-spacing: 1px; margin-bottom: 4px;")
        layout.addWidget(title)
        
        # Languages List
        from PySide6.QtWidgets import QListWidget, QListWidgetItem
        self.lang_list = QListWidget()
        self.lang_list.setStyleSheet("""
            QListWidget {
                background-color: #14171a;
                border: 1px solid #283038;
                border-radius: 8px;
                color: #e2e8f0;
                font-size: 12px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 8px 12px;
                border-radius: 6px;
                margin-bottom: 2px;
            }
            QListWidget::item:hover {
                background-color: #1e242a;
                color: #4cd3e3;
            }
            QListWidget::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2ac4db, stop:1 #1fa2b5);
                color: #0b151a;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.lang_list)
        
        self.lang_data = lm.get_available_langs()
        current_code = lm.current_lang
        
        for lang in self.lang_data:
            item = QListWidgetItem(f"{lang['flag']} {lang['name']}")
            item.setData(Qt.UserRole, lang['code'])
            self.lang_list.addItem(item)
            if lang['code'] == current_code:
                item.setSelected(True)
                
        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3c444a, stop:1 #2d3338);
                color: #c8d6e0;
                border: 1px solid #4a545c;
                border-radius: 6px;
                padding: 7px 18px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #47525a;
                color: #ffffff;
            }
        """)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_apply = QPushButton("Apply")
        self.btn_apply.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_apply.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8fe3ea, stop:0.4 #3598a6, stop:1 #247d8a);
                color: #0d171c;
                border: 1px solid #0ef6fd;
                border-radius: 6px;
                padding: 7px 22px;
                font-weight: 800;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #0ef6fd;
                color: #000000;
            }
        """)
        self.btn_apply.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_apply)
        layout.addLayout(btn_layout)

    def get_selected_language(self):
        selected = self.lang_list.selectedItems()
        if selected:
            return selected[0].data(Qt.UserRole)
        return None

class DropZoneOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.hide()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Deep Blue Neon Dim
        painter.fillRect(self.rect(), QColor(0, 243, 255, 30))
        
        # Glowing Border
        pen = QPen(QColor(0, 243, 255), 4)
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.drawRect(self.rect().adjusted(10, 10, -10, -10))
        
        # Text
        painter.setPen(QColor(0, 243, 255))
        font = QFont("Orbitron", 20, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, ">>> INITIALIZE DECRYPTION <<<\nDROP BIOS FILE HERE")

    def resizeEvent(self, event):
        parent_widget = self.parentWidget()
        if parent_widget:
            self.setGeometry(parent_widget.rect())


class InternetStatusWidget(QLabel):
    """Self-contained internet status indicator. Uses Qt Signal for thread-safe UI updates."""

    # Signal emitted from background thread → received on main thread
    _result_signal = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        # Connect signal to UI update slot (thread-safe)
        self._result_signal.connect(self._update_ui)
        self._set_checking()
        # Periodic timer every 5 seconds
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._run_check)
        self._timer.start(5000)
        # First check after 1 second
        QTimer.singleShot(1000, self._run_check)

    def _set_checking(self):
        self.setText("● CHECKING...")
        self.setStyleSheet(
            "background: #252a2f; color: #ffb74d; font-weight: bold;"
            " border: 1px solid #4a3d24; padding: 2px 10px; border-radius: 10px;"
            " font-family: 'Segoe UI', sans-serif; font-size: 10px; letter-spacing: 0.5px;"
        )

    def _run_check(self):
        """Start background thread for connectivity check."""
        import threading
        threading.Thread(target=self._check_worker, daemon=True).start()

    def _check_worker(self):
        """Runs in background thread. Emits signal when done (thread-safe)."""
        import socket
        import urllib.request
        connected = False
        # Method 1: HTTP
        try:
            urllib.request.urlopen("http://www.google.com", timeout=4)
            connected = True
        except Exception:
            pass
        # Method 2: TCP socket fallback
        if not connected:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(3)
                s.connect(("8.8.8.8", 53))
                s.close()
                connected = True
            except Exception:
                connected = False
        # Emit signal → Qt delivers this safely to main thread
        self._result_signal.emit(connected)

    @Slot(bool)
    def _update_ui(self, connected):
        """Called on main thread via signal."""
        if connected:
            self.setText("● ONLINE")
            self.setStyleSheet(
                "background: #1c2524; color: #00ff88; font-weight: bold;"
                " border: 1px solid #1f4a3c; padding: 2px 10px; border-radius: 10px;"
                " font-family: 'Segoe UI', sans-serif; font-size: 10px; letter-spacing: 0.5px;"
            )
        else:
            self.setText("● OFFLINE")
            self.setStyleSheet(
                "background: #2a1c1d; color: #ff5252; font-weight: bold;"
                " border: 1px solid #4a2123; padding: 2px 10px; border-radius: 10px;"
                " font-family: 'Segoe UI', sans-serif; font-size: 10px; letter-spacing: 0.5px;"
            )

class BiosServiceTool(QMainWindow):
    mea_output_signal = Signal(list, list)
    progress_signal = Signal(int)
    loading_signal = Signal(bool, str, float) # (show/hide, text, estimate)
    task_finished_signal = Signal()
    hex_data_signal = Signal(object)
    module_buttons_signal = Signal(dict)
    overlay_log_signal = Signal(str)
    status_text_signal = Signal(str)
    dmi_update_signal = Signal(str, str, str, str, str)  # brand, model, platform, mac, serial
    rg_exe_files_ready = Signal(object)  # Passes extracted file list to main thread
    trigger_rg_save_dialog = Signal(str)  # Triggers save dialog from background thread with pre-filled name
    brand_tools_signal = Signal(str)  # Dispatches brand tools update to main GUI thread

    @property
    def hex_model(self):
        if hasattr(self, 'hex_tabs') and self.hex_tabs.count() > 0:
            w = self.hex_tabs.currentWidget()
            if hasattr(w, 'hex_model'): return w.hex_model
        if not hasattr(self, '_fallback_hex_model'): self._fallback_hex_model = HexTableModel(b"")
        return self._fallback_hex_model

    @property
    def hex_view(self):
        if hasattr(self, 'hex_tabs') and self.hex_tabs.count() > 0:
            w = self.hex_tabs.currentWidget()
            if hasattr(w, 'hex_view'): return w.hex_view
        if not hasattr(self, '_fallback_hex_view'): self._fallback_hex_view = QTableView()
        return self._fallback_hex_view

    def add_new_hex_tab(self, title, data=b"", file_path=None):
        tab = HexEditorTab(data, self)
        tab.log_signal.connect(self.log_to_terminal)
        tab.file_path = file_path
        tab._base_title = title
        # Sync theme state to the model
        if hasattr(self, 'is_light_mode'):
            tab.hex_model.is_light_mode = self.is_light_mode
        idx = self.hex_tabs.addTab(tab, title)
        self.hex_tabs.setCurrentIndex(idx)
        # When modified, update tab title with '*'
        tab.modified_signal.connect(lambda t=tab: self._on_tab_modified(t))
        
        if file_path and os.path.exists(file_path):
            self._push_recent_file(file_path)
            if hasattr(self, '_file_watcher') and file_path not in self._file_watcher.files():
                self._file_watcher.addPath(file_path)
            if hasattr(self, '_watched_tab_map'):
                self._watched_tab_map[file_path] = tab
        
        return tab

    def _on_tab_modified(self, tab):
        idx = self.hex_tabs.indexOf(tab)
        if idx >= 0:
            base = tab._base_title
            self.hex_tabs.setTabText(idx, f"* {base}")

    def _on_tab_double_clicked(self, idx):
        if idx < 0: return
        tab = self.hex_tabs.widget(idx)
        if not tab: return
        current_title = tab._base_title
        new_title, ok = QInputDialog.getText(
            self, "Rename Tab", "New tab name:", text=current_title
        )
        if ok and new_title.strip():
            tab._base_title = new_title.strip()
            prefix = "* " if tab._is_modified else ""
            self.hex_tabs.setTabText(idx, prefix + tab._base_title)

    def close_hex_tab(self, index):
        if self.hex_tabs.count() > 1:
            w = self.hex_tabs.widget(index)
            # Unwatch from file system watcher
            if hasattr(w, 'file_path') and w.file_path:
                if hasattr(self, '_file_watcher'):
                    self._file_watcher.removePath(w.file_path)
                if hasattr(self, '_watched_tab_map'):
                    self._watched_tab_map.pop(w.file_path, None)
            self.hex_tabs.removeTab(index)
            if w:
                w.deleteLater()
        else:
            w = self.hex_tabs.currentWidget()
            if hasattr(w, 'hex_model'):
                w.hex_model.set_data(b"")

    @Slot(object)
    def _on_hex_data_received(self, data):
        file_title = os.path.basename(self.current_bios_file) if hasattr(self, 'current_bios_file') and self.current_bios_file else "Main BIOS"
        file_path = getattr(self, 'current_bios_file', None)

        if not hasattr(self, 'hex_tabs') or self.hex_tabs.count() == 0:
            tab = self.add_new_hex_tab(file_title, data, file_path=file_path)
            if hasattr(self, 'current_regions_map'):
                tab.hex_model.set_regions(self.current_regions_map)
            tab.mark_clean()
        else:
            w = self.hex_tabs.currentWidget()
            model = w.hex_model
            model.set_data(data)
            if hasattr(self, 'current_regions_map'):
                model.set_regions(self.current_regions_map)
            # Update tab title
            if hasattr(w, '_base_title'):
                w._base_title = file_title
                w.file_path = file_path
                w.mark_clean()
            idx = self.hex_tabs.indexOf(w)
            if idx >= 0:
                self.hex_tabs.setTabText(idx, file_title)

    def __init__(self):
        super().__init__()
        self.report_manager = ReportSettingsManager(get_app_root())
        self.mea_output_signal.connect(self._handle_mea_output_internal)
        
        # Initialize Overlays
        self.loading_overlay = LoadingOverlay(self)
        self.drop_overlay = DropZoneOverlay(self)
        
        self.loading_signal.connect(self._handle_loading_state)
        self.progress_signal.connect(self.loading_overlay.set_progress)
        self.overlay_log_signal.connect(self.loading_overlay.add_log)
        self.status_text_signal.connect(self.loading_overlay.set_status_text)
        self.task_finished_signal.connect(lambda: self.initiate_loader_stop(2000))
        
        self.setWindowTitle("R1 BIOS SERVICE TOOL")
        app_icon_path = get_resource_path(os.path.join("assets", "icon.ico"))
        if not os.path.exists(app_icon_path):
            app_icon_path = get_resource_path(os.path.join("assets", "R1AILAB.png"))
        
        if os.path.exists(app_icon_path):
            self.setWindowIcon(QIcon(app_icon_path))
        self.setMinimumSize(1000, 650)
        # Load saved theme (default dark)
        from PySide6.QtCore import QSettings as _QS
        _s = _QS("R1AILAB", "BIOS_TOOL")
        self.is_light_mode = _s.value("light_mode", False, type=bool)
        from PySide6.QtWidgets import QApplication as _QApp
        if self.is_light_mode:
            _QApp.instance().setStyleSheet(STYLESHEET_LIGHT)
        else:
            _QApp.instance().setStyleSheet(STYLESHEET_DARK)
        self.setAcceptDrops(True)
        
        # State
        self.is_programmer_connected = False
       
        
        self.current_bios_file = None
        self.current_regions_map = {}
        # Determine writable log file and workspace directory safely
        root_dir = get_app_root()
        try:
            test_file = os.path.join(root_dir, ".perm_test")
            with open(test_file, "w") as tf:
                tf.write("1")
            os.remove(test_file)
            self.log_file = os.path.join(root_dir, "app.log")
            self.workspace_dir = os.path.join(root_dir, "WORKSPACE")
        except Exception:
            fallback_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "R1_BIOS_TOOL")
            os.makedirs(fallback_dir, exist_ok=True)
            self.log_file = os.path.join(fallback_dir, "app.log")
            self.workspace_dir = os.path.join(fallback_dir, "WORKSPACE")
        self.reset_stage = 0
        self.auto_save_prefix = "" # For custom prefixes during auto-save
        self.pending_save_name = ""  # Pre-filled save filename (e.g. after RG Fix)
        self.cached_dmi_info = None
        self.staged_dmi_profile = None
        
        # Path Memory: Default to Downloads folder
        self.last_directory = os.path.join(os.path.expanduser("~"), "Downloads")
        if not os.path.exists(self.last_directory):
            self.last_directory = os.getcwd()
        
        # ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ Session & File Management ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬
        from PySide6.QtCore import QSettings, QFileSystemWatcher
        self._settings = QSettings("R1AILAB", "BIOS_TOOL")
        self._recent_files = self._settings.value("session/recent_files", [], type=list) or []
        self._file_watcher = QFileSystemWatcher(self)
        self._file_watcher.fileChanged.connect(self._on_watched_file_changed)
        self._watched_tab_map = {}  # path -> tab widget
        
        # Task Sentinel Flags
        self.is_task_running = False
        self.last_log_time = 0
        self.auto_decompile_pending = False
        self.skip_auto_repair = False
        
        # AUTO-SAVE LOGIC
        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.timeout.connect(self.update_auto_save_ui)
        self.auto_save_countdown = 0
        self.is_auto_saving = False

        # Set up External Binaries PATH for BIOSUtilities
        external_path = os.path.join(get_app_root(), "external")
        if os.path.exists(external_path):
            os.environ["PATH"] = external_path + os.pathsep + os.environ.get("PATH", "")

        # Initialize Central Error Manager
        self.error_manager = ErrorManager(self)

        # Reset and Cleanup on Startup
        self.cleanup_temp_files()

        # Initialize/Clear log file safely
        try:
            with open(self.log_file, "w", encoding="utf-8") as f:
                f.write(f"--- Session Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
        except Exception as e:
            print(f"[!] Warning: Could not initialize log file '{self.log_file}': {e}")
        
        self.setup_ui()
        
        # Connect data signals after UI setup ensures models exist
        self.hex_data_signal.connect(self._on_hex_data_received)
        self.module_buttons_signal.connect(self.enable_module_buttons)
        self.dmi_update_signal.connect(self._on_dmi_update)
        self.brand_tools_signal.connect(self._update_brand_tools)
        self.rg_exe_files_ready.connect(self._show_rg_exe_selection_dialog)
        self.trigger_rg_save_dialog.connect(self._open_rg_save_dialog)

        # Shortcuts
        self.shortcut_clear = QShortcut(QKeySequence("Ctrl+L"), self)
        self.shortcut_clear.activated.connect(self.clear_terminal_and_logs)
        
        # Apply current language translations
        self.retranslate_ui()

        # Automatic Cloud Update Check on Startup (like reference project)
        QTimer.singleShot(2500, self.check_startup_update)


    def setup_ui(self):
        # Main Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        self.setup_sidebar(main_layout)

        # Content Area
        content_wrapper = QWidget()
        content_layout = QVBoxLayout(content_wrapper)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(10)

        # --- TOP TOOLBAR ---
        self.top_toolbar = AnimatedToolbarMenu()
        
        # Clean Text Buttons (Driver Style)
        self.btn_open = QPushButton("OPEN")
        self.btn_open.setToolTip(t("btn_open", "OPEN BIOS"))
        self.btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open.clicked.connect(self.open_bios_dialog)
        self.top_toolbar.add_widget(self.btn_open)

        self.btn_save = QPushButton("SAVE")
        self.btn_save.setToolTip(t("btn_save", "SAVE CHANGES"))
        self.btn_save.setEnabled(False)
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.clicked.connect(self.save_bios_changes)
        self.top_toolbar.add_widget(self.btn_save)

        self.btn_language = QPushButton(f"LANG [{lm.current_lang.upper()}]")
        self.btn_language.setToolTip(f"{t('btn_language', 'LANGUAGE')} [{lm.current_lang.upper()}]")
        self.btn_language.setEnabled(True)
        self.btn_language.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_language.clicked.connect(self.show_language_dialog)
        self.top_toolbar.add_widget(self.btn_language)
        
        self.btn_report = QPushButton("REPORT")
        self.btn_report.setToolTip(t("btn_report", "REPORT SETTINGS"))
        self.btn_report.setEnabled(True)
        self.btn_report.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_report.clicked.connect(self.show_report_settings_dialog)
        self.top_toolbar.add_widget(self.btn_report)
        
        self.btn_help = QPushButton("HELP")
        self.btn_help.setToolTip(t("btn_help", "HELP & SUPPORT"))
        self.btn_help.setEnabled(True)
        self.btn_help.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_help.clicked.connect(self.show_help_dialog)
        self.top_toolbar.add_widget(self.btn_help)
        
        self.btn_update = QPushButton("UPDATE")
        self.btn_update.setToolTip(t("btn_update", "CHECK FOR UPDATES"))
        self.btn_update.setEnabled(True)
        self.btn_update.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_update.clicked.connect(self.show_update_dialog)
        self.top_toolbar.add_widget(self.btn_update)
        
        content_layout.addWidget(self.top_toolbar)
        # -------------------

        # Panels Layout (Terminal & Hex) - Used QSplitter for resizability
        self.panels_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.panels_splitter.setHandleWidth(8)
        self.panels_splitter.setStyleSheet("QSplitter::handle { background-color: #1f2233; margin: 0 4px; border-radius: 2px; }")

        # Main Display Container (Shared Frame for Terminal & Hex Viewer)
        self.main_display_container = QWidget()
        self.main_display_container.setObjectName("MainDisplayContainer")
        display_container_layout = QVBoxLayout(self.main_display_container)
        display_container_layout.setContentsMargins(0, 0, 0, 0)
        display_container_layout.setSpacing(6)

        # Tab Button Bar (Top of Shared Frame)
        self.tab_btn_bar = QWidget()
        self.tab_btn_bar.setObjectName("TabButtonBar")
        self.tab_btn_bar.setStyleSheet("""
            QWidget#TabButtonBar {
                background-color: #0d0f1a;
                border: 1px solid #1f2233;
                border-radius: 4px;
            }
        """)
        tab_bar_layout = QHBoxLayout(self.tab_btn_bar)
        tab_bar_layout.setContentsMargins(6, 4, 6, 4)
        tab_bar_layout.setSpacing(8)

        # Tab Switch Buttons
        self.btn_tab_terminal = QPushButton("📟 TERMINAL LOG")
        self.btn_tab_terminal.setObjectName("TabBtnTerminal")
        self.btn_tab_terminal.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tab_terminal.clicked.connect(lambda: self.switch_display_tab("TERMINAL"))

        self.btn_tab_hex = QPushButton("🔍 HEX VIEWER")
        self.btn_tab_hex.setObjectName("TabBtnHex")
        self.btn_tab_hex.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tab_hex.clicked.connect(lambda: self.switch_display_tab("HEX"))

        self.btn_tab_body = QPushButton("🧬 BODY VIEWER")
        self.btn_tab_body.setObjectName("TabBtnBody")
        self.btn_tab_body.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tab_body.clicked.connect(lambda: self.switch_display_tab("BODY"))

        tab_bar_layout.addWidget(self.btn_tab_terminal)
        tab_bar_layout.addWidget(self.btn_tab_hex)
        tab_bar_layout.addWidget(self.btn_tab_body)
        tab_bar_layout.addStretch()

        display_container_layout.addWidget(self.tab_btn_bar)

        # Stacked Widget to switch between Terminal and Hex Viewer
        self.display_stack = QStackedWidget()
        self.display_stack.setObjectName("DisplayStack")

        # Page 0: Terminal Panel
        terminal_widget = QWidget()
        terminal_layout = QVBoxLayout(terminal_widget)
        terminal_layout.setContentsMargins(0, 0, 0, 0)
        terminal_layout.setSpacing(4)
        
        self.terminal_label_widget = QLabel("TERMINAL OUTPUT")
        self.terminal_label_widget.setStyleSheet("font-weight: bold; font-family: monospace; color: #888888; font-size: 11px; padding: 2px 4px;")
        terminal_layout.addWidget(self.terminal_label_widget)

        self.terminal = WatermarkTerminal()
        self.terminal.anchorClicked.connect(self.handle_terminal_link)
        terminal_layout.addWidget(self.terminal)

        self.display_stack.addWidget(terminal_widget)  # Index 0: Terminal

        # Page 1: Hex Viewer Panel
        self.hex_widget = QWidget()
        self.hex_widget.setObjectName("HexWidget")
        self.hex_widget.setAcceptDrops(True)
        
        hex_layout = QVBoxLayout(self.hex_widget)
        hex_layout.setContentsMargins(0, 0, 0, 0)
        hex_layout.setSpacing(2)
        
        # Hex Viewer Title Bar with Recent Files button
        hex_header = QHBoxLayout()
        hex_header.setContentsMargins(4, 2, 4, 2)
        self.hex_label_widget = QLabel("HEX VIEWER")
        self.hex_label_widget.setObjectName("HexLabel")
        self.hex_label_widget.setStyleSheet("font-weight: bold; font-family: monospace; color: #888888; font-size: 11px; padding: 2px 4px;")
        hex_header.addWidget(self.hex_label_widget)
        hex_header.addStretch()
        
        hex_header_w = QWidget()
        hex_header_w.setLayout(hex_header)
        hex_layout.addWidget(hex_header_w)

        self.hex_tabs = QTabWidget()
        self.hex_tabs.setTabsClosable(True)
        self.hex_tabs.tabCloseRequested.connect(self.close_hex_tab)
        self.hex_tabs.tabBar().setMovable(True)  # Tabs are draggable/re-orderable
        self.hex_tabs.tabBar().tabBarDoubleClicked.connect(self._on_tab_double_clicked)
        self.hex_tabs.setStyleSheet("")
        
        self.add_tab_btn = QPushButton("+")
        self.add_tab_btn.setFixedSize(30, 25)
        self.add_tab_btn.setStyleSheet("background-color: transparent; font-weight: bold; border: none; color: #00f3ff; font-size: 14px;")
        self.add_tab_btn.clicked.connect(lambda: self.add_new_hex_tab("New Tab"))
        self.hex_tabs.setCornerWidget(self.add_tab_btn)
        
        hex_layout.addWidget(self.hex_tabs)
        
        # Hex Viewer Status Bar
        self.hex_status_bar = QWidget()
        self.hex_status_bar.setFixedHeight(24)
        self.hex_status_bar.setStyleSheet(
            "background-color: #0d0f1a; border-top: 1px solid #1f2233;"
        )
        sb_layout = QHBoxLayout(self.hex_status_bar)
        sb_layout.setContentsMargins(8, 0, 8, 0)
        sb_layout.setSpacing(16)
        
        _sb_style = "color: #888; font-size: 10px; font-family: Consolas, monospace;"
        _sb_val_style = "color: #00f3ff; font-size: 10px; font-family: Consolas, monospace; font-weight: bold;"
        
        sb_layout.addWidget(self._sb_label("Offset:", _sb_style))
        self.sb_offset = QLabel("-"); self.sb_offset.setStyleSheet(_sb_val_style)
        sb_layout.addWidget(self.sb_offset)
        
        sb_layout.addWidget(self._sb_sep())
        sb_layout.addWidget(self._sb_label("Selection:", _sb_style))
        self.sb_selection = QLabel("-"); self.sb_selection.setStyleSheet(_sb_val_style)
        sb_layout.addWidget(self.sb_selection)
        
        sb_layout.addWidget(self._sb_sep())
        sb_layout.addWidget(self._sb_label("File Size:", _sb_style))
        self.sb_filesize = QLabel("-"); self.sb_filesize.setStyleSheet(_sb_val_style)
        sb_layout.addWidget(self.sb_filesize)
        
        sb_layout.addWidget(self._sb_sep())
        self.sb_mode = QLabel("OVR"); self.sb_mode.setStyleSheet("color: #ffa500; font-size: 10px; font-family: Consolas; font-weight: bold;")
        sb_layout.addWidget(self.sb_mode)
        
        sb_layout.addStretch()
        
        sb_layout.addWidget(self._sb_label("RAM:", _sb_style))
        self.sb_ram = QLabel("-"); self.sb_ram.setStyleSheet(_sb_val_style)
        sb_layout.addWidget(self.sb_ram)
        
        hex_layout.addWidget(self.hex_status_bar)
        
        # Status Bar update timer
        self._sb_timer = QTimer(self)
        self._sb_timer.timeout.connect(self._update_hex_status_bar)
        self._sb_timer.start(1000)  # update every 1 second
        
        # Connect EventBus to update status bar on cursor/selection
        from core_workspace import event_bus as _eb
        _eb.cursor_moved.connect(self._sb_on_cursor)
        _eb.selection_changed.connect(self._sb_on_selection)
        
        # Add initial tab
        self.add_new_hex_tab("Main BIOS")

        self.display_stack.addWidget(self.hex_widget)  # Index 1: Hex Viewer

        # Page 2: Body Viewer Panel (Empty container for future components)
        self.body_widget = QWidget()
        self.body_widget.setObjectName("BodyWidget")
        body_layout = QVBoxLayout(self.body_widget)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(4)
        self.display_stack.addWidget(self.body_widget)  # Index 2: Body Viewer

        display_container_layout.addWidget(self.display_stack)

        self.main_display_container.setMinimumWidth(650)
        self.panels_splitter.addWidget(self.main_display_container)

        # DMI Panel (Right of display container)
        self.dmi_panel_widget = QWidget()
        self.dmi_panel_widget.setObjectName("DMIPanelWidget")
        self.dmi_panel_widget.setMinimumWidth(250)
        self.dmi_panel_widget.setMaximumWidth(400)
        self.setup_dmi_panel(self.dmi_panel_widget)
        self.panels_splitter.addWidget(self.dmi_panel_widget)
        
        # Set shared display to take 70% space and DMI panel to take 30%
        self.panels_splitter.setSizes([700, 300])
        content_layout.addWidget(self.panels_splitter, 2)
        
        # Install event filter for hex viewer drop event
        self.hex_widget_filter = HexWidgetEventFilter(self)
        self.hex_widget.installEventFilter(self.hex_widget_filter)
        self.hex_tabs.setAcceptDrops(True)
        self.hex_tabs.installEventFilter(self.hex_widget_filter)
        
        # Ensure default display is always TERMINAL log by default on startup
        from PySide6.QtCore import QSettings
        settings = QSettings("R1AILAB", "BIOS_TOOL")
        settings.setValue("detached_hex_viewer", False)
        self.switch_display_tab("TERMINAL")
        
        # Internet Status Indicator & Logs (Bottom Right)
        status_footer = QHBoxLayout()
        status_footer.setSpacing(8)
        
        self.btn_show_logs = QPushButton("SHOW LOGS")
        self.btn_show_logs.setObjectName("LogButton")
        self.btn_show_logs.clicked.connect(self.show_logs_popup)
        status_footer.addWidget(self.btn_show_logs)

        # Version Badge placed directly beside SHOW LOGS
        cur_v = "R1.1.0.0"
        try:
            from update_manager import get_local_version
            cur_v = get_local_version()
        except Exception:
            pass
        self.lbl_version_badge = QLabel(f"VERSION {cur_v}")
        self.lbl_version_badge.setStyleSheet("""
            QLabel {
                color: #00f2ff;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1a2228, stop:1 #0f1418);
                border: 1px solid #1f3640;
                border-radius: 4px;
                padding: 4px 10px;
                font-family: 'Segoe UI', Consolas, sans-serif;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }
        """)
        status_footer.addWidget(self.lbl_version_badge)
        
        status_footer.addStretch()

        # Internet Status Indicator
        self.net_status_widget = InternetStatusWidget()
        status_footer.addWidget(self.net_status_widget)
        
        content_layout.addLayout(status_footer)

        main_layout.addWidget(content_wrapper)
    def setup_dmi_panel(self, parent_widget):
        layout = QVBoxLayout(parent_widget)
        layout.setContentsMargins(5, 0, 5, 0)
        
        # Title
        title_label = QLabel("DMI INFORMATION")
        title_label.setStyleSheet("font-weight: bold; font-family: 'Segoe UI', sans-serif; font-size: 12px; color: #4cd3e3; letter-spacing: 1px; margin-bottom: 6px;")
        layout.addWidget(title_label)
        
        # Group Box
        dmi_group = QGroupBox()
        dmi_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #283038;
                border-radius: 8px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #22272b, stop:1 #191c1f);
            }
        """)
        
        form_layout = QFormLayout(dmi_group)
        form_layout.setContentsMargins(12, 14, 12, 14)
        form_layout.setSpacing(10)
        
        # Helper to create styled labels
        def create_value_label():
            lbl = QLabel("N/A")
            lbl.setStyleSheet("color: #556270; font-family: Consolas, monospace; font-size: 11px; font-weight: bold; background: #14171a; border: 1px solid #273038; border-radius: 4px; padding: 2px 6px;")
            lbl.setWordWrap(True)
            lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            return lbl
        
        def create_key_label(text):
            lbl = QLabel(text)
            lbl.setStyleSheet("color: #94a3b8; font-family: 'Segoe UI', sans-serif; font-size: 11px; font-weight: 600;")
            return lbl

        self.dmi_lbl_brand = create_value_label()
        self.dmi_lbl_model = create_value_label()
        self.dmi_lbl_platform = create_value_label()
        self.dmi_lbl_mac = create_value_label()
        self.dmi_lbl_serial = create_value_label()
        
        form_layout.addRow(create_key_label("Brand:"), self.dmi_lbl_brand)
        form_layout.addRow(create_key_label("Model:"), self.dmi_lbl_model)
        form_layout.addRow(create_key_label("Platform:"), self.dmi_lbl_platform)
        form_layout.addRow(create_key_label("MAC Addr:"), self.dmi_lbl_mac)
        form_layout.addRow(create_key_label("Serial No:"), self.dmi_lbl_serial)
        
        layout.addWidget(dmi_group)
        
        # DMI Action Buttons (SAVE, LOAD, APPLY)
        dmi_btn_layout = QVBoxLayout()
        dmi_btn_layout.setSpacing(6)
        dmi_btn_layout.setContentsMargins(0, 8, 0, 4)
        
        row_save_load = QHBoxLayout()
        row_save_load.setSpacing(6)
        
        self.btn_save_dmi = QPushButton("SAVE DMI")
        self.btn_save_dmi.setEnabled(False) # Disabled until valid Model or Serial DMI info is present!
        self.btn_save_dmi.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_dmi.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #252a2e, stop:1 #1c2024);
                color: #4cd3e3;
                border: 1px solid #2ac4db;
                border-radius: 6px;
                padding: 7px 10px;
                font-size: 11px;
                font-weight: bold;
                font-family: 'Segoe UI', sans-serif;
            }
            QPushButton:hover {
                background: #2ac4db;
                color: #0b151a;
            }
            QPushButton:disabled {
                background: #181b1e;
                color: #484f58;
                border-color: #24292e;
            }
        """)
        self.btn_save_dmi.clicked.connect(self.save_dmi_handler)
        row_save_load.addWidget(self.btn_save_dmi)
        
        self.btn_load_dmi = QPushButton("LOAD DMI")
        self.btn_load_dmi.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_load_dmi.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #252a2e, stop:1 #1c2024);
                color: #ffb74d;
                border: 1px solid #d99b26;
                border-radius: 6px;
                padding: 7px 10px;
                font-size: 11px;
                font-weight: bold;
                font-family: 'Segoe UI', sans-serif;
            }
            QPushButton:hover {
                background: #ffb74d;
                color: #0b151a;
            }
            QPushButton:disabled {
                background: #181b1e;
                color: #484f58;
                border-color: #24292e;
            }
        """)
        self.btn_load_dmi.clicked.connect(self.load_dmi_handler)
        row_save_load.addWidget(self.btn_load_dmi)
        
        dmi_btn_layout.addLayout(row_save_load)
        
        self.btn_apply_dmi = QPushButton("APPLY DMI TO BIOS")
        self.btn_apply_dmi.setEnabled(False) # Enabled ONLY after valid DMI file is loaded
        self.btn_apply_dmi.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_apply_dmi.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8fe3ea, stop:0.4 #3598a6, stop:1 #247d8a);
                color: #0d171c;
                border: 1px solid #0ef6fd;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 11px;
                font-weight: 800;
                font-family: 'Segoe UI', sans-serif;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background: #0ef6fd;
                color: #000000;
            }
            QPushButton:disabled {
                background: #181b1e;
                color: #454f59;
                border: 1px solid #23282d;
            }
        """)
        self.btn_apply_dmi.clicked.connect(self.apply_dmi_handler)
        dmi_btn_layout.addWidget(self.btn_apply_dmi)
        
        layout.addLayout(dmi_btn_layout)
        
        # Recent Files button below DMI info
        from PySide6.QtWidgets import QMenu
        self.btn_recent_files = QPushButton("Recent Files ▾")
        self.btn_recent_files.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #252a2e, stop:1 #1c2024); color: #c8d6e0; border: 1px solid #333d47;"
            "border-radius: 6px; padding: 6px 12px; font-family: 'Segoe UI', sans-serif; font-size: 11px; font-weight: 600; margin-top: 8px;"
        )
        self.btn_recent_files.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_recent_files.clicked.connect(self._show_recent_files_menu)
        layout.addWidget(self.btn_recent_files)
        
        # Programmer Status Indicator
        prog_status_layout = QHBoxLayout()
        prog_status_layout.setContentsMargins(0, 10, 0, 0)
        
        self.programmer_dot = QLabel("●")
        self.programmer_dot.setStyleSheet("color: #ff5252; font-size: 14px; padding: 0 2px;")
        prog_status_layout.addWidget(self.programmer_dot)
        
        self.programmer_status_label = QLabel("PROGRAMMER: DISCONNECTED")
        self.programmer_status_label.setCursor(Qt.PointingHandCursor)
        self.programmer_status_label.mousePressEvent = self.show_license_menu
        self.programmer_status_label.setStyleSheet(
            "background: #2a1c1d; color: #ff5252; font-size: 10px; font-weight: bold; font-family: 'Segoe UI', sans-serif; "
            "border: 1px solid #4a2123; border-radius: 6px; padding: 2px 8px;"
        )
        prog_status_layout.addWidget(self.programmer_status_label)
        prog_status_layout.addStretch()
        
        layout.addLayout(prog_status_layout)
        
        layout.addStretch()

    def _set_dmi_label(self, lbl, value):
        """Update a DMI label: cyan+bold if real value, grey if N/A."""
        if value and value not in ("N/A", "Unknown", "", "Detecting..."):
            lbl.setText(value)
            lbl.setStyleSheet(
                "color: #4cd3e3;"
                "background-color: #172227;"
                "border: 1px solid #1f4a56;"
                "font-family: Consolas, monospace;"
                "font-weight: bold;"
                "border-radius: 4px;"
                "padding: 2px 6px;"
            )
        else:
            lbl.setText(value or "N/A")
            lbl.setStyleSheet(
                "color: #556270;"
                "background-color: #14171a;"
                "border: 1px solid #273038;"
                "font-family: Consolas, monospace;"
                "font-weight: bold;"
                "border-radius: 4px;"
                "padding: 2px 6px;"
            )

    def _refresh_save_dmi_state(self):
        """
        Dynamically enables SAVE DMI button ONLY if real DMI information is present:
        Requires Model OR Serial Number (or both).
        If only Brand is present, or values are N/A / empty, SAVE DMI remains DISABLED!
        """
        if not hasattr(self, 'btn_save_dmi'):
            return

        def _is_valid_dmi_value(val):
            if not val:
                return False
            s = str(val).strip()
            return s not in ("", "N/A", "Unknown", "None", "Detecting...", "?")

        model_text = self.dmi_lbl_model.text() if hasattr(self, 'dmi_lbl_model') else ""
        serial_text = self.dmi_lbl_serial.text() if hasattr(self, 'dmi_lbl_serial') else ""

        has_model = _is_valid_dmi_value(model_text)
        has_serial = _is_valid_dmi_value(serial_text)

        # Enabled if Model exists OR Serial exists (or both). Brand alone is NOT enough!
        can_save = has_model or has_serial
        self.btn_save_dmi.setEnabled(can_save)

    @Slot(str, str, str, str, str)
    def _on_dmi_update(self, brand, model, platform, mac, serial):
        """Slot: receives DMI data from background thread via signal and updates UI labels."""
        if hasattr(self, 'dmi_lbl_brand'):
            self._set_dmi_label(self.dmi_lbl_brand, brand)
            self._set_dmi_label(self.dmi_lbl_model, model)
            self._set_dmi_label(self.dmi_lbl_platform, platform)
            self._set_dmi_label(self.dmi_lbl_mac, mac)
            self._set_dmi_label(self.dmi_lbl_serial, serial)
            
            # Dynamically update SAVE DMI button state (Model or Serial required)
            self._refresh_save_dmi_state()

            # TRIGGER DYNAMIC BRAND TOOLS
            self._update_brand_tools(brand)

    @Slot(str)
    def _update_brand_tools(self, dmi_brand):
        """Dynamically rename sidebar action buttons based on DMI brand."""
        if hasattr(self, 'brand_tools_group'):
            self.brand_tools_group.hide()

        # Unknown / empty brand: reset button labels
        if not dmi_brand or dmi_brand in ("N/A", "Unknown", "", "Detecting..."):
            if hasattr(self, 'btn_smart_me_fix'):
                self.btn_smart_me_fix.setText("SMART ME FIX")
            if hasattr(self, 'btn_extract_dmi'):
                self.btn_extract_dmi.setText("EXTRACT DMI")
            if hasattr(self, 'btn_dmi_migrate'):
                self.btn_dmi_migrate.setText("BIOS RG FIX")
            if hasattr(self, 'btn_password_remove'):
                self.btn_password_remove.setText("PASSWORD REMOVE")
            return

        # Try to find a matching brand plugin or brand name
        plugin = BrandManager.get_plugin_for_brand(dmi_brand)
        if plugin:
            brand_matches = [b for b in plugin.SUPPORTED_BRANDS
                             if b.upper() in dmi_brand.upper() or dmi_brand.upper() in b.upper()]
            display_name = min(brand_matches, key=len) if brand_matches else dmi_brand
        else:
            display_name = dmi_brand
        display_name = display_name.split()[0].upper()

        # Rename main action buttons to reflect the brand & ensure they are enabled
        if hasattr(self, 'btn_smart_me_fix'):
            self.btn_smart_me_fix.setText(f"{display_name} ME CLEAN")
            self.btn_smart_me_fix.setEnabled(True)
        if hasattr(self, 'btn_extract_dmi'):
            self.btn_extract_dmi.setText(f"{display_name} DMI EX")
            self.btn_extract_dmi.setEnabled(True)
        if hasattr(self, 'btn_dmi_migrate'):
            self.btn_dmi_migrate.setText(f"{display_name} RG FIX")
            self.btn_dmi_migrate.setEnabled(True)
        if hasattr(self, 'btn_password_remove'):
            self.btn_password_remove.setText(f"{display_name} PASS REMOVE")
            self.btn_password_remove.setEnabled(True)
        if hasattr(self, 'btn_save_fix'):
            self.btn_save_fix.setEnabled(True)
        if hasattr(self, 'btn_apply_patches'):
            self.btn_apply_patches.setEnabled(True)

    def setup_sidebar(self, layout):
        # Ã¢â€â‚¬Ã¢â€â‚¬ Outer container frame (the full sidebar, fixed width) Ã¢â€â‚¬Ã¢â€â‚¬
        outer_sidebar = QFrame()
        outer_sidebar.setObjectName("Sidebar")
        outer_sidebar.setMinimumWidth(210)
        outer_sidebar.setMaximumWidth(210)
        outer_layout = QVBoxLayout(outer_sidebar)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â
        # SECTION 1: LOGO + BRANDING Ã¢â‚¬â€ PINNED, NEVER SCROLLS
        # Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â
        branding_widget = QWidget()
        branding_widget.setObjectName("BrandingWidget")
        branding_layout = QVBoxLayout(branding_widget)
        branding_layout.setContentsMargins(10, 20, 10, 10)
        branding_layout.setSpacing(5)

        # Logo
        logo_label = QLabel()
        logo_label.setMinimumSize(150, 150)
        logo_path = get_resource_path(os.path.join("assets", "R1AILAB.png"))
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            scaled_pixmap = pixmap.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        branding_layout.addWidget(logo_label)

        # Name
        title = QLabel("R1 BIOS TOOL")
        title.setObjectName("Title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #4cd3e3; font-family: 'Segoe UI', sans-serif; font-size: 15px; font-weight: 800; letter-spacing: 2px; padding: 5px 10px;")
        branding_layout.addWidget(title)

        # Add branding directly to outer layout
        outer_layout.addWidget(branding_widget)

        # Thin separator line below logo
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #282f37; max-height: 1px; border: none;")
        outer_layout.addWidget(separator)

        # SECTION 2: SCROLLABLE BUTTONS AREA
        scroll_content = QWidget()
        scroll_content.setObjectName("ScrollContent")
        scroll_content.setStyleSheet("QWidget#ScrollContent { background: transparent; }")
        sidebar_layout = QVBoxLayout(scroll_content)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # ENTERPRISE ACTION ENGINE STYLING
        cyber_btn_style = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #252a2e, stop:1 #1c2024);
                color: #c8d6e0;
                border: 1px solid #333d47;
                border-left: 3px solid #2ac4db;
                border-radius: 6px;
                padding: 10px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.8px;
                margin: 4px 10px;
                min-height: 35px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2ac4db, stop:0.5 #3598a6, stop:1 #1fa2b5);
                border: 1px solid #0ef6fd;
                border-left: 4px solid #ffffff;
                color: #0b151a;
                font-weight: 800;
            }
            QPushButton:pressed {
                background-color: #00e0ed;
                color: #000000;
            }
            QPushButton:disabled {
                background-color: #181b1e;
                color: #454f59;
                border: 1px solid #23282d;
                border-left: 3px solid #2a3036;
            }
        """

        self.btn_smart_me_fix = QPushButton("SMART ME FIX")
        self.btn_smart_me_fix.setEnabled(False)
        self.btn_smart_me_fix.clicked.connect(self.smart_me_fix_handler)
        self.btn_smart_me_fix.setStyleSheet(cyber_btn_style)

        self.btn_dmi_migrate = QPushButton("BIOS RG FIX")
        self.btn_dmi_migrate.setEnabled(False)
        self.btn_dmi_migrate.clicked.connect(self.bios_rg_fix_handler)
        self.btn_dmi_migrate.setStyleSheet(cyber_btn_style)

        self.btn_extract_dmi = QPushButton("EXTRACT DMI")
        self.btn_extract_dmi.setEnabled(False)
        self.btn_extract_dmi.clicked.connect(self.extract_dmi_handler)
        self.btn_extract_dmi.setStyleSheet(cyber_btn_style)

        self.btn_password_remove = QPushButton("PASSWORD REMOVE")
        self.btn_password_remove.setEnabled(True)
        self.btn_password_remove.clicked.connect(self.open_password_remove_dialog)
        self.btn_password_remove.setStyleSheet(cyber_btn_style)

        # Grouped Patches
        self.btn_apply_patches = QPushButton("APPLY PATCHES")
        self.btn_apply_patches.setEnabled(False)
        self.btn_apply_patches.clicked.connect(self.show_patches_menu)
        self.btn_apply_patches.setStyleSheet(cyber_btn_style)

        # Final output
        self.btn_save_fix = QPushButton("SAVE && FIX")
        self.btn_save_fix.setEnabled(False)
        self.btn_save_fix.clicked.connect(self.save_and_fix_handler)
        self.btn_save_fix.setStyleSheet(cyber_btn_style)

        # Sub-buttons for developers or cases where auto fails
        self.btn_advanced_extract = QPushButton("MANUAL EXTRACT")
        self.btn_advanced_extract.setEnabled(False)
        self.btn_advanced_extract.clicked.connect(self.advanced_extract_click_handler)
        self.btn_advanced_extract.setStyleSheet(cyber_btn_style)

        self.btn_universal_extract = QPushButton("UNIVERSAL EXTRACT")
        self.btn_universal_extract.setEnabled(True)
        self.btn_universal_extract.clicked.connect(self.universal_extract_handler)
        self.btn_universal_extract.setStyleSheet(cyber_btn_style)

        self.btn_merge = QPushButton("⚡ MERGE")
        self.btn_merge.setEnabled(True)
        self.btn_merge.clicked.connect(self.merge_handler)
        self.btn_merge.setStyleSheet(cyber_btn_style)
        self.btn_merge.setObjectName("MergeButton")

        self.btn_dell_pfs_extract = QPushButton("DELL PFS EXTRACT")
        self.btn_dell_pfs_extract.setEnabled(True)
        self.btn_dell_pfs_extract.clicked.connect(self.dell_pfs_extract_handler)
        self.btn_dell_pfs_extract.setStyleSheet(cyber_btn_style)

        self.btn_ec_finder = QPushButton("EC FINDER")
        self.btn_ec_finder.setEnabled(True)
        self.btn_ec_finder.clicked.connect(self.ec_finder_handler)
        self.btn_ec_finder.setStyleSheet(cyber_btn_style)

        self.btn_settings = QPushButton("SETTINGS")
        self.btn_settings.setEnabled(True)
        self.btn_settings.clicked.connect(self.show_settings_dialog)
        self.btn_settings.setStyleSheet(cyber_btn_style)

        # Labels for sections
        self.label_main = QLabel("── ACTION ENGINE ──")
        self.label_main.setStyleSheet("color: #64748b; font-family: 'Segoe UI', sans-serif; font-size: 10px; font-weight: bold; letter-spacing: 1.5px; margin-top: 15px;")
        self.label_main.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.label_tools = QLabel("── UTILITIES ──")
        self.label_tools.setStyleSheet("color: #64748b; font-family: 'Segoe UI', sans-serif; font-size: 10px; font-weight: bold; letter-spacing: 1.5px; margin-top: 15px;")
        self.label_tools.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sidebar_layout.addWidget(self.label_main)
        sidebar_layout.addWidget(self.btn_smart_me_fix)
        sidebar_layout.addWidget(self.btn_dmi_migrate)
        sidebar_layout.addWidget(self.btn_extract_dmi)
        sidebar_layout.addWidget(self.btn_password_remove)
        sidebar_layout.addWidget(self.btn_apply_patches)

        sidebar_layout.addWidget(self.btn_save_fix)
        
        sidebar_layout.addStretch()
        sidebar_layout.addWidget(self.label_tools)
        sidebar_layout.addWidget(self.btn_advanced_extract)
        sidebar_layout.addWidget(self.btn_universal_extract)
        sidebar_layout.addWidget(self.btn_merge)
        sidebar_layout.addWidget(self.btn_dell_pfs_extract)
        sidebar_layout.addWidget(self.btn_ec_finder)
        sidebar_layout.addWidget(self.btn_settings)
        
        # Add Theme Toggle Switch (single pill button)
        self.theme_toggle = ThemeToggleSwitch()
        self.theme_toggle.set_state(getattr(self, 'is_light_mode', False), animate=False)
        
        # Add Hex Toggle Switch (Default to off on startup so Terminal Log is active)
        self.hex_toggle = HexToggleSwitch()
        self.hex_toggle.set_state(False, animate=False)

        toggle_wrapper = QHBoxLayout()
        toggle_wrapper.addStretch()
        toggle_wrapper.addWidget(self.theme_toggle)
        toggle_wrapper.addSpacing(10)
        toggle_wrapper.addWidget(self.hex_toggle)
        toggle_wrapper.addStretch()
        sidebar_layout.addLayout(toggle_wrapper)
        sidebar_layout.addSpacing(10)
        
        # Wrap sidebar in QScrollArea
        scroll_area = QScrollArea()
        scroll_area.setWidget(scroll_content)
        scroll_area.setWidgetResizable(True)
        # Hide the horizontal scrollbar; vertical scrollbar appears only when needed
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        # Remove borders and match background so it looks integrated
        scroll_area.setStyleSheet("QScrollArea, QScrollArea > QWidget > QWidget { border: none; background: transparent; } QScrollBar:vertical { width: 8px; }")
        
        
        
        
        
        outer_layout.addWidget(scroll_area)
        layout.addWidget(outer_sidebar)

    def apply_theme(self, is_light: bool):
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QSettings
        app = QApplication.instance()
        
        if is_light:
            app.setStyleSheet(STYLESHEET_LIGHT)
            self.is_light_mode = True
        else:
            app.setStyleSheet(STYLESHEET_DARK)
            self.is_light_mode = False
            
        settings = QSettings("R1AILAB", "BIOS_TOOL")
        settings.setValue("light_mode", self.is_light_mode)
        
        # Sync toggle switch visual state
        if hasattr(self, 'theme_toggle'):
            self.theme_toggle._is_light = self.is_light_mode
            self.theme_toggle.set_state(self.is_light_mode)
        
        # Force refresh hex tabs if they exist
        if hasattr(self, 'hex_tabs'):
            for i in range(self.hex_tabs.count()):
                tab = self.hex_tabs.widget(i)
                tab.hex_model.is_light_mode = self.is_light_mode
                tab.hex_model.layoutChanged.emit()

    def show_settings_dialog(self):
        dialog = SettingsDialog(self)
        if dialog.exec():
            from PySide6.QtCore import QSettings
            settings = QSettings("R1AILAB", "BIOS_TOOL")
            detached = settings.value("detached_hex_viewer", False, type=bool)
            self.toggle_hex_viewer_mode(detached)

    def switch_display_tab(self, mode: str):
        """Switch between TERMINAL, HEX VIEWER, and BODY VIEWER inside the shared display container."""
        active_style = (
            "QPushButton {"
            "    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2ac4db, stop:1 #1fa2b5);"
            "    color: #0c161c;"
            "    font-family: 'Segoe UI', sans-serif;"
            "    font-size: 11px;"
            "    font-weight: 700;"
            "    border: 1px solid #0ef6fd;"
            "    border-radius: 6px;"
            "    padding: 6px 18px;"
            "    margin: 0px;"
            "    text-align: center;"
            "}"
        )
        inactive_style = (
            "QPushButton {"
            "    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #252a2e, stop:1 #1c2024);"
            "    color: #94a3b8;"
            "    font-family: 'Segoe UI', sans-serif;"
            "    font-size: 11px;"
            "    font-weight: 600;"
            "    border: 1px solid #2d363f;"
            "    border-radius: 6px;"
            "    padding: 6px 18px;"
            "    margin: 0px;"
            "    text-align: center;"
            "}"
            "QPushButton:hover {"
            "    background: #2a3138;"
            "    color: #4cd3e3;"
            "    border: 1px solid #3d4a57;"
            "}"
        )
        mode_upper = mode.upper()
        is_hex = (mode_upper == "HEX")
        is_body = (mode_upper == "BODY")
        is_terminal = not (is_hex or is_body)

        if hasattr(self, 'display_stack'):
            if is_body:
                self.display_stack.setCurrentIndex(2)
            elif is_hex:
                self.display_stack.setCurrentIndex(1)
            else:
                self.display_stack.setCurrentIndex(0)

        if hasattr(self, 'btn_tab_hex'):
            self.btn_tab_hex.setStyleSheet(active_style if is_hex else inactive_style)
        if hasattr(self, 'btn_tab_terminal'):
            self.btn_tab_terminal.setStyleSheet(active_style if is_terminal else inactive_style)
        if hasattr(self, 'btn_tab_body'):
            self.btn_tab_body.setStyleSheet(active_style if is_body else inactive_style)

        if hasattr(self, 'hex_toggle') and self.hex_toggle._is_on != is_hex:
            self.hex_toggle.set_state(is_hex, animate=True)
        from PySide6.QtCore import QSettings
        settings = QSettings("R1AILAB", "BIOS_TOOL")
        settings.setValue("detached_hex_viewer", is_hex)

    def toggle_hex_viewer_mode(self, detached: bool):
        self.switch_display_tab("HEX" if detached else "TERMINAL")

    def show_language_dialog(self):
        dialog = LanguageDialog(self)
        if dialog.exec():
            selected_code = dialog.get_selected_language()
            if selected_code and selected_code != lm.current_lang:
                lm.save_preference(selected_code)
                self.retranslate_ui()

    def show_report_settings_dialog(self):
        dialog = ReportSettingsDialog(self.report_manager, self)
        if dialog.exec():
            if getattr(self, 'current_bios_file', None) and os.path.exists(self.current_bios_file):
                self.log_to_terminal("[INFO] Report settings updated. Refreshing analysis...")
                self.load_bios_file(self.current_bios_file)

    def show_help_dialog(self):
        from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                                        QLabel, QPushButton, QFrame)
        from PySide6.QtCore import Qt, QUrl, QByteArray
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtSvgWidgets import QSvgWidget

        # --- Links ---
        YOUTUBE_URL  = "https://www.youtube.com/@r1itlab"
        FACEBOOK_URL = "https://www.facebook.com/r1itlab"
        WHATSAPP_URL = "https://wa.me/880XXXXXXXXXX"

        # --- Embedded SVG icons ---
        SVG_YOUTUBE = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
          <path fill="#FF0000" d="M23.5 6.2a3 3 0 0 0-2.1-2.1C19.5 3.5 12 3.5 12 3.5s-7.5 0-9.4.6A3 3 0 0 0 .5 6.2C0 8.1 0 12 0 12s0 3.9.5 5.8a3 3 0 0 0 2.1 2.1C4.5 20.5 12 20.5 12 20.5s7.5 0 9.4-.6a3 3 0 0 0 2.1-2.1C24 15.9 24 12 24 12s0-3.9-.5-5.8z"/>
          <polygon fill="#FFFFFF" points="9.5,15.5 15.8,12 9.5,8.5"/>
        </svg>"""

        SVG_FACEBOOK = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
          <circle cx="12" cy="12" r="12" fill="#1877F2"/>
          <path fill="#FFFFFF" d="M16.7 15.5l.5-3.1h-3v-2c0-.9.4-1.7 1.7-1.7h1.3V6s-1.2-.2-2.3-.2c-2.4 0-3.9 1.4-3.9 4v2.4H8v3.1h3V24c.7.1 1.3.1 2 .1s1.3 0 2-.1v-8.5h2.7z"/>
        </svg>"""

        SVG_WHATSAPP = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
          <circle cx="12" cy="12" r="12" fill="#25D366"/>
          <path fill="#FFFFFF" d="M17.5 14.3c-.3-.1-1.8-.9-2.1-1-.3-.1-.5-.1-.7.2s-.8 1-1 1.2c-.2.2-.4.2-.7.1-1.8-.9-3-1.7-4.2-3.8-.3-.6.3-.6.9-1.7.1-.2 0-.4-.1-.5L8.5 7c-.3-.6-.6-.5-.8-.5H7c-.2 0-.5.1-.8.4C5.9 7.2 5 8 5 9.7c0 1.7 1.2 3.4 1.4 3.6.2.2 2.3 3.6 5.7 5 2.1.9 3 1 4 .8.7-.1 2.1-.9 2.4-1.7.3-.8.3-1.5.2-1.7-.1-.1-.3-.2-.7-.4z"/>
        </svg>"""

        dialog = QDialog(self)
        dialog.setWindowTitle("Help & Support")
        dialog.setFixedSize(460, 390)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #171a1d;
            }
            QLabel  { color: #e0e0e0; font-family: 'Segoe UI', sans-serif; }
            QPushButton {
                background: transparent; border: none;
                color: #e0e0e0; font-family: 'Segoe UI', sans-serif;
            }
        """)

        card = QFrame(dialog)
        card.setGeometry(12, 12, 436, 366)
        card.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #252a2e, stop:1 #1c2024);
                border: 1px solid #2d363f;
                border-radius: 12px;
            }
        """)

        main_layout = QVBoxLayout(card)
        main_layout.setContentsMargins(24, 20, 24, 18)
        main_layout.setSpacing(12)

        # Header
        h = QLabel("R1 BIOS TOOL")
        h.setStyleSheet("font-size: 20px; font-weight: 800; color: #4cd3e3; letter-spacing: 2px; border: none; background: transparent;")
        h.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(h)

        sub = QLabel("Official Help & Engineering Support")
        sub.setStyleSheet("font-size: 11px; color: #94a3b8; border: none; background: transparent;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(sub)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("background: #2d363f; max-height: 1px; border: none;")
        main_layout.addWidget(divider)

        # --- Row builder with QSvgWidget icon ---
        def make_row(svg_data, accent_color, platform_name, display_text, url):
            row = QFrame()
            row.setCursor(Qt.CursorShape.PointingHandCursor)
            row.setStyleSheet(f"""
                QFrame {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #20252a, stop:1 #1a1e22);
                    border-radius: 8px;
                    border: 1px solid #2d363f;
                    border-left: 3px solid {accent_color};
                }}
                QFrame:hover {{
                    background: #252d34;
                    border-color: #3b4754;
                    border-left: 3px solid {accent_color};
                }}
            """)
            rl = QHBoxLayout(row)
            rl.setContentsMargins(12, 8, 12, 8)
            rl.setSpacing(14)

            # Real SVG logo
            logo = QSvgWidget()
            logo.load(QByteArray(svg_data))
            logo.setFixedSize(32, 32)
            logo.setStyleSheet("border: none; background: transparent;")
            rl.addWidget(logo)

            # Text column
            tc = QVBoxLayout()
            tc.setSpacing(2)
            pname = QLabel(platform_name)
            pname.setStyleSheet("font-weight: bold; font-size: 12px; color: #ffffff; border: none; background: transparent;")
            plink = QLabel(display_text)
            plink.setStyleSheet(f"font-size: 11px; color: {accent_color}; border: none; background: transparent;")
            tc.addWidget(pname)
            tc.addWidget(plink)
            rl.addLayout(tc, 1)

            arr = QPushButton("›")
            arr.setStyleSheet(f"color: {accent_color}; font-size: 20px; font-weight: bold; border: none; background: transparent;")
            arr.setFixedWidth(24)
            arr.clicked.connect(lambda checked=False, u=url: QDesktopServices.openUrl(QUrl(u)))
            rl.addWidget(arr)

            row.mousePressEvent = lambda e, u=url: QDesktopServices.openUrl(QUrl(u))
            return row

        main_layout.addWidget(make_row(SVG_YOUTUBE,  "#ff4444", "YouTube",  "R1AILAB — BIOS Repair Tutorials", YOUTUBE_URL))
        main_layout.addWidget(make_row(SVG_FACEBOOK, "#2ac4db", "Facebook", "R1AILAB — Official Community",        FACEBOOK_URL))
        main_layout.addWidget(make_row(SVG_WHATSAPP, "#00ff88", "WhatsApp", "Engineering Direct Support",          WHATSAPP_URL))

        main_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.setFixedHeight(34)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3c444a, stop:1 #2d3338);
                color: #c8d6e0;
                border: 1px solid #4a545c;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #47525a;
                color: #ffffff;
                border-color: #5c6873;
            }
        """)
        close_btn.clicked.connect(dialog.accept)
        main_layout.addWidget(close_btn)

        dialog.exec()

    def show_update_dialog(self):
        try:
            from update_manager import UpdateDialog
            dlg = UpdateDialog(self)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "Update Error", f"Failed to open update manager:\n{e}")

    def check_startup_update(self):
        """Silently checks GitHub on application startup and prompts if a new version is available."""
        try:
            from update_manager import UpdateCheckWorker, is_newer_version, get_local_version, DEFAULT_UPDATE_URL
            
            def on_check_finished(success, data, error_msg):
                if not success:
                    return
                remote_ver = str(data.get("version", "0.0.0")).strip()
                local_ver = get_local_version()
                
                if is_newer_version(remote_ver, local_ver):
                    self.log_to_terminal(f"[SYSTEM] NEW UPDATE AVAILABLE: {remote_ver} (Current: {local_ver})")
                    self.show_update_dialog()
                else:
                    self.log_to_terminal(f"[SYSTEM] Software is up to date ({local_ver}).")

            self._startup_update_worker = UpdateCheckWorker(DEFAULT_UPDATE_URL)
            self._startup_update_worker.check_finished.connect(on_check_finished)
            self._startup_update_worker.start()
        except Exception as e:
            print(f"[!] Startup update check error: {e}")

    def retranslate_ui(self):
        # Update Layout Direction (RTL for Arabic)
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if lm.current_lang == 'ar':
            app.setLayoutDirection(Qt.RightToLeft)
        else:
            app.setLayoutDirection(Qt.LeftToRight)

        # Main window title
        self.setWindowTitle(t("app_title"))
        
        # Sidebar buttons
        self.btn_smart_me_fix.setText(t("btn_smart_me_fix"))
        self.btn_dmi_migrate.setText(t("btn_bios_rg_fix"))
        self.btn_extract_dmi.setText(t("btn_extract_dmi"))
        self.btn_apply_patches.setText(t("btn_apply_patches"))
        self.btn_save_fix.setText(t("btn_save_fix"))
        self.btn_advanced_extract.setText(t("btn_manual_extract"))
        self.btn_settings.setText(t("btn_settings"))
        if hasattr(self, 'btn_language'):
            self.btn_language.setText(t("btn_language") + f" [{lm.current_lang.upper()}]")
            
        # Section labels
        if hasattr(self, 'label_main'):
            self.label_main.setText(t("section_action_engine"))
        if hasattr(self, 'label_tools'):
            self.label_tools.setText(t("section_utilities"))
            
        # Content toolbar buttons (Text only, Driver style)
        self.btn_open.setText("OPEN")
        self.btn_open.setToolTip(t("btn_open", "OPEN BIOS"))
        if not self.is_auto_saving:
            self.btn_save.setText("SAVE")
            self.btn_save.setToolTip(t("btn_save", "SAVE CHANGES"))
        if hasattr(self, 'btn_language'):
            self.btn_language.setText(f"LANG [{lm.current_lang.upper()}]")
            self.btn_language.setToolTip(f"{t('btn_language', 'LANGUAGE')} [{lm.current_lang.upper()}]")
        if hasattr(self, 'btn_report'):
            self.btn_report.setText("REPORT")
            self.btn_report.setToolTip(t("btn_report", "REPORT SETTINGS"))
        if hasattr(self, 'btn_help'):
            self.btn_help.setText("HELP")
            self.btn_help.setToolTip(t("btn_help", "HELP & SUPPORT"))
        if hasattr(self, 'btn_update'):
            self.btn_update.setText("UPDATE")
            self.btn_update.setToolTip(t("btn_update", "CHECK FOR UPDATES"))
            
        if hasattr(self, 'lbl_version_badge'):
            cur_v = "R1.1.0.0"
            try:
                from update_manager import get_local_version
                cur_v = get_local_version()
            except Exception:
                pass
            self.lbl_version_badge.setText(f"VERSION {cur_v}")
            
        # Terminal label
        if hasattr(self, 'terminal_label_widget'):
            self.terminal_label_widget.setText(t("terminal_label"))
            
        # Hex label
        if hasattr(self, 'hex_label_widget'):
            self.hex_label_widget.setText(t("hex_label"))
            
        # Logs button
        self.btn_show_logs.setText(t("show_logs"))
        

    @Slot(QUrl)
    def handle_terminal_link(self, url):
        if url.scheme() == "hexjump":
            try:
                self.switch_display_tab("HEX")
                # URL format: hexjump:///0x18F7904
                # url.path() returns '/0x18F7904'  (the leading slash must be stripped)
                path = url.path().strip("/").strip()
                if not path:
                    # Fallback: extract from full URL string
                    path = url.toString().replace("hexjump:///", "").replace("hexjump://", "").strip().lstrip("/")

                # Parse hex value — int() handles '0x' prefix automatically
                offset = int(path, 16)

                if not hasattr(self, 'hex_tabs') or self.hex_tabs.count() == 0:
                    self.log_to_terminal(
                        "[INFO] <font color='#ffaa00'>⚠ Hex Viewer is not open. "
                        "Load a BIOS file and enable the Hex Viewer first, "
                        "then click the offset again.</font>"
                    )
                    return

                tab = self.hex_tabs.currentWidget()
                if tab is None or not hasattr(tab, 'hex_model'):
                    return

                row = offset // 16
                col = offset % 16

                # Bounds check
                if row >= tab.hex_model.rowCount():
                    self.log_to_terminal(
                        f"[WARNING] <font color='#ffaa00'>Offset 0x{offset:X} is out of range for the current file.</font>"
                    )
                    return

                idx = tab.hex_model.index(row, col)

                # Select and scroll to the offset
                tab.hex_view.selectionModel().clearSelection()
                from PySide6.QtCore import QItemSelectionModel
                tab.hex_view.selectionModel().select(
                    idx,
                    QItemSelectionModel.SelectionFlag.Select
                )
                tab.hex_view.scrollTo(idx, QAbstractItemView.ScrollHint.PositionAtCenter)

                # Log success — use terminal.append() directly to avoid re-processing by log_to_terminal
                msg = (
                    f"[INFO] ➜ Jumped to offset "
                    f"<font color='#00ff41'><b>0x{offset:08X}</b></font> "
                    f"<font color='#888888'>(row {row}, col {col})</font>"
                )
                if hasattr(self, 'mea_history'):
                    pass  # Only MEA raw output goes into mea_history
                self.terminal.append(msg)

            except (ValueError, Exception):
                pass

    @Slot(str)
    def log_to_terminal(self, message):
        """Callback for the parser to log messages."""
        if threading.current_thread() is not threading.main_thread():
            QMetaObject.invokeMethod(self, "log_to_terminal", Qt.ConnectionType.QueuedConnection, Q_ARG(str, message))
            return
            
        # Suppress Outdated ME Analyzer and GitHub download links
        msg_clean = message.lower()
        if any(ign in msg_clean for ign in [
            "outdated me analyzer",
            "outdated database",
            "download the latest from",
            "github.com/platomav",
        ]):
            self._last_suppressed_notice = True
            return

        # Suppress separator line immediately following suppressed notice
        if getattr(self, '_last_suppressed_notice', False):
            clean_str = message.replace("[INFO]", "").replace("[WARNING]", "").strip()
            if not clean_str or all(c in "═━-=" for c in clean_str):
                self._last_suppressed_notice = False
                return
            self._last_suppressed_notice = False

        # NOTE: Only MEA raw output is appended to mea_history (in _handle_mea_output_internal)
        # Regular terminal messages must NOT be added here to avoid parser confusion.

        # Interactive Jump: Make hex offsets clickable
        import re
        def replace_offset(match):
            val = match.group(1)
            # Use path-based URL (triple slash) so Qt does NOT try to parse 0x... as hostname
            # hexjump:///0x18F7904  →  scheme=hexjump, path=/0x18F7904
            return f'<a href="hexjump:///{val}" style="color:#00ff41; text-decoration:underline; font-weight:bold;">{val}</a>'
            
        display_message = message
        
        # Add visual checkmarks and colors to SUCCESS and ERROR globally
        if "[SUCCESS]" in display_message:
            # Strip existing weird checkmarks
            display_message = display_message.replace("✓", "").replace("✔", "").strip()
            if not display_message.endswith("✅"):
                display_message += " ✅"
            display_message = display_message.replace("[SUCCESS]", "<font color='#00ff41'><b>[SUCCESS]</b></font>")
            
        elif "[ERROR]" in display_message:
            display_message = display_message.replace("❌", "").replace("✖", "").strip()
            if not display_message.endswith("❌"):
                display_message += " ❌"
            display_message = display_message.replace("[ERROR]", "<font color='#ff3131'><b>[ERROR]</b></font>")
        if "hexjump://" not in display_message:
            display_message = re.sub(r'\b(0x[0-9a-fA-F]+)\b', replace_offset, display_message)

        self.terminal.append(display_message)
        self.overlay_log_signal.emit(message)
        
        # PERSISTENT LOGGING: Save the raw text to app.log (Strip HTML)
        try:
            import re
            # Strip HTML tags like <font color=...> for the log file
            clean_text = re.sub(r'<[^>]+>', '', message)
            # Replace &nbsp; with space
            clean_text = clean_text.replace('&nbsp;', ' ')
            
            with open(self.log_file, "a", encoding="utf-8") as f:
                timestamp = datetime.now().strftime("[%H:%M:%S]")
                f.write(f"{timestamp} {clean_text}\n")
        except Exception:
            pass 
            
        self.terminal.verticalScrollBar().setValue(self.terminal.verticalScrollBar().maximum())
        
        # MONITOR FOR AUTO-SAVE TRIGGER
        if "[INFO] [SUCCESS] Full CSME Clean Completed!" in message:
            self.start_auto_save_countdown()

    @Slot(int)
    def initiate_loader_stop(self, delay_ms=800):
        """Schedules the loading overlay to stop with a snappier feel.
        Using @Slot(int) to support QueuedConnection for perfect log synchronization.
        """
        self.is_task_running = False
        self.progress_signal.emit(100)
        QTimer.singleShot(delay_ms, self.loading_overlay.stop)

    def cleanup_temp_files(self):
        """Removes temporary session files and directories on startup."""
        dirs_to_clear = [self.workspace_dir, "backup_me", "extracted_firmware", "temp"]
        
        for d in dirs_to_clear:
            path = os.path.join(str(get_app_root()), d) if not os.path.isabs(d) else d
            if os.path.exists(path):
                try:
                    shutil.rmtree(path)
                except Exception:
                    pass
        
        # Ensure workspace exists for new tasks
        os.makedirs(self.workspace_dir, exist_ok=True)

    # Status Bar helpers
    def _sb_label(self, text, style):
        lbl = QLabel(text)
        lbl.setStyleSheet(style)
        return lbl

    def _sb_sep(self):
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: #1f2233;")
        sep.setFixedHeight(14)
        return sep

    def _update_hex_status_bar(self):
        """Periodic status bar update – RAM usage."""
        if not hasattr(self, 'sb_ram'): return
        try:
            import psutil, os as _os
            rss = psutil.Process(_os.getpid()).memory_info().rss
            self.sb_ram.setText(f"{rss / 1024 / 1024:.1f} MB")
        except Exception:
            self.sb_ram.setText("-")

    @Slot(object, int)
    def _sb_on_cursor(self, doc, offset):
        if not hasattr(self, 'sb_offset'): return
        if doc and offset >= 0:
            self.sb_offset.setText(f"0x{offset:08X}  ({offset})")
            self.sb_filesize.setText(f"0x{doc.size:X}  ({doc.size:,} B)")
        else:
            self.sb_offset.setText("-")

    @Slot(object, int, int)
    def _sb_on_selection(self, doc, start, length):
        if not hasattr(self, 'sb_selection'): return
        if doc and length > 1:
            self.sb_selection.setText(f"0x{length:X}  ({length:,} B)")
        else:
            self.sb_selection.setText("-")

    def _toggle_insert_mode(self):
        """Toggle INS/OVR mode indicator."""
        if not hasattr(self, 'sb_mode'): return
        current = self.sb_mode.text()
        if current == "OVR":
            self.sb_mode.setText("INS")
            self.sb_mode.setStyleSheet("color: #4CAF50; font-size: 10px; font-family: Consolas; font-weight: bold;")
        else:
            self.sb_mode.setText("OVR")
            self.sb_mode.setStyleSheet("color: #ffa500; font-size: 10px; font-family: Consolas; font-weight: bold;")

    def setup_global_shortcuts(self):
        """Register application-level keyboard shortcuts."""
        QShortcut(QKeySequence("Ctrl+O"), self).activated.connect(self.open_bios_dialog)
        QShortcut(QKeySequence("Ctrl+W"), self).activated.connect(self._close_current_hex_tab)
        QShortcut(QKeySequence("Ctrl+Tab"), self).activated.connect(self._next_hex_tab)
        QShortcut(QKeySequence("Ctrl+Shift+Tab"), self).activated.connect(self._prev_hex_tab)
        QShortcut(QKeySequence(Qt.Key.Key_Insert), self).activated.connect(self._toggle_insert_mode)
        QShortcut(QKeySequence(Qt.Key.Key_F1), self).activated.connect(self.show_shortcuts_dialog)

    def show_shortcuts_dialog(self):
        dlg = ShortcutsReferenceDialog(self)
        dlg.exec()

    def _close_current_hex_tab(self):
        if hasattr(self, 'hex_tabs'):
            self.close_hex_tab(self.hex_tabs.currentIndex())

    def _next_hex_tab(self):
        if not hasattr(self, 'hex_tabs'): return
        n = self.hex_tabs.count()
        if n > 1:
            self.hex_tabs.setCurrentIndex((self.hex_tabs.currentIndex() + 1) % n)

    def _prev_hex_tab(self):
        if not hasattr(self, 'hex_tabs'): return
        n = self.hex_tabs.count()
        if n > 1:
            self.hex_tabs.setCurrentIndex((self.hex_tabs.currentIndex() - 1) % n)

    def initialize_ui_window(self, show_now=True):
        """Initializes tool status, keyboard shortcuts, and optionally brings window to front."""
        if show_now:
            self.show()
            self.raise_()
            self.activateWindow()
        
        self.log_to_terminal("[INFO] R1 BIOS Service Tool started")
        self.log_to_terminal("[INFO] UI initialized and ready")
        
        # Auto-run firmware organization
        self.log_to_terminal("[INFO] Scanning for local firmware files...")
        detect_and_organize_local_firmware(get_app_root(), self.log_to_terminal)
        self.log_to_terminal("[INFO] Main screen loaded, ready for module selection")
        
        # Register global keyboard shortcuts
        self.setup_global_shortcuts()
        
        # Restore last session (re-open last tabs)
        QTimer.singleShot(500, self._restore_session)

    def _restore_session(self):
        """Session restore disabled - hex viewer always starts fresh."""
        pass  # Do not restore previous session files

    def _save_session(self):
        """Persist open tab file paths so they can be restored next launch."""
        from PySide6.QtCore import QSettings
        s = QSettings("R1AILAB", "BIOS_TOOL")
        open_paths = []
        for i in range(self.hex_tabs.count()):
            w = self.hex_tabs.widget(i)
            if hasattr(w, 'file_path') and w.file_path and os.path.exists(w.file_path):
                open_paths.append(w.file_path)
        s.setValue("session/last_open_tabs", open_paths)
        s.setValue("session/recent_files", self._recent_files)

    def _push_recent_file(self, path):
        """Add a file to the recent files list, keeping max 20 entries."""
        if path in self._recent_files:
            self._recent_files.remove(path)
        self._recent_files.insert(0, path)
        self._recent_files = self._recent_files[:20]
        # Update settings immediately
        self._settings.setValue("session/recent_files", self._recent_files)

    def _show_recent_files_menu(self):
        """Show a popup menu of recently opened files."""
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background-color: #171a1d; color: #ffffff; border: 1px solid #3c444d; border-radius: 6px; }"
            "QMenu::item { padding: 6px 20px; font-family: 'Segoe UI', sans-serif; }"
            "QMenu::item:selected { background-color: #3598a6; color: #ffffff; }"
            "QMenu::separator { background-color: #283038; height: 1px; margin: 3px 0px; }"
        )
        if not self._recent_files:
            action = menu.addAction("(No recent files)")
            action.setEnabled(False)
        else:
            for path in self._recent_files:
                name = os.path.basename(path)
                short = path if len(path) < 55 else "..." + path[-52:]
                action = menu.addAction(f"{name}  →  {short}")
                action.setData(path)
            menu.addSeparator()
            menu.addAction("Clear Recent Files").setData("__clear__")
        
        from PySide6.QtGui import QCursor
        chosen = menu.exec(self.btn_recent_files.mapToGlobal(self.btn_recent_files.rect().bottomLeft()))
        if chosen:
            data = chosen.data()
            if data == "__clear__":
                self._recent_files.clear()
                self._settings.setValue("session/recent_files", [])
            elif data and isinstance(data, str) and os.path.exists(data):
                self.prompt_and_load_bios(data)

    def _on_watched_file_changed(self, path):
        """Called when a file being watched has been modified externally."""
        tab = self._watched_tab_map.get(path)
        if not tab: return
        
        idx = self.hex_tabs.indexOf(tab)
        title = os.path.basename(path)
        
        from PySide6.QtWidgets import QMessageBox
        msg = QMessageBox(self)
        msg.setWindowTitle("File Changed Externally")
        msg.setText(f"<b>{title}</b> was modified by another program.\n\nDo you want to reload it?")
        msg.setIcon(QMessageBox.Icon.Warning)
        btn_reload = msg.addButton("Reload", QMessageBox.ButtonRole.AcceptRole)
        msg.addButton("Ignore", QMessageBox.ButtonRole.RejectRole)
        msg.exec()
        
        if msg.clickedButton() == btn_reload:
            try:
                with open(path, "rb") as f:
                    data = f.read()
                if hasattr(tab, 'hex_model'):
                    tab.hex_model.set_data(data)
                    tab.mark_clean()
                self.log_to_terminal(f"[INFO] Reloaded: {title}")
            except Exception as e:
                self.log_to_terminal(f"[ERROR] Reload failed: {e}")

    def toggle_tab_read_only(self, tab):
        """Toggle read-only status on a tab's document."""
        if not hasattr(tab, 'hex_model'): return
        doc = tab.hex_model.document
        doc.is_read_only = not doc.is_read_only
        state = "Read-Only" if doc.is_read_only else "Editable"
        self.log_to_terminal(f"[INFO] Tab '{tab._base_title}' is now {state}")
        # Update tab title to show [R] indicator
        idx = self.hex_tabs.indexOf(tab)
        if idx >= 0:
            prefix = "[R] " if doc.is_read_only else ""
            self.hex_tabs.setTabText(idx, f"{prefix}{tab._base_title}")

    def closeEvent(self, event):
        """Save session before close and clean up child windows."""
        self._save_session()
        # Close hex viewer if it's open as a floating window
        if hasattr(self, 'hex_widget') and self.hex_widget.isVisible():
            self.hex_widget.close()
        super().closeEvent(event)

    @Slot(dict)
    def enable_module_buttons(self, firmware_regions):
        has_file = bool(self.current_bios_file)
        
        # Core Action buttons are always enabled whenever a BIOS file is loaded
        if hasattr(self, 'btn_smart_me_fix'):
            self.btn_smart_me_fix.setEnabled(has_file)
        if hasattr(self, 'btn_dmi_migrate'):
            self.btn_dmi_migrate.setEnabled(has_file)
        if hasattr(self, 'btn_extract_dmi'):
            self.btn_extract_dmi.setEnabled(has_file)
        if hasattr(self, 'btn_apply_patches'):
            self.btn_apply_patches.setEnabled(has_file)
        if hasattr(self, 'btn_save_fix'):
            self.btn_save_fix.setEnabled(has_file)
        if hasattr(self, 'btn_save'):
            self.btn_save.setEnabled(has_file)
        
        # Manual extract as a fallback for packages
        if has_file and self.current_bios_file:
            ext = os.path.splitext(self.current_bios_file)[1].lower()
            if hasattr(self, 'btn_advanced_extract'):
                self.btn_advanced_extract.setEnabled(ext in ['.exe', '.cap', '.pfs', '.pkg'])
        else:
            if hasattr(self, 'btn_advanced_extract'):
                self.btn_advanced_extract.setEnabled(False)

    def automated_repair_bios(self, manual_components=None):
        """
        Full automated BIOS repair via Smart Repair Engine.
        Replaces old manual pipeline - supports all ME versions,
        auto-selects firmware, runs FIT, verifies with MEA,
        and delivers to TESTING_AREA/FINAL BIOS.
        """
        if not self.current_bios_file:
            self.log_to_terminal("[ERROR] No BIOS file is currently loaded.")
            return

        # Step 1: Parse MEA history for firmware info
        history_str = self.mea_history
        mea_meta = parse_mea_output(history_str)

        if not mea_meta or not mea_meta.get("version"):
            self.log_to_terminal(
                f"[DEBUG] Captured MEA History length: {len(history_str)} chars"
            )
            self.log_to_terminal(
                "[ERROR] Could not detect firmware version from MEA. "
                "Please ensure the file has been analyzed first."
            )
            return

        self.log_to_terminal(
            f"[INFO] Firmware detected - "
            f"Version: {mea_meta['version']} | "
            f"Family: {mea_meta.get('family','?')} | "
            f"SKU: {mea_meta.get('sku','?')} | "
            f"Chipset: {mea_meta.get('chipset','?')}"
        )

        # Step 2: Run full pipeline via Smart Repair Engine
        def _progress(pct):
            self.progress_signal.emit(int(pct))

        result = smart_repair_engine.run_smart_repair(
            bios_path        = str(self.current_bios_file),
            mea_meta         = mea_meta,
            log_cb           = self.log_to_terminal,
            progress_cb      = _progress,
            deliver_to_final = True,
            error_manager    = self.error_manager,
            manual_components= manual_components
        )

        # Step 3: Update GUI on success
        repaired_path = result.get("output_path")
        final_path    = result.get("final_path")

        if result["success"] and repaired_path and os.path.exists(repaired_path):
            self.log_to_terminal("-" * 30)
            self.log_to_terminal("[SUCCESS] SMART REPAIR COMPLETE!")
            if final_path:
                self.log_to_terminal(
                    f"[INFO] Saved to TESTING_AREA/FINAL BIOS: "
                    f"{os.path.basename(final_path)}"
                )
            self.log_to_terminal(
                f"[INFO] Backup in REPAIRED_BIOS: "
                f"{os.path.basename(repaired_path)}"
            )

            # Reload hex view with the fixed file
            self.current_bios_file = repaired_path
            self.log_to_terminal("[INFO] Reloading hex view with repaired data...")
            try:
                with open(repaired_path, "rb") as f:
                    self.hex_data_signal.emit(f.read())
            except Exception as e:
                self.log_to_terminal(f"[ERROR] Hex reload failed: {e}")

            # Set skip flag to prevent loop on auto-reload
            self.skip_auto_repair = True
            
            # Trigger auto-save countdown
            success_msg = (
                "<font color='#00ff41'><b>[INFO] [SUCCESS] Full CSME Clean Completed! ✅</b></font><br>"
                "<font color='#00ff41'><b>[INFO] STATUS: Manufacturing Mode: Disabled ✅</b></font>"
            )
            self.log_to_terminal(success_msg)
        else:
            if result.get("status") == "HALTED":
                halt_step = result.get("halt_step", "UNKNOWN")
                halt_msg = (
                    "<font color='#ff3131'><b>\u274c PIPELINE HALTED \u2014 Critical Error Detected</b></font><br>"
                    f"<font color='#ff3131'><b>[STEP] {halt_step}</b></font><br>"
                    "<font color='#ffaa00'><b>[INFO] No further repair steps were attempted. See popup for details.</b></font>"
                )
                self.log_to_terminal(halt_msg)
            else:
                fail_msg = (
                    "<font color='#ff3131'><b>[ERROR] Smart Repair Engine reported failure. \u26a0\ufe0f</b></font><br>"
                    "<font color='#ff3131'><b>[INFO] STATUS: Initialized Mode (Repair Incomplete)</b></font>"
                )
                self.log_to_terminal(fail_msg)
                self.log_to_terminal(
                    "[ERROR] Check terminal output and fit_errors_solutions.log."
                )


    def save_repair_to_history(self, meta, repair_set):
        """Saves successful repair data for future learning."""
        try:
            history_path = os.path.join(get_app_root(), "TESTING_AREA", "repair_history.json")
            record = {
                "timestamp": datetime.now().isoformat(),
                "version": meta.get("version"),
                "sku": meta.get("sku"),
                "repair_set": {k: os.path.basename(v) for k, v in repair_set.items()}
            }
            history = []
            if os.path.exists(history_path):
                with open(history_path, "r") as f: history = json.load(f)
            history.append(record)
            with open(history_path, "w") as f: json.dump(history, f, indent=4)
        except: pass

    def smart_me_fix_handler(self):
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QAction
        
        menu = QMenu(self)
        is_light = getattr(self, 'is_light_mode', False)
        if not is_light:
            menu.setStyleSheet("QMenu { background-color: #171a1d; color: #ffffff; border: 1px solid #3c444d; border-radius: 6px; padding: 4px; } QMenu::item { padding: 6px 20px; font-family: 'Segoe UI', sans-serif; } QMenu::item:selected { background-color: #3598a6; color: #ffffff; border-radius: 4px; }")
        else:
            menu.setStyleSheet("QMenu { background-color: #ffffff; color: #2563eb; border: 1px solid #2563eb; } QMenu::item:selected { background-color: #2563eb; color: #ffffff; }")

        auto_action = QAction("⚡ AUTO CLEAN", self)
        auto_action.triggered.connect(self.run_auto_me_clean)
        menu.addAction(auto_action)

        manual_action = QAction("⚙️ MANUAL CLEAN", self)
        manual_action.triggered.connect(self.run_manual_me_clean)
        menu.addAction(manual_action)

        menu.exec(self.btn_smart_me_fix.mapToGlobal(self.btn_smart_me_fix.rect().bottomLeft()))

    def run_auto_me_clean(self):
        self._execute_me_clean()

    def run_manual_me_clean(self):
        from me_clean_advanced import AdvancedMECleanDialog
        from mea_parser import parse_mea_output
        is_light = getattr(self, 'is_light_mode', False)
        
        # Determine required components based on MEA version
        required_components = ["ME"]
        if self.mea_history:
            mea_meta = parse_mea_output(self.mea_history)
            if mea_meta and "version" in mea_meta:
                v_parts = mea_meta["version"].split(".")
                major = int(v_parts[0]) if v_parts[0].isdigit() else 0
                if major >= 12:
                    required_components = ["ME", "PMC", "PCHC", "PHY"]
                    
        dialog = AdvancedMECleanDialog(self, is_dark_mode=not is_light, required_components=required_components)
        dialog.files_selected.connect(self._validate_and_execute_manual_me)
        dialog.exec()

    def _validate_and_execute_manual_me(self, manual_components: dict):
        from PySide6.QtWidgets import QMessageBox
        me_region_key = "me_csme" if "me_csme" in self.current_regions_map else "me_region" if "me_region" in self.current_regions_map else None
        
        manual_me_path = manual_components.get("ME")
        
        if not me_region_key or not self.current_bios_file or not manual_me_path:
            self.log_to_terminal("[WARNING] Could not locate ME region in current BIOS for validation, or ME file not provided.")
            self._execute_me_clean(manual_components=manual_components)
            return
            
        region = self.current_regions_map[me_region_key]
        
        try:
            with open(self.current_bios_file, "rb") as f:
                f.seek(region["offset"])
                old_me_data = f.read(region["size"])
                
            with open(manual_me_path, "rb") as f:
                new_me_data = f.read()
                
            old_size = len(old_me_data)
            new_size = len(new_me_data)
            
            old_header = old_me_data[:16].hex().upper()
            new_header = new_me_data[:16].hex().upper()
            
            old_footer = old_me_data[-16:].hex().upper()
            new_footer = new_me_data[-16:].hex().upper()
            
            warnings = []
            if old_size != new_size:
                warnings.append(f"Size mismatch: Old = {old_size} bytes, New = {new_size} bytes")
                
            if old_header != new_header:
                warnings.append(f"Header mismatch!\nOld: {old_header}\nNew: {new_header}")
                
            if old_footer != new_footer:
                warnings.append(f"Footer mismatch!\nOld: {old_footer}\nNew: {new_footer}")
                
            if warnings:
                msg = "Manual ME Validation Warnings:\n\n" + "\n\n".join(warnings) + "\n\nDo you want to proceed anyway?"
                reply = QMessageBox.warning(self, "ME Validation Warning", msg, QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.No:
                    self.log_to_terminal("[INFO] Manual ME Clean aborted by user due to validation mismatch.")
                    return
            else:
                self.log_to_terminal("[INFO] Manual ME file validation passed! (Size, Header, Footer match)")
                
        except Exception as e:
            self.log_to_terminal(f"[ERROR] Failed to validate manual ME file: {e}")
            
        self._execute_me_clean(manual_components=manual_components)

    def _execute_me_clean(self, manual_components=None):
        prefix = "MANUAL" if manual_components else "AUTO"
        self.log_to_terminal(f"[ACTION] Starting SMART ME FIX ({prefix}-FIT Pipeline)...")
        self.is_task_running = True
        self._handle_loading_state(True, f"Repairing ME Region ({prefix})...")
        self.progress_signal.emit(15)
        
        def _run_fix():
            try:
                self.progress_signal.emit(40)
                self.automated_repair_bios(manual_components=manual_components)
                self.progress_signal.emit(100)
            except Exception as e:
                self.log_to_terminal(f"[ERROR] Smart ME Fix Failed: {str(e)}")
            finally:
                QMetaObject.invokeMethod(self, "initiate_loader_stop", Qt.ConnectionType.QueuedConnection, Q_ARG(int, 2000))
                
        threading.Thread(target=_run_fix, daemon=True).start()

    def show_patches_menu(self):
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #171a1d; color: #ffffff; border: 1px solid #3c444d; border-radius: 6px; padding: 4px; } QMenu::item { padding: 6px 20px; font-family: 'Segoe UI', sans-serif; } QMenu::item:selected { background-color: #3598a6; color: #ffffff; border-radius: 4px; }")
        
        unlock_action = menu.addAction("🔓 UNLOCK DATA REGIONS")
        unlock_action.triggered.connect(self.unlock_bios)
        
        password_action = menu.addAction("🔑 REMOVE PASSWORD")
        password_action.triggered.connect(self.remove_password)
        
        # Position menu above or at the button
        menu.exec(self.btn_apply_patches.mapToGlobal(self.btn_apply_patches.rect().bottomLeft()))

    def save_and_fix_handler(self):
        self.log_to_terminal("[ACTION] SAVE && FIX triggered. Recalculating Checksums...")
        
        if not self.current_bios_file:
            return

        # Always default to the original file's directory
        base_dir = os.path.dirname(self.current_bios_file)

        # If a pending save name was pre-set (e.g. from RG Fix pipeline), use it
        if self.pending_save_name:
            suggested_path = os.path.join(base_dir, self.pending_save_name)
            self.pending_save_name = ""  # clear after use
        else:
            suggested_path = os.path.join(base_dir, os.path.basename(self.current_bios_file))

        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save Fixed BIOS", suggested_path, "BIOS Files (*.bin *.rom *.fd *.cap);;All Files (*)"
        )
        
        if not save_path:
            return

        self.last_directory = os.path.dirname(save_path)

        self._handle_loading_state(True, "Finalizing & Saving...")
        
        def _run_save():
            try:
                data = bytearray(self.hex_model.get_data())
                
                # AUTO FIX FV CHECKSUMS (The expert's suggestion)
                from compare_fixer import CompareFixer
                fix_count = CompareFixer.fix_fv_checksums(data, self.log_to_terminal)
                
                with open(save_path, "wb") as f:
                    f.write(data)
                
                if fix_count > 0:
                    self.log_to_terminal(f"[SUCCESS] Saved with {fix_count} FV Checksum corrections! ✅")
                else:
                    self.log_to_terminal(f"[SUCCESS] Saved successfully. No checksum errors found. ✅")
                    
                self.log_to_terminal(f"[INFO] File: {os.path.basename(save_path)}")
                
            except Exception as e:
                self.log_to_terminal(f"[ERROR] Failed to Save & Fix: {str(e)}")
            finally:
                QMetaObject.invokeMethod(self, "initiate_loader_stop", Qt.ConnectionType.QueuedConnection, Q_ARG(int, 2000))

        threading.Thread(target=_run_save, daemon=True).start()

    @Slot(str)
    def _open_rg_save_dialog(self, suggested_name):
        """Opens the Save dialog in the main thread with a pre-filled filename after RG Fix."""
        if not self.current_bios_file:
            return

        # Always use the original BIOS file's directory as the base directory
        base_dir = os.path.dirname(self.current_bios_file)
        suggested_path = os.path.join(base_dir, suggested_name)

        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save Fixed BIOS", suggested_path,
            "BIOS Files (*.bin *.rom *.fd *.cap);;All Files (*)"
        )
        if not save_path:
            self.log_to_terminal("[INFO] Save cancelled by user.")
            return

        self.last_directory = os.path.dirname(save_path)
        self._handle_loading_state(True, "Finalizing & Saving...")

        def _do_save():
            try:
                data = bytearray(self.hex_model.get_data())
                from compare_fixer import CompareFixer
                fix_count = CompareFixer.fix_fv_checksums(data, self.log_to_terminal)
                with open(save_path, "wb") as f:
                    f.write(data)
                if fix_count > 0:
                    self.log_to_terminal(f"[SUCCESS] Saved with {fix_count} FV Checksum corrections! ✅")
                else:
                    self.log_to_terminal(f"[SUCCESS] Saved successfully. ✅")
                self.log_to_terminal(f"[INFO] File: {os.path.basename(save_path)}")
            except Exception as e:
                self.log_to_terminal(f"[ERROR] Failed to save: {str(e)}")
            finally:
                QMetaObject.invokeMethod(self, "initiate_loader_stop", Qt.ConnectionType.QueuedConnection, Q_ARG(int, 2000))

        threading.Thread(target=_do_save, daemon=True).start()

    def unlock_bios(self):
        self.is_task_running = True
        self._handle_loading_state(True, "Unlocking Data Regions...")
        self.progress_signal.emit(25)
        
        def _run_unlock():
            try:
                self.log_to_terminal("[INFO] Unlock BIOS button clicked")
                if "descriptor" in self.current_regions_map:
                    region = self.current_regions_map["descriptor"]
                    self.log_to_terminal(f"[INFO] Descriptor region start: 0x{region['offset']:X}, size: {region['size']/1024:.0f} KB")
                    self.progress_signal.emit(70)
                    self.log_to_terminal("[INFO] Applying Unlock BIOS patch...")
                    # Simulating patching duration for now since patch logic is stubbed
                    import time
                    time.sleep(1.5)
                else:
                    self.log_to_terminal("[WARNING] Descriptor region not detected - cannot run Unlock BIOS")
            except Exception as e:
                self.log_to_terminal(f"[ERROR] Unlock failed: {str(e)}")
            finally:
                QMetaObject.invokeMethod(self, "initiate_loader_stop", Qt.ConnectionType.QueuedConnection, Q_ARG(int, 2000))
                
        threading.Thread(target=_run_unlock, daemon=True).start()



    def remove_password(self):
        self.is_task_running = True
        self._handle_loading_state(True, "Removing Passwords...")
        self.progress_signal.emit(25)
        
        def _run_pass_remove():
            try:
                self.log_to_terminal("[INFO] Remove Password button clicked")
                reg_key = "bios" if "bios" in self.current_regions_map else "bios_region"
                if reg_key in self.current_regions_map:
                    region = self.current_regions_map[reg_key]
                    mb_size = region['size'] / (1024 * 1024)
                    self.log_to_terminal(f"[INFO] BIOS region start: 0x{region['offset']:X}, size: {mb_size:.2f} MB")
                    self.progress_signal.emit(70)
                    self.log_to_terminal("[INFO] Applying Password Remove patch...")
                    # Simulation
                    import time
                    time.sleep(1.5)
                else:
                    self.log_to_terminal("[WARNING] BIOS region not detected - cannot run Password Remove")
            except Exception as e:
                self.log_to_terminal(f"[ERROR] Password removal failed: {str(e)}")
            finally:
                QMetaObject.invokeMethod(self, "initiate_loader_stop", Qt.ConnectionType.QueuedConnection, Q_ARG(int, 2000))
                
        threading.Thread(target=_run_pass_remove, daemon=True).start()

    def dmi_migrate_click_handler(self):
        self.log_to_terminal("[INFO] MIGRATE DMI button clicked")
        if not self.current_bios_file:
            self.log_to_terminal("[WARNING] No BIOS file loaded")
            return
            
        old_path, _ = QFileDialog.getOpenFileName(self, "Select Original BIO/Dump Backup", "", "Bin (*.bin);;All Files (*)")
        if not old_path:
            return
            
        keyword, ok = QInputDialog.getText(self, "DMI Keyword (Optional)", 
                                         "Enter a specific serial number or keyword to search.\nLeave empty to auto-search common UEFI headers:")
        if not ok:
            return
            
        self.is_task_running = True
        self._handle_loading_state(True, "Migrating NVRAM...")
        self.progress_signal.emit(30)
            
        def _run_migration():
            try:
                output_path = DMIMigrator.migrate(old_path, self.current_bios_file, keyword, self.log_to_terminal)
                if output_path:
                    self.progress_signal.emit(100)
                    self.log_to_terminal("[SUCCESS] Reloading Hex View with new DMI data...")
                    self.current_bios_file = output_path
                    with open(output_path, "rb") as f:
                        data = f.read()
                        self.hex_data_signal.emit(data)
                else:
                    self.log_to_terminal("[ERROR] DMI Migration failed or aborted.")
            except Exception as e:
                self.log_to_terminal(f"[ERROR] Exception during migration: {str(e)}")
            finally:
                QMetaObject.invokeMethod(self, "initiate_loader_stop", Qt.ConnectionType.QueuedConnection, Q_ARG(int, 2000))
                
        threading.Thread(target=_run_migration, daemon=True).start()
        
    def ec_finder_handler(self):
        """Handler for ECFinder options using a drop-down menu - 2 options only"""
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QCursor
        import subprocess
        
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1a1a1a;
                color: #00ff41;
                border: 1px solid #00ff41;
                font-size: 13px;
            }
            QMenu::item {
                padding: 10px 24px;
                font-weight: bold;
            }
            QMenu::item:selected {
                background-color: #00ff41;
                color: #000;
            }
        """)
        
        action_micro = menu.addAction("1 micro EC Finder")
        action_smart = menu.addAction("2 EC Finder")
        
        action = menu.exec(QCursor.pos())
        
        if action == action_micro:
            # Launch bundled ECFinder.exe from external/ECFinder/
            self.log_to_terminal("[ACTION] Launching 1 micro EC Finder...")
            tool_path = get_ecfinder_path(self, prompt_if_missing=True)
            if tool_path and os.path.exists(tool_path):
                tool_dir = os.path.dirname(tool_path)
                try:
                    cmd = [tool_path]
                    if hasattr(self, 'current_bios_file') and self.current_bios_file and os.path.exists(self.current_bios_file):
                        cmd.append(self.current_bios_file)
                    subprocess.Popen(cmd, cwd=tool_dir, creationflags=subprocess.CREATE_NEW_CONSOLE)
                    self.log_to_terminal("[SUCCESS] 1 micro EC Finder opened successfully. ✅")
                except Exception as e:
                    self.log_to_terminal(f"[ERROR] Failed to launch 1 micro EC Finder: {e}")
            else:
                self.log_to_terminal("[WARNING] 1 micro EC Finder: ECFinder.exe not found. Please place it in external/ECFinder/.")
        
        elif action == action_smart:
            # Open Smart EC Finder carver dialog
            self.log_to_terminal("[ACTION] Opening 2 EC Finder (Smart Carver)...")
            dlg = SmartECFinderDialog(self)
            dlg.exec()

    def dell_pfs_extract_handler(self):
        """Opens glossy drop-zone dialog, then runs Dell PFS extraction."""
        from extractor_dialog import ExtractorDropDialog
        from PySide6.QtWidgets import QDialog

        script_path = os.path.join(str(get_app_root()), "external", "Dell_PFS", "Dell_PFS_Extract.py")
        if not os.path.exists(script_path):
            self.log_to_terminal("[ERROR] Dell PFS Extractor script not found in external/Dell_PFS/")
            return

        dialog = ExtractorDropDialog(
            title="DELL PFS EXTRACTOR",
            subtitle="Drop a Dell BIOS executable (.exe) to extract its firmware packages",
            accepted_exts=[".exe"],
            parent=self
        )

        # Pre-fill if a .exe BIOS file is already loaded
        if hasattr(self, 'current_bios_file') and self.current_bios_file and \
                self.current_bios_file.lower().endswith(".exe"):
            dialog._on_file_received(self.current_bios_file)

        if dialog.exec() != QDialog.Accepted or not dialog.selected_file:
            self.log_to_terminal("[INFO] Dell PFS Extraction cancelled.")
            return

        target_file = dialog.selected_file
        self.log_to_terminal(f"[ACTION] Dell PFS Extracting: {os.path.basename(target_file)}")
        self.is_task_running = True
        self._handle_loading_state(True, "Extracting Dell PFS...")

        def _run_dell_extract():
            import subprocess
            try:
                result = subprocess.run(
                    [sys.executable, script_path, target_file],
                    capture_output=True, text=True
                )
                for line in result.stdout.splitlines():
                    if line.strip():
                        self.log_to_terminal(f"  > {line.strip()}")
                for line in result.stderr.splitlines():
                    if line.strip():
                        self.log_to_terminal(f"  [ERR] {line.strip()}")
                if result.returncode == 0:
                    self.log_to_terminal("[SUCCESS] Dell PFS Extraction completed.")
                else:
                    self.log_to_terminal(f"[ERROR] Dell PFS failed (code {result.returncode}).")
            except Exception as e:
                self.log_to_terminal(f"[ERROR] Dell PFS extraction error: {e}")
            finally:
                QMetaObject.invokeMethod(self, "initiate_loader_stop",
                    Qt.ConnectionType.QueuedConnection, Q_ARG(int, 1000))

        threading.Thread(target=_run_dell_extract, daemon=True).start()



    def universal_extract_handler(self):
        """Opens glossy drop-zone dialog, then launches Universal Extractor with selected file."""
        from extractor_dialog import ExtractorDropDialog
        from PySide6.QtWidgets import QDialog
        import subprocess

        ue_path = os.path.join(str(get_app_root()), "external", "UniExtract", "UniExtract.exe")
        if not os.path.exists(ue_path):
            self.log_to_terminal(f"[ERROR] Universal Extractor not found at: {ue_path}")
            return

        dialog = ExtractorDropDialog(
            title="UNIVERSAL EXTRACTOR",
            subtitle="Drop any BIOS installer or executable to extract its contents",
            accepted_exts=[".exe", ".bin", ".rom", ".zip", ".7z", ".msi"],
            parent=self
        )

        # Pre-fill if a file is already loaded
        if hasattr(self, 'current_bios_file') and self.current_bios_file:
            dialog._on_file_received(self.current_bios_file)

        if dialog.exec() != QDialog.Accepted or not dialog.selected_file:
            self.log_to_terminal("[INFO] Universal Extract cancelled.")
            return

        target_file = dialog.selected_file
        self.log_to_terminal(f"[ACTION] Universal Extractor launching for: {os.path.basename(target_file)}")
        try:
            subprocess.Popen([ue_path, target_file])
            self.log_to_terminal("[SUCCESS] Universal Extractor opened.")
        except Exception as e:
            self.log_to_terminal(f"[ERROR] Failed to launch Universal Extractor: {e}")


    def merge_handler(self):
        """Opens the Merge Dialog to combine two firmware/binary files."""
        from merge_dialog import MergeDialog
        from PySide6.QtWidgets import QDialog

        dialog = MergeDialog(parent=self)
        dialog.exec()

    def bios_rg_fix_handler(self):
        """Show options for BIOS RG Fix."""
        from PySide6.QtGui import QAction
        from PySide6.QtWidgets import QMenu
        
        self.log_to_terminal("[INFO] BIOS RG FIX button clicked")
        if not self.current_bios_file:
            self.log_to_terminal("[WARNING] No BIOS file loaded")
            return
            
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background-color: #0f172a; color: #ffffff; border: 1px solid #38bdf8; }"
            "QMenu::item { padding: 8px 24px; font-weight: bold; }"
            "QMenu::item:selected { background-color: #0369a1; }"
        )

        ready_action = QAction("📂 BIOS RG Ready", self)
        ready_action.triggered.connect(self.run_bios_rg_ready)
        menu.addAction(ready_action)

        exe_action = QAction("📦 BIOS RG .EXE", self)
        exe_action.triggered.connect(self.run_bios_rg_exe)
        menu.addAction(exe_action)

        menu.exec(self.btn_dmi_migrate.mapToGlobal(self.btn_dmi_migrate.rect().bottomLeft()))

    def run_bios_rg_ready(self):
        """Original BIOS RG Fix logic using a pre-extracted file."""
        donor_path, _ = QFileDialog.getOpenFileName(self, "Select Clean BIOS/Update File", self.last_directory, "Bin (*.bin *.rom *.fd *.cap *.exe *.pfs);;All Files (*)")
        if not donor_path:
            return
            
        self.last_directory = os.path.dirname(donor_path)
        
        self.is_task_running = True
        
        # --- DMI Confirmation Dialog ---
        reply = QMessageBox.question(
            self, 'DMI Migration', 
            "Do you want to migrate DMI data (Serial Number, Windows Key, etc.) from the original file?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes
        )
        migrate_dmi = (reply == QMessageBox.StandardButton.Yes)
        
        self._handle_loading_state(True, "Cleaning BIOS Region...")
        self.progress_signal.emit(20)
            
        def _run_fix():
            try:
                self.progress_signal.emit(40)
                
                # --- HP SOFTPAQ AUTO-DETECTION ---
                is_hp_exe = donor_path.lower().endswith(".exe")
                
                if is_hp_exe:
                    self.log_to_terminal("[INFO] HP SoftPaq detected. File Match Complete ✅")
                    self.log_to_terminal("[INFO] Using Adaptive HP Repair logic...")
                    repairer = HPBIOSRepairer(self.current_bios_file, donor_path, migrate_dmi=migrate_dmi)
                    # Monkey-patch log methods
                    repairer.log_info = lambda msg: self.log_to_terminal(f"[INFO] {msg}")
                    repairer.log_error = lambda msg: self.log_to_terminal(f"[ERROR] {msg}")
                    
                    # Output path
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    current_bios_str = str(self.current_bios_file or "unknown.bin")
                    out_name = f"HP_CLEAN_{timestamp}_{os.path.basename(current_bios_str)}"
                    out_dir = os.path.join(str(get_app_root()), "REPAIRED_BIOS")
                    os.makedirs(out_dir, exist_ok=True)
                    out_path = os.path.join(out_dir, out_name)
                    
                    success = repairer.perform_repair(out_path)
                    output_path = out_path if success else None
                    
                    if output_path:
                        self.progress_signal.emit(100)
                        self.log_to_terminal("[SUCCESS] HP SoftPaq BIOS Clean Complete ✅")
                        self.log_to_terminal("[INFO] Reloading Hex View with Clean BIOS Region...")
                        self.current_bios_file = output_path
                        with open(output_path, "rb") as f:
                            data = f.read()
                            self.hex_data_signal.emit(data)
                        
                        orig_base = os.path.splitext(os.path.basename(self.current_bios_file))[0]
                        suggested_name = f"{orig_base}_RG_cline.bin"
                        self.trigger_rg_save_dialog.emit(suggested_name)
                    else:
                        self.log_to_terminal("[ERROR] HP SoftPaq Repair failed.")
                else:
                    # USE V1 SMART ENGINE FOR ALL NON-HP EXEs (Standard BIOS RG Ready flow)
                    from rg_engine.validator import validate_and_trim
                    from rg_engine.replacer import replace_bios_region
                    
                    if not hasattr(self, 'current_regions_map') or "bios" not in self.current_regions_map:
                        if "bios_region" in self.current_regions_map:
                            region_info = self.current_regions_map["bios_region"]
                        else:
                            self.log_to_terminal("[ERROR] BIOS Region not found in current map.")
                            QMetaObject.invokeMethod(self, "initiate_loader_stop", Qt.ConnectionType.QueuedConnection, Q_ARG(int, 2000))
                            return
                    else:
                        region_info = self.current_regions_map["bios"]
                        
                    target_offset = region_info["offset"]
                    target_size = region_info["size"]
                    
                    self.log_to_terminal(f"[INFO] Target BIOS Region Size: {target_size} bytes")
                    
                    # Read Old BIOS Region from currently loaded file
                    old_bios_region = None
                    try:
                        with open(self.current_bios_file, "rb") as bf:
                            bf.seek(target_offset)
                            old_bios_region = bf.read(target_size)
                    except Exception as rf_e:
                        self.log_to_terminal(f"[WARNING] Could not read old BIOS region: {rf_e}")

                    self.progress_signal.emit(50)
                    valid_data, head_rem, foot_rem = validate_and_trim(
                        donor_path, 
                        target_size, 
                        old_bios_region=old_bios_region,
                        log_callback=self.log_to_terminal
                    )
                    
                    if not valid_data:
                        self.log_to_terminal("[ERROR] Validation Failed: File rejected because Header/Footer did not match loaded BIOS region.")
                        QMetaObject.invokeMethod(self, "initiate_loader_stop", Qt.ConnectionType.QueuedConnection, Q_ARG(int, 2000))
                        return
                        
                    self.progress_signal.emit(70)
                    
                    migrated_dmi_data = None
                    if migrate_dmi:
                        try:
                            from dmi_extractor import DMIExtractor
                            self.log_to_terminal("[INFO] Preserving DMI/NVRAM data before BIOS Region replacement...")
                            migrated_dmi_data = DMIExtractor.extract_info(
                                self.current_bios_file,
                                getattr(self, 'current_regions_map', None),
                                self.log_to_terminal
                            )
                        except Exception as dmi_e:
                            self.log_to_terminal(f"[WARNING] Could not extract DMI for migration: {dmi_e}")

                    report = replace_bios_region(self.current_bios_file, valid_data, target_offset, target_size, log_callback=self.log_to_terminal)

                    if migrate_dmi and migrated_dmi_data and migrated_dmi_data.get("Details"):
                        try:
                            self.log_to_terminal("[ACTION] Migrating preserved DMI/NVRAM into clean BIOS Region...")
                            with open(self.current_bios_file, "rb") as rf:
                                new_bin_data = bytearray(rf.read())
                            
                            from dmi_injector import DMIInjector
                            inj_fields = {}
                            for k, v in migrated_dmi_data.get("Details", {}).items():
                                inj_fields[k] = {
                                    "value": v,
                                    "offset": migrated_dmi_data.get("Offsets", {}).get(k, ""),
                                    "end_offset": migrated_dmi_data.get("EndOffsets", {}).get(k, ""),
                                    "length": migrated_dmi_data.get("Lengths", {}).get(k, 0),
                                    "encoding": migrated_dmi_data.get("Encodings", {}).get(k, "UTF-16LE"),
                                    "region": migrated_dmi_data.get("Regions", {}).get(k, "BIOS"),
                                    "relative_offset": migrated_dmi_data.get("RelativeOffsets", {}).get(k, "")
                                }
                            raw_blocks = migrated_dmi_data.get("RawBlocks", {})
                            c = DMIInjector.inject_fields(
                                new_bin_data, inj_fields, 
                                regions_map=getattr(self, 'current_regions_map', None),
                                raw_blocks=raw_blocks,
                                log_cb=self.log_to_terminal
                            )
                            with open(self.current_bios_file, "wb") as wf:
                                wf.write(new_bin_data)
                                wf.flush()
                                os.fsync(wf.fileno())
                            self.log_to_terminal(f"[SUCCESS] DMI Migration Complete: {c} field(s) preserved in clean BIOS! ✅")
                        except Exception as mig_err:
                            self.log_to_terminal(f"[ERROR] DMI auto-migration failed: {mig_err}")
                    
                    self.progress_signal.emit(100)
                    self.log_to_terminal("\n--- BIOS RG FIX REPORT ---")
                    self.log_to_terminal(f"Original Region Size: {target_size} bytes")
                    self.log_to_terminal(f"Header Removed:       {head_rem} bytes")
                    self.log_to_terminal(f"Footer Removed:       {foot_rem} bytes")
                    self.log_to_terminal(f"Backup File:          {os.path.basename(report['backup_path'])}")
                    self.log_to_terminal("Status:               SUCCESS")
                    self.log_to_terminal("--------------------------\n")
                    
                    self.log_to_terminal("[INFO] Reloading Hex View with Clean BIOS Region...")
                    with open(self.current_bios_file, "rb") as f:
                        data = f.read()
                        self.hex_data_signal.emit(data)
                        
                    orig_base = os.path.splitext(os.path.basename(self.current_bios_file))[0]
                    suggested_name = f"{orig_base}_RG_cline.bin"
                    self.trigger_rg_save_dialog.emit(suggested_name)
                    
            except Exception as e:
                self.log_to_terminal(f"[ERROR] Exception during BIOS RG FIX: {str(e)}")
            finally:
                QMetaObject.invokeMethod(self, "initiate_loader_stop", Qt.ConnectionType.QueuedConnection, Q_ARG(int, 2000))
                
        threading.Thread(target=_run_fix, daemon=True).start()

    def run_bios_rg_exe(self):
        """New V1 Pipeline for extracting and replacing BIOS region from vendor EXEs."""
        from extractor_dialog import ExtractorDropDialog
        from rg_engine.extractor import extract_bios_package, list_extracted_files
        from rg_engine.ui import ExtractedFileListDialog
        from rg_engine.validator import validate_and_trim
        from rg_engine.replacer import replace_bios_region
        import time

        dialog = ExtractorDropDialog(
            title="BIOS RG .EXE EXTRACTOR",
            subtitle="Drop an Official BIOS Update Package (.exe)",
            accepted_exts=[".exe"],
            parent=self
        )

        if dialog.exec() != QDialog.Accepted or not dialog.selected_file:
            self.log_to_terminal("[INFO] BIOS RG .EXE cancelled.")
            return

        exe_path = dialog.selected_file
        self.is_task_running = True
        self._handle_loading_state(True, "Extracting Package...")
        self.progress_signal.emit(10)
        self.log_to_terminal(f"[ACTION] Extracting Official Package: {os.path.basename(exe_path)}")

        def _run_pipeline():
            try:
                # Step 1: Extract
                dest_dir = extract_bios_package(exe_path, log_callback=self.log_to_terminal)
                self.progress_signal.emit(30)
                
                self.log_to_terminal("Reading Extracted Files...")
                extracted_files = list_extracted_files(dest_dir, log_callback=self.log_to_terminal)
                
                if not extracted_files:
                    self.log_to_terminal("[ERROR] No files were extracted. Unsupported package.")
                    return
                
                self.progress_signal.emit(40)
                self.log_to_terminal("Waiting For User Selection...")
                
                # Use a proper Signal to send the file list safely to the main thread.
                self.rg_exe_files_ready.emit(extracted_files)

            except Exception as e:
                self.log_to_terminal(f"[ERROR] Exception during BIOS RG .EXE extraction: {str(e)}")
                QMetaObject.invokeMethod(self, "initiate_loader_stop", Qt.ConnectionType.QueuedConnection, Q_ARG(int, 2000))

        threading.Thread(target=_run_pipeline, daemon=True).start()

    @Slot(object)
    def _show_rg_exe_selection_dialog(self, extracted_files):
        from rg_engine.ui import ExtractedFileListDialog
        
        dialog = ExtractedFileListDialog(extracted_files, parent=self)
        if dialog.exec() != QDialog.Accepted or not dialog.selected_file:
            self.log_to_terminal("[INFO] User cancelled file selection.")
            self.initiate_loader_stop(0)
            return
            
        selected_candidate = dialog.selected_file
        self.log_to_terminal(f"[INFO] User Selected: {os.path.basename(selected_candidate)}")
        self._handle_loading_state(True, "Validating Region...")
        
        # Determine target size
        if not hasattr(self, 'current_regions_map') or "bios" not in self.current_regions_map:
            # Fallback to older nomenclature or error
            if "bios_region" in self.current_regions_map:
                region_info = self.current_regions_map["bios_region"]
            else:
                self.log_to_terminal("[ERROR] BIOS Region not found in current map.")
                self.initiate_loader_stop(0)
                return
        else:
            region_info = self.current_regions_map["bios"]
            
        target_offset = region_info["offset"]
        target_size = region_info["size"]
        
        # Read Old BIOS Region from currently loaded file
        old_bios_region = None
        try:
            with open(self.current_bios_file, "rb") as bf:
                bf.seek(target_offset)
                old_bios_region = bf.read(target_size)
        except Exception as rf_e:
            self.log_to_terminal(f"[WARNING] Could not read old BIOS region: {rf_e}")

        def _run_validation_and_replace():
            from rg_engine.validator import validate_and_trim
            from rg_engine.replacer import replace_bios_region
            import time
            
            try:
                # Step 2: Validate and Trim
                self.progress_signal.emit(50)
                valid_data, head_rem, foot_rem = validate_and_trim(
                    selected_candidate, 
                    target_size, 
                    old_bios_region=old_bios_region,
                    log_callback=self.log_to_terminal
                )
                
                if not valid_data:
                    self.log_to_terminal("[ERROR] Validation Failed: Selected candidate rejected (Header/Footer mismatch). Operation Stopped.")
                    return
                
                self.progress_signal.emit(70)
                
                # Step 3: Replace
                report = replace_bios_region(self.current_bios_file, valid_data, target_offset, target_size, log_callback=self.log_to_terminal)
                
                self.progress_signal.emit(100)
                
                # Report
                self.log_to_terminal("\n--- BIOS RG FIX REPORT ---")
                self.log_to_terminal(f"Original Region Size: {target_size} bytes")
                self.log_to_terminal(f"Header Removed:       {head_rem} bytes")
                self.log_to_terminal(f"Footer Removed:       {foot_rem} bytes")
                self.log_to_terminal(f"Backup File:          {os.path.basename(report['backup_path'])}")
                self.log_to_terminal("Status:               SUCCESS")
                self.log_to_terminal("--------------------------\n")
                
                # Reload Hex View
                with open(self.current_bios_file, "rb") as f:
                    data = f.read()
                    self.hex_data_signal.emit(data)
                
                # Build suggested save name: {original_name}_RG_cline.bin
                orig_base = os.path.splitext(os.path.basename(self.current_bios_file))[0]
                suggested_name = f"{orig_base}_RG_cline.bin"
                
                # Emit signal to open Save dialog safely in main thread
                self.trigger_rg_save_dialog.emit(suggested_name)

            except Exception as e:
                self.log_to_terminal(f"[ERROR] Exception during validation/replace: {str(e)}")
            finally:
                QMetaObject.invokeMethod(self, "initiate_loader_stop", Qt.ConnectionType.QueuedConnection, Q_ARG(int, 2000))
                
        threading.Thread(target=_run_validation_and_replace, daemon=True).start()

    def open_password_remove_dialog(self):
        """Open the PasswordRemoverDialog for automated multi-brand password removal."""
        current_file = getattr(self, 'current_bios_file', None)
        if current_file and os.path.exists(current_file):
            current_file = os.path.abspath(current_file)
        else:
            current_file = None

        brand = "UNKNOWN"
        if hasattr(self, 'cached_dmi_info') and self.cached_dmi_info:
            brand = self.cached_dmi_info.get("Brand", "UNKNOWN")
        if brand in ("UNKNOWN", "N/A", "") and hasattr(self, 'dmi_lbl_brand'):
            brand_text = self.dmi_lbl_brand.text().strip()
            if brand_text and brand_text not in ("N/A", "Unknown", "Detecting...", ""):
                brand = brand_text.split()[0].upper()

        dialog = PasswordRemoverDialog(initial_file=current_file, brand=brand, parent=self)
        dialog.exec()

    def extract_dmi_handler(self):
        self.log_to_terminal("[ACTION] Extracting DMI Information...")
        if not self.current_bios_file:
            self.log_to_terminal("[WARNING] No BIOS file loaded")
            return

        self.is_task_running = True
        self._handle_loading_state(True, "Scanning DMI Metadata...")
        self.progress_signal.emit(30)

        def _run_extraction():
            try:
                info = DMIExtractor.extract_info(self.current_bios_file, self.current_regions_map, self.log_to_terminal)
                self.progress_signal.emit(70)
                
                if info and isinstance(info, dict):
                    self.cached_dmi_info = info
                    brand = info.get("Brand", "Unknown")
                    self.log_to_terminal(f"[SUCCESS] Detected Brand: <font color='#ffff00'>{brand}</font>")
                    self.log_to_terminal("[INFO] DMI Information Extracted:")
                    
                    details = info.get("Details", {})
                    offsets = info.get("Offsets", {})
                    reg_map = info.get("Regions", {})
                    
                    # Emit signal to update DMI Box safely from background thread
                    if hasattr(self, 'dmi_lbl_brand'):
                        model_str = details.get("System Model", details.get("Product Name", details.get("Model", "N/A")))
                        plat_str  = details.get("Platform", "N/A")
                        mac_str   = details.get("MAC Address", "N/A")
                        ser_str   = details.get("Serial Number", details.get("System Serial Number", details.get("Service Tag", details.get("SNID", "N/A"))))
                        self.dmi_update_signal.emit(brand, model_str, plat_str, mac_str, ser_str)


                    import time
                    all_occurrences = info.get("AllOccurrences", {})
                    encodings = info.get("Encodings", {})

                    if isinstance(details, dict) and isinstance(offsets, dict) and isinstance(reg_map, dict):
                        for k, v in details.items():
                            off_str = offsets.get(k, "N/A")
                            reg_name = reg_map.get(k, "UNKNOWN")
                            enc_str = encodings.get(k, "")
                            enc_label = f" | {enc_str}" if enc_str else ""

                            # Clickable hex link for primary offset
                            if str(off_str).startswith("0x"):
                                off_link = f"<a href='hexjump:///{off_str}' style='color:#00f3ff;text-decoration:underline;'><b>{off_str}</b></a>"
                            else:
                                off_link = off_str

                            # Primary main field display
                            self.log_to_terminal(f"  - <font color='#ffff00'><b>{k}: {v}</b></font>")
                            self.log_to_terminal(f"    &nbsp;&nbsp;[Location: {reg_name} | Offset: {off_link}{enc_label}] <font color='#00ff41'><b>(Primary)</b></font>")

                            # Show all additional detected locations (mirrors, descriptors, board IDs)
                            field_occs = all_occurrences.get(k, [])
                            for occ in field_occs:
                                occ_off = occ.get("offset", "")
                                if occ_off == off_str:
                                    continue
                                occ_val = occ.get("value", "")
                                occ_reg = occ.get("location", "UNKNOWN")
                                occ_enc = occ.get("encoding", "")
                                occ_type = occ.get("type", "secondary")

                                if str(occ_off).startswith("0x"):
                                    occ_link = f"<a href='hexjump:///{occ_off}' style='color:#00f3ff;text-decoration:underline;'><b>{occ_off}</b></a>"
                                else:
                                    occ_link = occ_off

                                occ_enc_label = f" | {occ_enc}" if occ_enc else ""

                                if occ_type == "board":
                                    self.log_to_terminal(
                                        f"    &nbsp;&nbsp;↳ <font color='#a0a0a0'>Board/SKU:</font> <b>{occ_val}</b> "
                                        f"[Location: {occ_reg} | Offset: {occ_link}{occ_enc_label}]"
                                    )
                                else:
                                    self.log_to_terminal(
                                        f"    &nbsp;&nbsp;↳ <font color='#00e5ff'>Mirror Location:</font> <b>{occ_val}</b> "
                                        f"[Location: {occ_reg} | Offset: {occ_link}{occ_enc_label}]"
                                    )

                            if "ME" in reg_name or "CSME" in reg_name:
                                self.log_to_terminal(f"    <font color='#ff3131'><b>⚠️ WARNING: {k} is stored in ME Region. BIOS Clean will NOT remove this! Use SMART ME FIX.</b></font>")
                            time.sleep(0.01) # Small delay to keep UI snappy and animation smooth
                    
                    # Store in FINAL folder as requested
                    output_dir = os.path.join(str(get_app_root()), "TESTING_AREA", "FINAL")
                    os.makedirs(output_dir, exist_ok=True)
                    
                    import json
                    output_file = os.path.join(output_dir, "dmi_info.json")
                    with open(output_file, 'w') as f:
                        json.dump(info, f, indent=4)
                    self.log_to_terminal(f"[INFO] Data and Offsets stored in: {output_file}")
                else:
                    self.log_to_terminal("[WARNING] No DMI information could be automatically identified.")
                
                self.progress_signal.emit(100)
            except Exception as e:
                self.log_to_terminal(f"[ERROR] DMI Extraction failed: {str(e)}")
            finally:
                QMetaObject.invokeMethod(self, "initiate_loader_stop", Qt.ConnectionType.QueuedConnection, Q_ARG(int, 1500))

        threading.Thread(target=_run_extraction, daemon=True).start()

    def save_dmi_handler(self):
        """Saves current DMI fields, offsets, and hardware signature into a reusable mapping file."""
        if not self.current_bios_file or not os.path.exists(self.current_bios_file):
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "No BIOS File", "Please load a BIOS file first!")
            return

        # If DMI is not cached yet, extract now
        if not self.cached_dmi_info or not self.cached_dmi_info.get("Details"):
            self.log_to_terminal("[ACTION] Extracting DMI Information for saving...")
            try:
                from dmi_extractor import DMIExtractor
                self.cached_dmi_info = DMIExtractor.extract_info(
                    self.current_bios_file, 
                    getattr(self, 'current_regions_map', None), 
                    self.log_to_terminal
                )
            except Exception as e:
                self.log_to_terminal(f"[ERROR] Extraction failed: {e}")

        if not self.cached_dmi_info or not self.cached_dmi_info.get("Details"):
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "DMI Empty", "No DMI fields could be extracted from the current BIOS file.")
            return

        details = self.cached_dmi_info.get("Details", {})
        offsets = self.cached_dmi_info.get("Offsets", {})
        end_offsets = self.cached_dmi_info.get("EndOffsets", {})
        lengths = self.cached_dmi_info.get("Lengths", {})
        encodings = self.cached_dmi_info.get("Encodings", {})
        rel_offsets = self.cached_dmi_info.get("RelativeOffsets", {})
        reg_map = self.cached_dmi_info.get("Regions", {})
        brand   = self.cached_dmi_info.get("Brand", "Unknown")

        try:
            file_size = os.path.getsize(self.current_bios_file)
            with open(self.current_bios_file, "rb") as bf:
                head_hex = bf.read(64).hex()
                bf.seek(max(0, file_size - 64))
                tail_hex = bf.read(64).hex()
        except Exception:
            file_size = 0
            head_hex = ""
            tail_hex = ""

        model_str = details.get("System Model", details.get("Product Name", details.get("Model", "")))
        serial_str = details.get("Serial Number", details.get("System Serial Number", details.get("Service Tag", "")))

        def _is_real(s):
            return bool(s and str(s).strip() not in ("", "N/A", "Unknown", "None", "Detecting...", "?"))

        has_real_model = _is_real(model_str)
        has_real_serial = _is_real(serial_str)

        # Require Model OR Serial (or both). Brand alone is NOT enough!
        if not has_real_model and not has_real_serial:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "No DMI Information",
                "Saving is disabled because no System Model or Serial Number was found in this file.\n\n"
                "Brand name alone cannot be saved. The file must have at least a Model Number or Serial Number."
            )
            return

        dmi_profile = {
            "format": "R1_BIOS_DMI_MAP",
            "version": "1.1",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source_file": os.path.basename(self.current_bios_file),
            "signature": {
                "brand": brand,
                "model": model_str,
                "serial": serial_str,
                "file_size": file_size,
                "head_sig": head_hex,
                "tail_sig": tail_hex
            },
            "fields": {},
            "all_occurrences": (self.cached_dmi_info.get("AllOccurrences", {}) if self.cached_dmi_info else {}),
            "raw_blocks": (self.cached_dmi_info.get("RawBlocks", {}) if self.cached_dmi_info else {})
        }

        for k, v in details.items():
            off_str = offsets.get(k, "N/A")
            end_str = end_offsets.get(k, "")
            len_val = lengths.get(k, 0)
            enc_str = encodings.get(k, "UTF-16LE")
            reg_name = reg_map.get(k, "UNKNOWN")
            rel_str = rel_offsets.get(k, "")

            # compute relative offset if not already computed
            if not rel_str and str(off_str).startswith("0x") and hasattr(self, 'current_regions_map') and self.current_regions_map:
                try:
                    off_i = int(off_str, 16)
                    for r_n, r_i in self.current_regions_map.items():
                        if r_i['offset'] <= off_i < r_i['offset'] + r_i['size']:
                            reg_name = r_n.upper()
                            rel_str = f"0x{off_i - r_i['offset']:X}"
                            break
                except Exception:
                    pass

            dmi_profile["fields"][k] = {
                "value": str(v),
                "offset": str(off_str),
                "end_offset": str(end_str),
                "length": len_val,
                "encoding": str(enc_str),
                "region": str(reg_name),
                "relative_offset": str(rel_str)
            }

        base_name = os.path.splitext(os.path.basename(self.current_bios_file))[0]
        default_save = os.path.join(self.last_directory, f"{base_name}_DMI_MAP.dmi")

        from PySide6.QtWidgets import QFileDialog, QMessageBox
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save DMI Mapping File",
            default_save,
            "DMI Profile (*.dmi *.json);;All Files (*)"
        )

        if not save_path:
            return

        self.last_directory = os.path.dirname(save_path)
        try:
            import json
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(dmi_profile, f, indent=4)
            self.log_to_terminal(
                f"[SUCCESS] DMI Mapping File saved: <font color='#00ff41'><b>{os.path.basename(save_path)}</b></font> "
                f"({len(details)} fields recorded) ✅"
            )
            QMessageBox.information(
                self,
                "DMI Saved",
                f"DMI mapping successfully saved to:\n{save_path}\n\n"
                f"Brand: {brand}\n"
                f"Model: {model_str}\n"
                f"Fields: {len(details)}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save DMI mapping file:\n{e}")

    def load_dmi_handler(self):
        """Loads a DMI mapping file, verifies Safety Signature against open BIOS, and stages injection."""
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load DMI Mapping File",
            self.last_directory,
            "DMI Profile (*.dmi *.json);;All Files (*)"
        )
        if not file_path:
            return

        self.last_directory = os.path.dirname(file_path)

        import json
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                profile = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Read Error", f"Invalid DMI mapping file:\n{e}")
            return

        if not isinstance(profile, dict) or "fields" not in profile:
            QMessageBox.critical(self, "Format Error", "The selected file is not a valid R1 DMI mapping profile.")
            return

        # Check if user has target BIOS loaded in the tool
        if not self.current_bios_file or not os.path.exists(self.current_bios_file):
            QMessageBox.warning(
                self,
                "No Target BIOS Loaded",
                "Please open or drag-and-drop the Target/Clean BIOS file into the tool first!\n\n"
                "The tool must verify the Safety Signature against the target firmware before enabling injection."
            )
            return

        # Safety Signature Verification
        sig = profile.get("signature", {})
        prof_brand = sig.get("brand", "Unknown")
        prof_model = sig.get("model", "Unknown")
        prof_size  = sig.get("file_size", 0)

        target_size = os.path.getsize(self.current_bios_file)
        
        # Detect brand of target BIOS
        target_brand = "Unknown"
        try:
            with open(self.current_bios_file, "rb") as tf:
                t_content = tf.read(min(target_size, 0x200000))
            from dmi_extractor import DMIExtractor
            target_brand = DMIExtractor.detect_brand(t_content, file_path=self.current_bios_file)
        except Exception:
            pass

        mismatch_reasons = []
        if prof_size and target_size != prof_size:
            mismatch_reasons.append(
                f"• Size Mismatch: Profile expects {prof_size:,} bytes ({prof_size/(1024*1024):.1f} MB), "
                f"but target BIOS is {target_size:,} bytes ({target_size/(1024*1024):.1f} MB)"
            )

        if prof_brand != "Unknown" and target_brand != "Unknown" and prof_brand.lower() != target_brand.lower():
            mismatch_reasons.append(
                f"• Brand Mismatch: Profile is from '{prof_brand}', but target BIOS is detected as '{target_brand}'"
            )

        if mismatch_reasons:
            err_msg = (
                "<b>[!] DMI SAFETY SIGNATURE MISMATCH DETECTED</b><br><br>"
                "The loaded DMI profile does NOT match the currently active BIOS firmware:<br><br>"
                + "<br>".join(mismatch_reasons) +
                "<br><br><font color='#ff3131'><b>Injecting DMI data into an incompatible BIOS model or size "
                "will corrupt firmware tables and may brick the motherboard!</b></font><br><br>"
                "Do you want to override and FORCE load anyway?"
            )
            reply = QMessageBox.warning(
                self,
                "Signature Mismatch Warning",
                err_msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                self.log_to_terminal(f"[ERROR] DMI load aborted: Safety Signature mismatch for {os.path.basename(file_path)} ❌")
                self.staged_dmi_profile = None
                if hasattr(self, 'btn_apply_dmi'):
                    self.btn_apply_dmi.setEnabled(False)
                return
            else:
                self.log_to_terminal("[WARNING] Safety Signature override: DMI loaded by user override.")

        # Successfully verified (or override approved)
        self.staged_dmi_profile = profile
        if hasattr(self, 'btn_apply_dmi'):
            self.btn_apply_dmi.setEnabled(True)

        fields = profile.get("fields", {})
        ser_val  = fields.get("Serial Number", {}).get("value", fields.get("System Serial Number", {}).get("value", "N/A"))
        mod_val  = fields.get("System Model", {}).get("value", fields.get("Model", {}).get("value", "N/A"))
        mac_val  = fields.get("MAC Address", {}).get("value", "N/A")
        plat_val = fields.get("Platform", {}).get("value", "N/A")

        if hasattr(self, 'dmi_lbl_brand'):
            self._set_dmi_label(self.dmi_lbl_brand, prof_brand)
            self._set_dmi_label(self.dmi_lbl_model, mod_val)
            self._set_dmi_label(self.dmi_lbl_platform, plat_val)
            self._set_dmi_label(self.dmi_lbl_mac, mac_val)
            self._set_dmi_label(self.dmi_lbl_serial, ser_val)

        self.log_to_terminal(
            f"[SUCCESS] DMI Profile Loaded & Verified: <font color='#ffd600'><b>{os.path.basename(file_path)}</b></font> "
            f"({len(fields)} fields ready) ✅"
        )
        self.log_to_terminal(f"  - Source Model: {prof_model} | Serial: {ser_val}")
        self.log_to_terminal("  - <font color='#00ff41'><b>[APPLY DMI TO BIOS] button is now ENABLED! Click to inject.</b></font>")

    def apply_dmi_handler(self):
        """Applies staged DMI fields into the current BIOS file at the exact offsets."""
        if not self.staged_dmi_profile:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "No Profile Loaded", "Please LOAD a DMI profile first!")
            return

        if not self.current_bios_file or not os.path.exists(self.current_bios_file):
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "No Target BIOS", "No active BIOS file to inject into.")
            return

        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            "Confirm DMI Injection",
            f"Are you sure you want to inject DMI fields into the current BIOS?\n\n"
            f"Target File: {os.path.basename(self.current_bios_file)}\n\n"
            f"A safety backup (.dmi_backup.bin) will be created automatically.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            # 1. Automatic Backup
            import shutil
            backup_path = self.current_bios_file + ".dmi_backup.bin"
            shutil.copy2(self.current_bios_file, backup_path)
            self.log_to_terminal(f"[INFO] Created safety backup: {os.path.basename(backup_path)}")

            # 2. Read Binary
            with open(self.current_bios_file, "rb") as f:
                data = bytearray(f.read())

            fields = self.staged_dmi_profile.get("fields", {})
            raw_blocks = self.staged_dmi_profile.get("raw_blocks", {})
            self.log_to_terminal("[ACTION] Injecting DMI fields...")
            self.log_to_terminal(
                "  Strategy: 0) Raw EFI variable structure  1) Profile offset  2) String search  "
                "3) SMBIOS anchor (for factory-clean BIOS)"
            )

            from dmi_injector import DMIInjector
            all_occ = self.staged_dmi_profile.get("all_occurrences", {})
            injected_count = DMIInjector.inject_fields(
                data, fields, regions_map=getattr(self, 'current_regions_map', None),
                raw_blocks=raw_blocks, all_occurrences=all_occ, log_cb=self.log_to_terminal
            )

            # 3. Write back to BIOS file (with explicit flush + fsync to guarantee disk commit)
            with open(self.current_bios_file, "wb") as f:
                written = f.write(data)
                f.flush()
                import os as _os
                _os.fsync(f.fileno())
            self.log_to_terminal(
                f"[INFO] Written {written:,} bytes to {os.path.basename(self.current_bios_file)} "
                f"(file size verified: {os.path.getsize(self.current_bios_file):,} bytes)"
            )

            # 4. Refresh Hex Viewer
            self.hex_data_signal.emit(bytes(data))

            # 5. Disable Apply button now that it has been applied
            if hasattr(self, 'btn_apply_dmi'):
                self.btn_apply_dmi.setEnabled(False)
            self.staged_dmi_profile = None

            self.log_to_terminal(
                f"[SUCCESS] DMI Injection Complete! <font color='#00ff41'><b>{injected_count} fields</b></font> "
                f"successfully injected into {os.path.basename(self.current_bios_file)} ✅"
            )

            # 6. AUTOMATIC SAVE DIALOG TRIGGER
            from PySide6.QtWidgets import QFileDialog, QMessageBox
            base_dir = os.path.dirname(self.current_bios_file)
            base_name, ext = os.path.splitext(os.path.basename(self.current_bios_file))
            default_out = os.path.join(base_dir, f"{base_name}_DMI_OK{ext or '.bin'}")

            self.log_to_terminal("[ACTION] Opening Save Dialog to save the modified BIOS file...")
            save_dest, _ = QFileDialog.getSaveFileName(
                self,
                "Save Injected BIOS File",
                default_out,
                "BIOS Binary (*.bin *.rom);;All Files (*)"
            )

            final_saved_file = self.current_bios_file
            if save_dest:
                with open(save_dest, "wb") as sf:
                    sf.write(data)
                    sf.flush()
                    import os as _os2
                    _os2.fsync(sf.fileno())
                self.current_bios_file = save_dest
                final_saved_file = save_dest
                self.log_to_terminal(
                    f"[SUCCESS] Injected BIOS saved to: <font color='#00ff41'><b>{os.path.basename(save_dest)}</b></font> ✅"
                )
                QMessageBox.information(
                    self,
                    "DMI Injected & Saved",
                    f"Successfully injected {injected_count} DMI fields and saved to:\n{save_dest}\n\n"
                    f"Safety backup retained at:\n{backup_path}"
                )
            else:
                self.log_to_terminal(
                    f"[INFO] Save dialog skipped. Modified binary remains in: {os.path.basename(self.current_bios_file)} "
                    f"(Backup: {os.path.basename(backup_path)})"
                )
                QMessageBox.information(
                    self,
                    "DMI Injection Complete",
                    f"Successfully injected {injected_count} DMI fields into:\n{self.current_bios_file}\n\n"
                    f"Original file was backed up to:\n{backup_path}"
                )

        except Exception as e:
            self.log_to_terminal(f"[ERROR] DMI Injection failed: {e}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Injection Error", f"Failed to inject DMI:\n{e}")



    def advanced_extract_click_handler(self):
        self.log_to_terminal("[INFO] ADVANCED EXTRACT button clicked")
        if not self.current_bios_file: return
        current_bios = str(self.current_bios_file)

        destination = QFileDialog.getExistingDirectory(self, "Select Destination Folder", self.last_directory)
        if not destination: return
            
        self.last_directory = destination
            
        self.is_task_running = True
        self._handle_loading_state(True, "Universal Extraction...")
        self.progress_signal.emit(15)

        def _run_extract():
            try:
                self.progress_signal.emit(40)
                success = AdvancedExtractor.run_universal_extract(current_bios, destination, self.log_to_terminal)
                self.progress_signal.emit(100)
            except Exception as e:
                self.log_to_terminal(f"[ERROR] Extraction failed: {str(e)}")
            finally:
                QMetaObject.invokeMethod(self, "initiate_loader_stop", Qt.ConnectionType.QueuedConnection, Q_ARG(int, 2000))

        threading.Thread(target=_run_extract, daemon=True).start()

    def clear_terminal_and_logs(self):
        """
        Sequential Clear with State Counter:
        1st Press: Clear Terminal UI (Dashboard Information).
        2nd Press: Full System Reset (Work files, Workspace, Logs).
        """
        if self.reset_stage == 0:
            # First Press: Clear UI / Dashboard Info
            self.terminal.clear()
            self.reset_stage = 1
            self.log_to_terminal("[INFO] Dashboard information cleared.")
            self.log_to_terminal("[TIP] Press Ctrl+L again to clear all internal work, logs, and workspace files.")
        else:
            # Second Press: Full Reset
            self.reset_application_state()
            self.reset_stage = 0

    def reset_application_state(self):
        """Resets the entire application to its initial state."""
        self.current_bios_file = None
        self.current_regions_map = {}
        if hasattr(self, 'hex_tabs') and self.hex_tabs.count() > 0:
            self.hex_tabs.currentWidget().hex_model.set_regions({})
        self.mea_history = "" # Reset MEA history
        
        # Explicitly disable all module buttons
        self.enable_module_buttons({})
        
        self.terminal.clear()
        self.hex_model.set_data(b"")
        
        # Reset UI Labels & Buttons
        if hasattr(self, 'dmi_lbl_brand'):
            self._set_dmi_label(self.dmi_lbl_brand, "N/A")
            self._set_dmi_label(self.dmi_lbl_model, "N/A")
            self._set_dmi_label(self.dmi_lbl_platform, "N/A")
            self._set_dmi_label(self.dmi_lbl_mac, "N/A")
            self._set_dmi_label(self.dmi_lbl_serial, "N/A")
            self.cached_dmi_info = None
            self.staged_dmi_profile = None
            if hasattr(self, 'btn_save_dmi'):
                self.btn_save_dmi.setEnabled(False)
            if hasattr(self, 'btn_apply_dmi'):
                self.btn_apply_dmi.setEnabled(False)
        if hasattr(self, 'btn_smart_me_fix'):
            self.btn_smart_me_fix.setText("SMART ME FIX")
            self.btn_extract_dmi.setText("EXTRACT DMI")
        
        # Reset Log File and Workspace
        try:
            # Clear Log File
            with open(self.log_file, "w", encoding="utf-8") as f:
                f.write(f"--- Session Reset: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
            
            # Clear WORKSPACE directory (Auto-decompiled files)
            if os.path.exists(self.workspace_dir):
                shutil.rmtree(self.workspace_dir)
                os.makedirs(self.workspace_dir, exist_ok=True)
                self.log_to_terminal("[SYSTEM] Workspace files deleted.")

            self.log_to_terminal("[SYSTEM] Full System Reset performed successfully.")
            self.log_to_terminal("[INFO] All logs and history cleared. Software returned to defaults.")
        except Exception as e:
            self.log_to_terminal(f"[ERROR] Failed during system reset: {str(e)}")

    def show_logs_popup(self):
        """Opens a popup window to show the contents of app.log."""
        dialog = LogViewerDialog(self)
        dialog.exec()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        pass

    def dropEvent(self, event):
        # ── Hardware guard check ──
        if not getattr(self, '_programmer_connected', True):
            self._show_no_programmer_popup()
            event.ignore()
            return

        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            file_path = urls[0].toLocalFile()
            event.acceptProposedAction()  # Release Windows OLE drag-drop lock immediately!
            self.log_to_terminal(f"[INFO] File dropped: {os.path.basename(file_path)}")
            # Defer showing the dialog so dropEvent finishes cleanly and Windows returns to normal
            QTimer.singleShot(10, lambda p=file_path: self.prompt_and_load_bios(p))

    def open_bios_dialog(self):
        # ── Hardware guard check ──
        if not getattr(self, '_programmer_connected', True):
            self._show_no_programmer_popup()
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open BIOS File",
            self.last_directory,
            "All Supported Files (*.bin *.rom *.fd *.cap *.exe *.pfs *.pkg *.sbk *.sbi *.msdm);;BIOS Dumps (*.bin *.rom *.fd *.cap);;Update Packages (*.exe *.pfs *.pkg);;All Files (*)"
        )

        if file_path:
            self.last_directory = os.path.dirname(file_path)
            self.log_to_terminal(f"[INFO] User selected file: {os.path.basename(file_path)}")
            self.prompt_and_load_bios(file_path)

    def prompt_and_load_bios(self, file_path: str):
        """
        Pauses before heavy analysis, showing a sleek confirmation popup with
        file details, size, and prompt 'Press [ENTER] to start analysis'.
        Eliminates UI freeze and lag upon drop or file browsing.
        """
        if not file_path or not os.path.exists(file_path):
            return

        allowed_extensions = {'.bin', '.rom', '.fd', '.cap', '.exe', '.pfs', '.pkg', '.sbk', '.sbi', '.msdm'}
        _, ext = os.path.splitext(file_path)
        if ext.lower() not in allowed_extensions:
            # Let standard validator display invalid format dialog
            self.load_bios_file(file_path)
            return

        try:
            from firmware_confirm_dialog import FirmwareConfirmDialog
            dlg = FirmwareConfirmDialog(file_path, parent=self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self.log_to_terminal(f"[INFO] Ingestion confirmed for: {os.path.basename(file_path)}")
                QApplication.processEvents()
                # Run immediately with zero latency
                QTimer.singleShot(0, lambda: self.load_bios_file(file_path))
            else:
                self.log_to_terminal(f"[INFO] Ingestion cancelled by technician: {os.path.basename(file_path)}")
        except Exception as e:
            self.log_to_terminal(f"[WARNING] Confirmation dialog fallback ({e}). Proceeding to load.")
            self.load_bios_file(file_path)

    def _show_no_programmer_popup(self):
        """Shown when user tries to do anything without the programmer connected."""
        dlg = QDialog(self)
        dlg.setWindowTitle("Hardware Required")
        dlg.setFixedSize(420, 240)
        dlg.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Dialog)
        dlg.setStyleSheet("""
            QDialog { background-color: #171a1d; color: #ffffff; }
            QLabel  { color: #ffffff; font-family: 'Segoe UI'; }
            QPushButton {
                background-color: #252a2e; color: #4cd3e3;
                border: 1px solid #3c444d; border-radius: 6px;
                padding: 8px 22px; font-size: 12px; font-weight: bold;
            }
            QPushButton:hover { background-color: #2e353b; border-color: #4cd3e3; color: #ffffff; }
        """)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(28, 24, 28, 20)
        lay.setSpacing(10)

        icon_lbl = QLabel("🔌")
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 36px;")
        lay.addWidget(icon_lbl)

        title_lbl = QLabel("R1 Programmer Not Connected")
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #ff4444;")
        lay.addWidget(title_lbl)

        msg_lbl = QLabel(
            "All BIOS services are disabled.<br>"
            "Please connect your <b>R1 BIOS Programmer (FT232H)</b> to continue.<br><br>"
            "Need help? Contact us:<br>"
            "<a href='https://r1itlab.com/contact' style='color:#00f3ff;'>r1itlab.com/contact</a>&nbsp;&nbsp;"
            "<a href='https://t.me/r1itlab' style='color:#00f3ff;'>Telegram: @r1itlab</a>"
        )
        msg_lbl.setAlignment(Qt.AlignCenter)
        msg_lbl.setWordWrap(True)
        msg_lbl.setOpenExternalLinks(True)
        msg_lbl.setStyleSheet("font-size: 11px; color: #aaaaaa;")
        lay.addWidget(msg_lbl)

        lay.addStretch()

        btn_ok = QPushButton("OK")
        btn_ok.clicked.connect(dlg.accept)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(btn_ok)
        btn_row.addStretch()
        lay.addLayout(btn_row)

        dlg.exec()

    def show_license_menu(self, event):
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QCursor
        
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #444;
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
            }
            QMenu::item {
                padding: 8px 20px;
            }
            QMenu::item:selected {
                background-color: #00ff41;
                color: #000;
            }
        """)
        
        action_license = menu.addAction("🔑 Manage License Key")
        action = menu.exec(QCursor.pos())
        
        if action == action_license:
            dialog = LicenseKeyDialog(self)
            dialog.exec()
            # Re-check status after dialog closes
            from programmer_guard import is_programmer_connected
            self.update_programmer_status(is_programmer_connected())

    @Slot(bool)
    def update_programmer_status(self, connected: bool):
        """Called by background monitor to update the indicator and enable/disable UI."""
        import license_manager
        active_license = license_manager.get_active_license()
        
        if active_license:
            self._programmer_connected = True
            self.programmer_dot.setStyleSheet(
                "color: #00ff88; font-size: 14px; padding: 0 2px;"
            )
            company = active_license.get('company', 'Unknown')
            # Truncate company name if too long to prevent pushing UI
            if len(company) > 15:
                company = company[:12] + "..."
            self.programmer_status_label.setText(f"LICENSE ACTIVE: {company}")
            self.programmer_status_label.setStyleSheet(
                "background: #1c2524; color: #4cd3e3; font-size: 10px; font-weight: bold; font-family: 'Segoe UI', sans-serif; "
                "border: 1px solid #1f4a56; border-radius: 6px; padding: 2px 8px;"
            )
            if hasattr(self, 'top_toolbar'):
                self.top_toolbar.setEnabled(True)
            return

        self._programmer_connected = connected

        if connected:
            self.programmer_dot.setStyleSheet(
                "color: #00ff88; font-size: 14px; padding: 0 2px;"
            )
            self.programmer_status_label.setText("PROGRAMMER: CONNECTED")
            self.programmer_status_label.setStyleSheet(
                "background: #1c2524; color: #00ff88; font-size: 10px; font-weight: bold; font-family: 'Segoe UI', sans-serif; "
                "border: 1px solid #1f4a3c; border-radius: 6px; padding: 2px 8px;"
            )
            if hasattr(self, 'top_toolbar'):
                self.top_toolbar.setEnabled(True)
        else:
            self.programmer_dot.setStyleSheet(
                "color: #ff5252; font-size: 14px; padding: 0 2px;"
            )
            self.programmer_status_label.setText("PROGRAMMER: DISCONNECTED")
            self.programmer_status_label.setStyleSheet(
                "background: #2a1c1d; color: #ff5252; font-size: 10px; font-weight: bold; font-family: 'Segoe UI', sans-serif; "
                "border: 1px solid #4a2123; border-radius: 6px; padding: 2px 8px;"
            )
            if hasattr(self, 'top_toolbar'):
                self.top_toolbar.setEnabled(False)

    @Slot(bool, str, float)
    def _handle_loading_state(self, show, text="", estimate=0.0):
        if show:
            self.loading_overlay.start(text, estimate)
        else:
            self.loading_overlay.stop()

    def load_bios_file(self, file_path):
        allowed_extensions = {'.bin', '.rom', '.fd', '.cap', '.exe', '.pfs', '.pkg', '.sbk', '.sbi', '.msdm'}
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        if ext not in allowed_extensions:
            self.log_to_terminal(f"[ERROR] Invalid file format: '{ext}'.")
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("Invalid File Format")
            msg.setText(f"The file you selected has an invalid format: '{ext}'\n\nPlease provide a BIOS dump or supported update package.")
            msg.setStyleSheet("QMessageBox { background-color: #171a1d; color: #ff5252; } QLabel { color: #ff5252; font-weight: bold; } QPushButton { background-color: #252a2e; border: 1px solid #3c444d; color: #ffffff; border-radius: 4px; padding: 6px 16px; font-weight: bold; } QPushButton:hover { background-color: #e03131; color: #ffffff; }")
            msg.exec()
            return

        # ── 1. INSTANT ZERO-LATENCY UI RESPONSE (0ms) ──
        self.is_task_running = True
        estimate = tracker.get_estimate("load_bios_file", 6.0)
        self._handle_loading_state(True, "Reading Firmware Image...", estimate)
        self._start_perf_time = time.perf_counter()
        self.progress_signal.emit(10)
        self.status_text_signal.emit("Reading Firmware Image...")
        self.overlay_log_signal.emit(f"Ingesting {os.path.basename(file_path)}...")

        self.current_bios_file = str(file_path)
        self.reset_stage = 0
        self.terminal.clear()
        self.mea_history = ""
        self.cached_dmi_info = None
        self.staged_dmi_profile = None

        if hasattr(self, 'btn_save_dmi'):
            self.btn_save_dmi.setEnabled(False)
        if hasattr(self, 'btn_apply_dmi'):
            self.btn_apply_dmi.setEnabled(False)

        # Immediate DMI labels reset
        if hasattr(self, 'dmi_lbl_brand'):
            self._set_dmi_label(self.dmi_lbl_brand, "Detecting...")
            self._set_dmi_label(self.dmi_lbl_model, "N/A")
            self._set_dmi_label(self.dmi_lbl_platform, "N/A")
            self._set_dmi_label(self.dmi_lbl_mac, "N/A")
            self._set_dmi_label(self.dmi_lbl_serial, "N/A")

        self.log_to_terminal(f"[INFO] Initializing analysis for: {os.path.basename(file_path)}")

        # Force UI repaint immediately so loading overlay animates instantly on screen
        QApplication.processEvents()

        # Smart Extraction for Executable Wrappers/Packages
        if ext in ['.exe', '.pfs', '.pkg', '.sbk', '.sbi', '.msdm', '.cap']:
            self.progress_signal.emit(25)
            self.status_text_signal.emit("Unpacking Vendor Package...")
            self.overlay_log_signal.emit(f"Smart Extraction ({ext.upper()})...")
            self.log_to_terminal(f"[INFO] Detected Vendor Package ({ext.upper()}). Launching Smart Extraction...")
            
            def run_smart_extract():
                try:
                    from advanced_extractor import AdvancedExtractor
                    temp_extract_dir = os.path.join(self.workspace_dir, "smart_extract")
                    os.makedirs(temp_extract_dir, exist_ok=True)
                    
                    if AdvancedExtractor.run_universal_extract(file_path, temp_extract_dir, self.log_to_terminal):
                        extracted_files = []
                        for root, _, files in os.walk(temp_extract_dir):
                            for f in files:
                                if f.lower().endswith(('.bin', '.rom', '.fd')):
                                    extracted_files.append(os.path.join(root, f))
                        
                        if extracted_files:
                            best_file = max(extracted_files, key=os.path.getsize)
                            self.log_to_terminal(f"[SUCCESS] Smart Extraction successful. Loading image: {os.path.basename(str(best_file))}")
                            QTimer.singleShot(0, lambda: self.load_bios_file(best_file))
                            return
                        else:
                            self.log_to_terminal("[WARNING] Extraction succeeded but no BIOS image (.bin) was found inside.")
                    else:
                        self.log_to_terminal("[ERROR] Smart Extraction failed for this package.")
                except Exception as e:
                    self.log_to_terminal(f"[ERROR] Smart Extraction Crashed: {str(e)}")
                finally:
                    QMetaObject.invokeMethod(self, "initiate_loader_stop", Qt.ConnectionType.QueuedConnection, Q_ARG(int, 2000))

            threading.Thread(target=run_smart_extract, daemon=True).start()
            return

        # ── 2. FLUID ASYNCHRONOUS BACKGROUND WORKER (ZERO FREEZE) ──
        def run_analysis_task():
            try:
                # Step 1: Read File in Background (Off GUI thread)
                self.progress_signal.emit(20)
                self.status_text_signal.emit("Reading Firmware Image...")
                self.overlay_log_signal.emit("Reading binary image...")
                self.log_to_terminal("[INFO] Reading binary image into memory...")
                
                with open(file_path, "rb") as f:
                    raw_data = f.read()

                # Step 2: High-Speed Brand Detection in Background
                self.progress_signal.emit(35)
                self.status_text_signal.emit("Detecting Brand & Signatures...")
                self.overlay_log_signal.emit("Scanning brand signatures...")
                self.log_to_terminal("[INFO] Scanning firmware signatures & brand detection...")
                
                from dmi_extractor import DMIExtractor
                brand = DMIExtractor.detect_brand(raw_data, file_path=file_path)
                
                # Instantly reflect brand on UI safely via QueuedConnection & dispatch brand tools
                if hasattr(self, 'dmi_lbl_brand'):
                    QMetaObject.invokeMethod(self.dmi_lbl_brand, "setText", Qt.ConnectionType.QueuedConnection, Q_ARG(str, brand))
                self.brand_tools_signal.emit(brand)
                
                self.log_to_terminal(f"[INFO] Auto-Detected Brand: {brand}")
                self.overlay_log_signal.emit(f"Brand: {brand}")

                # Step 3: Hex Viewer Feed (Queued to GUI thread)
                self.progress_signal.emit(45)
                self.status_text_signal.emit("Loading Hex Engine...")
                self.overlay_log_signal.emit("Mapping Hex buffer...")
                self.hex_data_signal.emit(raw_data)
                self.log_to_terminal("[INFO] Hex data loaded to viewer (Deep analysis starting...)")

                # Step 4: SPI & Firmware Descriptor Parsing
                self.progress_signal.emit(60)
                self.status_text_signal.emit("Parsing SPI Firmware...")
                self.overlay_log_signal.emit("Parsing Flash Descriptor & Regions...")
                
                r_settings = self.report_manager.settings
                metadata = get_bios_metadata(file_path, self.log_to_terminal, getattr(self, "handle_mea_output", None), report_settings=r_settings, raw_data=raw_data)
                
                if metadata:
                    self.progress_signal.emit(65)
                    self.status_text_signal.emit("Generating Health Report...")
                    self.overlay_log_signal.emit("System Health Report Generated")
                    self.log_to_terminal("-" * 30)
                    self.log_to_terminal(">>> SYSTEM HEALTH REPORT GENERATED")
                    self.log_to_terminal("-" * 30)

                    # Microcode audit is handled by bios_parser based on report_settings
                    self.progress_signal.emit(78)
                    
                    # Chain Analysis 4: BIOS Guard technology
                    self.progress_signal.emit(88)
                    if r_settings.get('show_bios_guard', True):
                        self.status_text_signal.emit("Checking Security / BIOS Guard...")
                        self.overlay_log_signal.emit("Checking Security / BIOS Guard...")
                        from analysis_suite import AnalysisSuite
                        AnalysisSuite.run_bios_guard_analysis(file_path, self.log_to_terminal)
                        
                    self.progress_signal.emit(95)
                    self.status_text_signal.emit("Finalizing Firmware Profile...")
                    self.overlay_log_signal.emit("Finalizing firmware profile...")

                    self.log_to_terminal("-" * 30)
                    self.log_to_terminal("[SUCCESS] ALL ANALYSES COMPLETE")
                    self.log_to_terminal("-" * 30)
                    
                    QMetaObject.invokeMethod(self.btn_save, "setEnabled", Qt.ConnectionType.QueuedConnection, Q_ARG(bool, True))
                    QMetaObject.invokeMethod(self.btn_smart_me_fix, "setEnabled", Qt.ConnectionType.QueuedConnection, Q_ARG(bool, True))
                        
                    # Setup region patch interactions
                    regions = metadata.get("regions")
                    if regions and isinstance(regions, dict) and any(regions.values()):
                        self.current_regions_map = regions
                        if hasattr(self, 'hex_tabs') and self.hex_tabs.count() > 0:
                            self.hex_tabs.currentWidget().hex_model.set_regions(regions)
                        self.module_buttons_signal.emit(regions)
                        
                        # Auto decompile setup
                        self.auto_decompile_pending = True
                        mea_py = os.path.join(str(get_app_root()), "ME Analyzer", "MEA.py")
                        if not os.path.exists(mea_py):
                            self.run_auto_decompile()
                    else:
                        self.current_regions_map = {}
                        self.module_buttons_signal.emit({})
                        self.log_to_terminal("\n" + "!"*45)
                        self.log_to_terminal("[NOTICE] THIS IS NOT AN INTEL FIRMWARE FILE")
                        self.log_to_terminal("[INFO] AMD OR OTHER FIRMWARE SYSTEM DETECTED")
                        self.log_to_terminal("!"*45 + "\n")
                else:
                    self.current_regions_map = {}
                    self.module_buttons_signal.emit({})
                    self.log_to_terminal("[ERROR] Failed to process BIOS file.")
            except Exception as e:
                self.log_to_terminal(f"[ERROR] Load task crashed: {str(e)}")
            finally:
                self.progress_signal.emit(100)
                self.status_text_signal.emit("Analysis Complete")
                self.overlay_log_signal.emit("Analysis Complete")
                
                if hasattr(self, '_start_perf_time'):
                    duration = time.perf_counter() - self._start_perf_time
                    tracker.record_duration("load_bios_file", duration)

                QMetaObject.invokeMethod(self, "finalize_load_task", Qt.ConnectionType.QueuedConnection)

        # Launch background thread immediately - UI main thread is free!
        threading.Thread(target=run_analysis_task, daemon=True).start()


    @Slot()
    def finalize_load_task(self):
        """Called when analysis completes to finalize UI updates."""
        self.log_to_terminal("[SUCCESS] Operation finished.")
        # Snappy closure
        self.initiate_loader_stop(500) 

    def run_auto_decompile(self):
        """Internal helper to run automatic decompilation for workspace readiness."""
        if not getattr(self, "auto_decompile_pending", False):
            return
            
        if not self.current_bios_file or not self.current_regions_map:
            self.auto_decompile_pending = False
            return
            
        self.auto_decompile_pending = False
        self.log_to_terminal("-" * 30)
        self.log_to_terminal("[INFO] Initializing automatic BIOS decompilation...")
        
        try:
            # 1. Parse Version from MEA History
            mea_meta = parse_mea_output(self.mea_history)
            me_version = mea_meta.get("version")
            
            if not me_version:
                self.log_to_terminal("[ERROR] Automatic Version Detection Failed. Check patterns in mea_parser.py.")
                self.log_to_terminal(f"[DEBUG] Captured MEA History length: {len(self.mea_history)}")
                return

            self.log_to_terminal(f"[INFO] Detected ME Version: {me_version}")
            self.log_to_terminal(f"[INFO] Targeting Workspace: {self.workspace_dir}")
            
            # 2. Run decompiler using ONLY Intel FIT (Mandatory)
            decomp_target = fit_automator.execute_fit_decompile(self.current_bios_file, me_version, self.workspace_dir, self.log_to_terminal)
            
            if decomp_target and os.path.exists(decomp_target):
                self.log_to_terminal("-" * 30)
                self.log_to_terminal(f"[SUCCESS] INTERNAL WORKSPACE READY: {os.path.basename(decomp_target)}")
            else:
                self.log_to_terminal("[WARN] Standard Intel FIT Decompile failed (Image corruption detected).")
                self.log_to_terminal("[TIP] You can try manual repair by clicking the 'SMART ME FIX' button.")
                self.skip_auto_repair = False
                
        except Exception as e:
            self.log_to_terminal(f"[ERROR] Auto-decompile process crashed: {str(e)}")

        pass

    def handle_mea_output(self, ui_lines, file_lines):
        # Called from background thread
        self.mea_output_signal.emit(ui_lines, file_lines)

    @Slot(list, list)
    def _handle_mea_output_internal(self, ui_lines, file_lines):
        self.mea_history += "\n".join(file_lines) + "\n"
        
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                for line in file_lines:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    # Replace UI color tag if somehow it sneaked in file log
                    line_clean = line.replace("<font color='#00f3ff'>", "").replace("</font>", "")
                    f.write(f"[{timestamp}] {line_clean}\n")
        except Exception:
            pass
            
        suppress_sep = False
        for line in ui_lines:
            line_l = line.lower()
            if any(ign in line_l for ign in ["outdated me analyzer", "outdated database", "download the latest from", "github.com/platomav"]):
                suppress_sep = True
                continue
            if suppress_sep and all(c in "═━-=&nbsp; " for c in line.replace("<font color='#d0d0e0'>", "").replace("</font>", "").strip()):
                suppress_sep = False
                continue
            suppress_sep = False
            self.terminal.append(line)
            # Detect end of MEA report
            if "[SUCCESS] ME Analyzer complete." in line:
                self.log_to_terminal("-" * 30)
                self.log_to_terminal("<font color='#00f3ff'><b>[INFO] Firmware Analysis Complete.</b></font>")
                
                # --- MANUAL SMART REPAIR TRIGGER ---
                if "Initialized" in self.mea_history:
                    self.log_to_terminal("<font color='#ffff00'><b>[NOTICE] Initialized Firmware Detected! ⚡ ⚠️</b></font>")
                self.log_to_terminal("[INFO] Decompilation deferred for performance.")
                self.log_to_terminal("[TIP] Click <b>'SMART ME FIX'</b> to start the repair pipeline.")
                self.log_to_terminal("-" * 30)
                    
        self.terminal.verticalScrollBar().setValue(self.terminal.verticalScrollBar().maximum())



    @Slot(int)
    def start_auto_save_countdown_with_delay(self, seconds=4):
        """Starts the auto-save countdown with a specific duration."""
        if self.is_auto_saving:
            return
            
        self.is_auto_saving = True
        self.auto_save_countdown = seconds
        self.btn_save.setText("")
        self.btn_save.setToolTip(f"SAVE ({self.auto_save_countdown}s)")
        self.btn_save.setStyleSheet("border-color: #00ff41; color: #00ff41; font-weight: bold;") # Matrix Green for notice
        self.auto_save_timer.start(1000)

    def start_auto_save_countdown(self):
        """Initializes and starts the 4-second auto-save timer."""
        self.start_auto_save_countdown_with_delay(4)

    def update_auto_save_ui(self):
        """Timer callback that decrements the counter and triggers save at 0."""
        self.auto_save_countdown -= 1
        
        if self.auto_save_countdown <= 0:
            self.auto_save_timer.stop()
            self.btn_save.setText("")
            self.btn_save.setToolTip("SAVE CHANGES")
            self.btn_save.setStyleSheet("border-color: #ff00ff; color: #ff00ff;") # Reset to Purple
            self.is_auto_saving = False
            # Trigger the save dialog
            self.save_bios_changes()
        else:
            self.btn_save.setText("")
        self.btn_save.setToolTip(f"SAVE ({self.auto_save_countdown}s)")

    def save_bios_changes(self):
        # Stop auto-save if user clicks manually
        if self.is_auto_saving:
            self.auto_save_timer.stop()
            self.is_auto_saving = False
            self.btn_save.setText("")
            self.btn_save.setToolTip("SAVE CHANGES")
            self.btn_save.setStyleSheet("border-color: #ff00ff; color: #ff00ff;")
            
        if not self.current_bios_file:
            return
            
        # Apply prefix if set
        filename = os.path.basename(self.current_bios_file)
        if self.auto_save_prefix:
            filename = self.auto_save_prefix + filename
            self.auto_save_prefix = "" # Reset after use
            
        # Suggest the current filename in the last used directory
        suggested_path = os.path.join(self.last_directory, filename)
        
        reply = QFileDialog.getSaveFileName(
            self, "Save BIOS Changes", suggested_path, "BIOS Files (*.bin *.rom *.fd *.cap);;All Files (*)"
        )
        
        if reply[0]:
            self.last_directory = os.path.dirname(reply[0])
            try:
                with open(reply[0], "wb") as f:
                    f.write(self.hex_model.get_data())
                self.log_to_terminal(f"[SUCCESS] Changes saved successfully to: {os.path.basename(reply[0])}")
                
                # --- AUTO-RELOAD SAVED FILE ---
                self.log_to_terminal("[INFO] Automatically reloading the saved file after 2 seconds for verification...")
                saved_path = str(reply[0])
                self._reload_timer = QTimer(self)
                self._reload_timer.setSingleShot(True)
                self._reload_timer.timeout.connect(lambda: self.load_bios_file(saved_path))
                self._reload_timer.start(2000)
                
            except Exception as e:
                self.log_to_terminal(f"[ERROR] Failed to save changes: {str(e)}")

    @Slot(str, str, bool)
    def show_error_prompt_sync(self, title: str, message: str, allow_custom_fit: bool = False):
        """
        Synchronous UI blocking prompt for fatal/critical pipeline errors.
        Sets self.last_error_choice to return the choice across threads.
        """
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setMinimumWidth(650)
        dialog.setMinimumHeight(350)
        dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowStaysOnTopHint)
        
        is_light = getattr(self, 'is_light_mode', False)
        bg_color = "#f0f2f5" if is_light else "#171a1d"
        border_color = "#ef4444" if is_light else "#ff3131"
        text_color = "#1f2937" if is_light else "#ffffff"
        btn_bg = "#ffffff" if is_light else "#252a2e"
        
        dialog.setStyleSheet(f"QDialog {{ background-color: {bg_color}; border: 2px solid {border_color}; }}")
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        lbl_icon = QLabel(f"⚠️ {title.upper()}")
        lbl_icon.setStyleSheet(f"color: {border_color}; font-size: 22px; font-weight: bold; font-family: 'Orbitron', monospace;")
        lbl_icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_icon)
        
        lbl_msg = QTextBrowser()
        lbl_msg.setHtml(message)
        lbl_msg.setStyleSheet(f"background-color: {'#ffffff' if is_light else '#12141d'}; color: {text_color}; font-size: 14px; border: 1px solid {border_color}; padding: 10px;")
        layout.addWidget(lbl_msg)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        btn_retry = QPushButton("Retry")
        btn_retry.setCursor(Qt.PointingHandCursor)
        btn_retry.setStyleSheet(f"QPushButton {{ background-color: {btn_bg}; color: {text_color}; border: 1px solid #f59e0b; font-size: 14px; font-weight: bold; padding: 12px; }} QPushButton:hover {{ background-color: #f59e0b; color: #fff; }}")
        
        btn_ignore = QPushButton("Ignore && Continue")
        btn_ignore.setCursor(Qt.PointingHandCursor)
        btn_ignore.setStyleSheet(f"QPushButton {{ background-color: {btn_bg}; color: {text_color}; border: 1px solid #6b7280; font-size: 14px; font-weight: bold; padding: 12px; }} QPushButton:hover {{ background-color: #6b7280; color: #fff; }}")
        
        btn_abort = QPushButton("Abort")
        btn_abort.setCursor(Qt.PointingHandCursor)
        btn_abort.setStyleSheet(f"QPushButton {{ background-color: {border_color}; color: #ffffff; border: 1px solid {border_color}; font-size: 14px; font-weight: bold; padding: 12px; }} QPushButton:hover {{ background-color: #dc2626; }}")
        
        btn_layout.addWidget(btn_retry)
        btn_layout.addWidget(btn_ignore)
        btn_layout.addWidget(btn_abort)
        layout.addLayout(btn_layout)
        
        if allow_custom_fit:
            # Inline class for DropZone so it has access to local context
            class ExternalFitDropZone(QFrame):
                def __init__(self, parent_dialog, main_app):
                    super().__init__()
                    self.parent_dialog = parent_dialog
                    self.main_app = main_app
                    self.setAcceptDrops(True)
                    self.setStyleSheet(f"QFrame {{ border: 2px dashed #00f3ff; background-color: {'#ffffff' if is_light else '#12141d'}; border-radius: 8px; margin-top: 10px; }} QFrame:hover {{ background-color: {'#e0f2fe' if is_light else '#1a1d2e'}; }}")
                    vlay = QVBoxLayout(self)
                    vlay.setContentsMargins(10, 20, 10, 20)
                    lbl = QLabel("⬇️ DROP EXTERNAL FIT TOOL (.EXE) HERE TO RETRY ⬇️")
                    lbl.setAlignment(Qt.AlignCenter)
                    lbl.setStyleSheet("color: #00f3ff; font-weight: bold; border: none; background: transparent; font-size: 14px;")
                    vlay.addWidget(lbl)
                    
                def dragEnterEvent(self, event):
                    if event.mimeData().hasUrls():
                        urls = event.mimeData().urls()
                        if urls and urls[0].toLocalFile().lower().endswith(".exe"):
                            event.accept()
                            return
                    event.ignore()
                    
                def dropEvent(self, event):
                    urls = event.mimeData().urls()
                    if urls:
                        file_path = urls[0].toLocalFile()
                        try:
                            from fit_automator import get_paths
                            import shutil
                            import os
                            ext_dir = get_paths()["fit_workspace"] / "external_custom_fit"
                            ext_dir.mkdir(parents=True, exist_ok=True)
                            dest_path = ext_dir / "fit.exe"
                            shutil.copy2(file_path, dest_path)
                            self.main_app.external_fit_tool_path = str(dest_path)
                            self.parent_dialog.done(3) # Retry with external
                        except Exception as e:
                            self.main_app.log_to_terminal(f"[ERROR] Failed to setup external FIT tool: {e}")
            
            drop_zone = ExternalFitDropZone(dialog, self)
            layout.addWidget(drop_zone)
        
        btn_retry.clicked.connect(lambda: dialog.done(1))
        btn_ignore.clicked.connect(lambda: dialog.done(2))
        btn_abort.clicked.connect(lambda: dialog.done(0))
        
        result = dialog.exec()
        
        if result == 1:
            self.last_error_choice = "retry"
        elif result == 2:
            self.last_error_choice = "ignore"
        elif result == 3:
            self.last_error_choice = "retry_with_external"
        else:
            self.last_error_choice = "abort"


if __name__ == "__main__":
    import ctypes
    # Tell Windows this is a separate app, not generic Python, so taskbar/titlebar icons work
    try:
        myappid = 'r1ailab.biostool.premium.1'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

    app = QApplication(sys.argv)

    # Set app-wide font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Set global application window icon
    app_icon_path = get_resource_path(os.path.join("assets", "icon.ico"))
    if not os.path.exists(app_icon_path):
        app_icon_path = get_resource_path(os.path.join("assets", "R1AILAB.png"))
    if os.path.exists(app_icon_path):
        app.setWindowIcon(QIcon(app_icon_path))

    # ═══════════════════════════════════════════════════════════════════════
    # DUAL-LAYER SECURITY GATE
    # Layer 1: Valid Activation Key (GitHub verified + HWID locked)
    # Layer 2: R1 BIOS Programmer (FT232H hardware dongle)
    # At least ONE must be active — otherwise software is completely blocked.
    # ═══════════════════════════════════════════════════════════════════════
    from programmer_guard import is_programmer_connected
    from security_gate import SecurityGate, TRUST_NONE, TRUST_KEY_ONLY, TRUST_HW_ONLY, TRUST_FULL

    _security_gate = SecurityGate()

    # ── MODERN SPLASH SCREEN (Cyber Hexagon + Dynamic Circular Gauge) ────
    from splash_screen import ModernSplashScreen
    import time

    TOTAL_SPLASH_SEC = 3.0  # 3.0 seconds load duration

    splash = ModernSplashScreen(duration_ms=int(TOTAL_SPLASH_SEC * 1000), auto_timer=False)
    splash.start_animation()
    app.processEvents()

    start_splash_time = time.time()

    # Phase 1: Smoothly animate from 0% to ~25%
    while (time.time() - start_splash_time) < 0.65 and splash.progress < 25.0:
        elapsed = time.time() - start_splash_time
        pct = min(25.0, (elapsed / TOTAL_SPLASH_SEC) * 100.0)
        splash.set_progress_val(pct)
        app.processEvents()
        time.sleep(0.015)

    # Phase 2: Check security gate
    splash.set_progress_val(28.0, "AUTHENTICATING SECURITY GATE...")
    app.processEvents()
    trust_level = _security_gate.check_and_unlock(parent_widget=splash)

    # Phase 3: Initialize main window in memory while splash advances (STRICTLY HIDDEN)
    splash.set_progress_val(40.0, "LOADING FIRMWARE ENGINES...")
    app.processEvents()
    window = BiosServiceTool()
    window.initialize_ui_window(show_now=False)
    app.processEvents()

    # Phase 4: GUARANTEED 100% COMPLETION LOOP (Strictly reaches 100% in ~3s)
    # Software will NEVER open prematurely before 100%!
    curr_pct = max(splash.progress, 55.0)
    while splash.progress < 100.0:
        elapsed = time.time() - start_splash_time
        target_pct = (elapsed / TOTAL_SPLASH_SEC) * 100.0
        curr_pct += 0.85
        pct = min(100.0, max(target_pct, curr_pct))
        splash.set_progress_val(pct)
        app.processEvents()
        time.sleep(0.018)

    # Phase 5: Display 100% and SYSTEM READY in neon green with full glowing rings
    splash.set_progress_val(100.0, "SYSTEM READY")
    app.processEvents()
    time.sleep(0.40)  # Let user clearly see 100% SYSTEM READY

    # Phase 6: Transition to main window ONLY AFTER splash has fully completed 100%
    splash.close()
    window.show()
    window.raise_()
    window.activateWindow()

    # ── Set initial programmer status ──
    _initial_connected = is_programmer_connected()
    window._programmer_connected = _initial_connected

    # ── Show startup status toast ──
    def _show_startup_status():
        window.update_programmer_status(_initial_connected)
        if trust_level == TRUST_FULL:
            msg = QMessageBox(window)
            msg.setWindowTitle("Security Status")
            msg.setText("Full Dual-Auth Active\n\n✅ License Key: Valid\n✅ R1 BIOS Programmer: Connected")
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setStyleSheet(
                "QMessageBox { background-color: #171a1d; color: #00ff88; }"
                "QLabel { color: #00ff88; font-weight: bold; font-family: 'Segoe UI', sans-serif; }"
                "QPushButton { background-color: #252a2e; color: #00ff88; border: 1px solid #1f4a38; border-radius: 6px; padding: 6px 18px; font-weight: bold; }"
                "QPushButton:hover { background-color: #1c2e28; color: #ffffff; }"
            )
            QTimer.singleShot(2200, msg.accept)
            msg.exec()
        elif trust_level == TRUST_KEY_ONLY:
            msg = QMessageBox(window)
            msg.setWindowTitle("Security Status")
            msg.setText("License Key Active\n\n✅ License Key: Valid\n⚠️ R1 BIOS Programmer: Not Connected")
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setStyleSheet(
                "QMessageBox { background-color: #171a1d; color: #4cd3e3; }"
                "QLabel { color: #4cd3e3; font-weight: bold; font-family: 'Segoe UI', sans-serif; }"
                "QPushButton { background-color: #252a2e; color: #4cd3e3; border: 1px solid #3c444d; border-radius: 6px; padding: 6px 18px; font-weight: bold; }"
                "QPushButton:hover { background-color: #2e353b; color: #ffffff; }"
            )
            QTimer.singleShot(2200, msg.accept)
            msg.exec()
        elif trust_level == TRUST_HW_ONLY:
            msg = QMessageBox(window)
            msg.setWindowTitle("Security Status")
            msg.setText("Hardware Dongle Active\n\n⚠️ License Key: Not Activated\n✅ R1 BIOS Programmer: Connected")
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setStyleSheet(
                "QMessageBox { background-color: #171a1d; color: #fbbf24; }"
                "QLabel { color: #fbbf24; font-weight: bold; font-family: 'Segoe UI', sans-serif; }"
                "QPushButton { background-color: #252a2e; color: #fbbf24; border: 1px solid #5a451e; border-radius: 6px; padding: 6px 18px; font-weight: bold; }"
                "QPushButton:hover { background-color: #2e2619; color: #ffffff; }"
            )
            QTimer.singleShot(2200, msg.accept)
            msg.exec()

    QTimer.singleShot(400, _show_startup_status)

    # ── Start background security monitoring (every 10s) ────────────────────
    # If both programmer disconnects AND license is revoked → force close.
    _security_gate.start_monitoring(window, check_interval_ms=10000)

    # ── Also update programmer status indicator every 5s ────────────────────
    _prog_status_timer = QTimer()
    _prog_status_timer.setInterval(5000)
    def _update_prog_indicator():
        connected = is_programmer_connected()
        window.update_programmer_status(connected)
    _prog_status_timer.timeout.connect(_update_prog_indicator)
    _prog_status_timer.start()

    # ── Check for file path argument (Integration with R1 FLASH ULTRA) ──────
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        if os.path.exists(file_path):
            QTimer.singleShot(1000, lambda: window.load_bios_file(file_path))

    sys.exit(app.exec())






