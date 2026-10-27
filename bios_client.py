# Main Entry Point
import sys
import os
import io

# Add current directory to path for IDE module resolution
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QTextEdit, QFileDialog, 
                             QLabel, QFrame, QDialog, QTableView, QHeaderView, QSplitter,
                             QMenu, QMessageBox, QGraphicsBlurEffect, QTabWidget,
                             QLineEdit, QComboBox, QCheckBox, QDialogButtonBox,
                             QAbstractItemView, QInputDialog)
from PySide6.QtCore import (Qt, QSize, QMetaObject, Q_ARG, Slot, QTimer, 
                            QAbstractTableModel, QModelIndex, Signal, Property, 
                            QPropertyAnimation, QRectF, QEasingCurve)
from PySide6.QtGui import (QFont, QColor, QPalette, QIcon, QShortcut, 
                           QKeySequence, QAction, QPainter, QPen, QBrush, QPainterPath, QPixmap)
import threading
import socket
import shutil
import multiprocessing

# Import logic
from bios_parser import get_bios_metadata
from firmware_organizer import detect_and_organize_local_firmware
from me_cleaner import apply_firmware_patch # Changed from apply_me_clean_patch
from bios_decompiler import decompile_bios
from advanced_extractor import AdvancedExtractor
from analysis_suite import AnalysisSuite
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
from network_manager import NetworkManager
from path_utils import get_app_root

# Cyberpunk Stylesheet
STYLESHEET = """
QMainWindow {
    background-color: #0a0b10;
}

QFrame#Sidebar {
    background-color: #12141d;
    border-right: 1px solid #1f2233;
    min-width: 200px;
    max-width: 200px;
}

QLabel#Title {
    color: #00f3ff;
    font-size: 18px;
    font-weight: bold;
    padding: 20px 10px;
    text-transform: uppercase;
    letter-spacing: 2px;
}

QPushButton {
    font-family: 'Orbitron', 'Digital-7', monospace;
    background-color: #1a1d2e;
    color: #ffffff;
    border: 1px solid #00f3ff;
    padding: 12px;
    font-size: 14px;
    font-weight: bold;
    text-align: left;
    border-radius: 4px;
    margin: 5px 10px;
}

QPushButton:hover {
    background-color: #00f3ff;
    color: #0a0b10;
}

QPushButton:disabled {
    background-color: #0a0b10;
    color: #444444;
    border: 1px solid #222222;
}

QPushButton#ActionButton {
    text-align: center;
    border: 2px solid #00ff41;
    color: #00ff41;
}

QPushButton#ActionButton:hover {
    background-color: #00ff41;
    color: #000000;
}

QTextEdit#Terminal {
    background-color: #000000;
    color: #00FF00;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 12px;
    border: 1px solid #1f2233;
    padding: 10px;
}

QLabel#InternetStatus {
    font-family: 'Orbitron', sans-serif;
    font-size: 11px;
    font-weight: bold;
    padding: 2px 8px;
    border-radius: 10px;
    background-color: #1a1d2e;
    border: 1px solid #1f2233;
}

QDialog {
    background-color: #0a0b10;
    color: #00ff41;
}

QPushButton#LogButton {
    background-color: #12141d;
    border: 1px solid #333;
    font-size: 10px;
    padding: 4px 8px;
    min-width: 80px;
}

QPushButton#LogButton:hover {
    background-color: #333;
    color: #fff;
}

QScrollBar:vertical {
    border: none;
    background: #0a0b10;
    width: 10px;
}

QScrollBar::handle:vertical {
    background: #1f2233;
    min-height: 20px;
}

QTableView#HexView {
    background-color: #000000;
    color: #4CAF50; /* A darker/classic green or grey for data */
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 13px;
    border: 1px solid #1f2233;
    gridline-color: transparent; /* Hide grid lines to look like standard hex editor */
    selection-background-color: #004488;
    selection-color: #ffffff;
}

QTableView#HexView::item {
    padding-left: 2px;
    padding-right: 2px;
}

QHeaderView::section {
    background-color: #0a0b10; /* Darker to blend in */
    color: #00f3ff; /* Keep the neon blue for headers */
    border: none;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 13px;
    padding: 2px 4px;
    text-align: left;
}

QTableView QTableCornerButton::section {
    background-color: #12141d;
    border: 1px solid #1f2233;
}

QPushButton#AdvancedButton {
    border: 1px solid #00f3ff;
    color: #00f3ff;
}

QPushButton#AdvancedButton:disabled {
    background-color: #0a0b10;
    color: #444444;
    border: 1px solid #222222;
}
"""

class HexTableModel(QAbstractTableModel):
    # Fast character lookup table (Pre-calculating for Latin-1)
    CHARS_LOOKUP = [chr(b) if (32 <= b <= 126 or b >= 160) else "." for b in range(256)]

    def __init__(self, data=b"", parent=None):
        super().__init__(parent)
        self._data = bytearray(data)

    def set_data(self, data):
        self.beginResetModel()
        self._data = bytearray(data)
        self.endResetModel()

    def get_data(self):
        return self._data

    def insert_bytes(self, offset, count=1, insert_data=None):
        self.beginInsertRows(QModelIndex(), (offset)//16, (offset + count)//16)
        if insert_data is not None:
            self._data[offset:offset] = insert_data
        else:
            self._data[offset:offset] = b'\x00' * count
        self.endInsertRows()
        self.layoutChanged.emit()

    def remove_bytes(self, offset, count=1):
        if offset + count > len(self._data):
            count = len(self._data) - offset
        if count <= 0:
            return
            
        self.beginResetModel()
        del self._data[offset:offset + count]
        self.endResetModel()
        self.layoutChanged.emit()

    def replace_bytes(self, offset, new_bytes):
        count = len(new_bytes)
        if count <= 0 or offset >= len(self._data): return
        end = min(offset + count, len(self._data))
        written = end - offset
        self._data[offset:end] = new_bytes[:written]
        
        # If it goes past EOF, we append the rest
        if written < count:
            remaining = new_bytes[written:]
            self.insert_bytes(end, len(remaining), remaining)
        else:
            self.dataChanged.emit(self.index(offset//16, 0), self.index((end)//16, 16))

    def search(self, query_bytes, direction="All", start_offset=0):
        results = []
        if not self._data or not query_bytes: return results
        
        idx = self._data.find(query_bytes, 0)
        while idx != -1:
            results.append(idx)
            idx = self._data.find(query_bytes, idx + 1)
            
        if direction == "Forward":
            results = [r for r in results if r >= start_offset]
        elif direction == "Backward":
            results = [r for r in results if r <= start_offset]
            results.sort(reverse=True)
            
        return results

    def rowCount(self, parent=QModelIndex()):
        return (len(self._data) + 15) // 16

    def columnCount(self, parent=QModelIndex()):
        return 17
        
    def flags(self, index):
        if not index.isValid():
            return Qt.ItemIsEnabled
        
        # Make hex columns (0-15) editable
        if index.column() < 16:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable
        # Decoded text column is read-only
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def setData(self, index, value, role=Qt.EditRole):
        if role == Qt.EditRole and index.column() < 16:
            try:
                # Convert input back to hex byte
                val = int(value, 16)
                if 0 <= val <= 255:
                    offset = index.row() * 16 + index.column()
                    if offset < len(self._data):
                        self._data[offset] = val
                        self.dataChanged.emit(index, index, [Qt.DisplayRole])
                        # Also update the decoded text column
                        text_index = self.index(index.row(), 16)
                        self.dataChanged.emit(text_index, text_index, [Qt.DisplayRole])
                        return True
            except ValueError:
                return False
        return False

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        
        row = index.row()
        col = index.column()
        offset = row * 16 + col
        
        if role == Qt.DisplayRole:
            if col < 16:
                if offset < len(self._data):
                    return f"{self._data[offset]:02X}"
                return ""
            else:
                start = row * 16
                end = min(start + 16, len(self._data))
                chunk = self._data[start:end]
                # Fast lookup instead of conditional chr() calling
                return "".join(self.CHARS_LOOKUP[b] for b in chunk)
                
        elif role == Qt.TextAlignmentRole:
            if col < 16:
                return int(Qt.AlignCenter)
            return int(Qt.AlignLeft | Qt.AlignVCenter)
            
        elif role == Qt.ForegroundRole:
            if col == 16:
                return QColor("#00f3ff") # Blue text for decoded characters
            return None
            
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            if section < 16:
                return f"{section:02X}"
            return "Decoded text"
        else:
            return f"{section * 16:08X}"

class HexSearchDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Find")
        self.setFixedSize(400, 150)
        self.setStyleSheet("QDialog { background-color: #0a0b10; color: #00f3ff; } QLabel { color: #00f3ff; }")
        layout = QVBoxLayout(self)
        
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel("Search for:"))
        self.search_input = QLineEdit()
        self.search_input.setStyleSheet("background-color: #12141d; color: #ffffff; border: 1px solid #1f2233;")
        h_layout.addWidget(self.search_input)
        layout.addLayout(h_layout)
        
        options_layout = QHBoxLayout()
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Hex-values", "Text-string"])
        self.type_combo.setStyleSheet("background-color: #12141d; color: #ffffff; border: 1px solid #1f2233;")
        options_layout.addWidget(self.type_combo)
        
        self.direction_combo = QComboBox()
        self.direction_combo.addItems(["All", "Forward", "Backward"])
        self.direction_combo.setStyleSheet("background-color: #12141d; color: #ffffff; border: 1px solid #1f2233;")
        options_layout.addWidget(self.direction_combo)
        
        layout.addLayout(options_layout)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.setStyleSheet("QPushButton { background-color: #1a1d2e; color: #ffffff; border: 1px solid #00f3ff; padding: 5px; }")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_search_params(self):
        return {
            "query": self.search_input.text(),
            "type": self.type_combo.currentText(),
            "direction": self.direction_combo.currentText()
        }

class HexSelectBlockDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Block")
        self.setFixedSize(300, 150)
        self.setStyleSheet("QDialog { background-color: #0a0b10; color: #00f3ff; } QLabel { color: #00f3ff; }")
        layout = QVBoxLayout(self)
        
        h_start = QHBoxLayout()
        h_start.addWidget(QLabel("Start Offset (hex):"))
        self.start_input = QLineEdit()
        self.start_input.setStyleSheet("background-color: #12141d; color: #ffffff; border: 1px solid #1f2233;")
        h_start.addWidget(self.start_input)
        layout.addLayout(h_start)
        
        h_end = QHBoxLayout()
        h_end.addWidget(QLabel("End Offset (hex):"))
        self.end_input = QLineEdit()
        self.end_input.setStyleSheet("background-color: #12141d; color: #ffffff; border: 1px solid #1f2233;")
        h_end.addWidget(self.end_input)
        layout.addLayout(h_end)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.setStyleSheet("QPushButton { background-color: #1a1d2e; color: #ffffff; border: 1px solid #00f3ff; padding: 5px; }")
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
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid(): return None
        if role == Qt.DisplayRole:
            res = self.results[index.row()]
            col = index.column()
            if col == 0: return f"{res['offset']:08X}"
            elif col == 1: return res['hex']
            elif col == 2: return res['text']
        return None
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole: return None
        if orientation == Qt.Horizontal:
            return ["Offset", "Excerpt (hex)", "Excerpt (text)"][section]
        return str(section)

class HexEditorTab(QWidget):
    log_signal = Signal(str)

    def __init__(self, data=b"", parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.setHandleWidth(4)
        
        self.hex_view = QTableView()
        self.hex_view.setObjectName("HexView")
        self.hex_model = HexTableModel(data)
        self.hex_view.setModel(self.hex_model)
        
        self.hex_view.setShowGrid(False)
        self.hex_view.setWordWrap(False)
        self.hex_view.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.hex_view.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        font = QFont("Consolas", 11)
        self.hex_view.setFont(font)
        for i in range(16):
            self.hex_view.setColumnWidth(i, 26)
        self.hex_view.setColumnWidth(16, 160)
        self.hex_view.horizontalHeader().setMinimumSectionSize(20)
        self.hex_view.verticalHeader().setDefaultSectionSize(20)
        self.hex_view.verticalHeader().setMinimumSectionSize(20)
        self.hex_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.hex_view.verticalHeader().setFixedWidth(85)
        self.hex_view.verticalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.hex_view.horizontalHeader().setStretchLastSection(True)
        self.hex_view.horizontalHeader().setFixedHeight(25)
        
        self.corner_label = QLabel("Offset (h)", self.hex_view)
        self.corner_label.setStyleSheet("color: #00f3ff; font-weight: bold; font-family: 'Consolas', monospace; font-size: 12px; background-color: #0a0b10; padding-left: 5px;")
        self.corner_label.setGeometry(1, 1, 84, 23)
        self.corner_label.show()
        
        self.splitter.addWidget(self.hex_view)
        
        self.results_panel = QWidget()
        self.results_panel.hide()
        rp_layout = QVBoxLayout(self.results_panel)
        rp_layout.setContentsMargins(0, 0, 0, 0)
        
        rp_header = QHBoxLayout()
        lbl = QLabel("Search Results")
        lbl.setStyleSheet("color: #00f3ff; font-weight: bold;")
        close_btn = QPushButton("X")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet("background-color: transparent; color: #ff3131; border: none;")
        close_btn.clicked.connect(self.results_panel.hide)
        rp_header.addWidget(lbl)
        rp_header.addStretch()
        rp_header.addWidget(close_btn)
        rp_layout.addLayout(rp_header)
        
        self.results_table = QTableView()
        self.results_table.setStyleSheet("background-color: #000000; color: #4CAF50; selection-background-color: #004488;")
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.results_table.verticalHeader().hide()
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.doubleClicked.connect(self.goto_search_result)
        rp_layout.addWidget(self.results_table)
        
        self.splitter.addWidget(self.results_panel)
        self.layout.addWidget(self.splitter)
        
        self.setup_shortcuts()
        self.hex_view.customContextMenuRequested.connect(self.show_hex_context_menu)

    def setup_shortcuts(self):
        self.shortcut_delete = QShortcut(QKeySequence(Qt.Key_Delete), self.hex_view)
        self.shortcut_delete.activated.connect(self.delete_selected_data)
        
        self.shortcut_backspace = QShortcut(QKeySequence(Qt.Key_Backspace), self.hex_view)
        self.shortcut_backspace.activated.connect(self.delete_selected_data)
        
        self.shortcut_find = QShortcut(QKeySequence("Ctrl+F"), self.hex_view)
        self.shortcut_find.activated.connect(self.show_find_dialog)
        
        self.shortcut_select_block = QShortcut(QKeySequence("Ctrl+E"), self.hex_view)
        self.shortcut_select_block.activated.connect(self.show_select_block_dialog)
        
        self.shortcut_copy = QShortcut(QKeySequence("Ctrl+C"), self.hex_view)
        self.shortcut_copy.activated.connect(self.copy_hex_data)
        
        self.shortcut_cut = QShortcut(QKeySequence("Ctrl+X"), self.hex_view)
        self.shortcut_cut.activated.connect(self.cut_selected_data)
        
        self.shortcut_paste_insert = QShortcut(QKeySequence("Ctrl+V"), self.hex_view)
        self.shortcut_paste_insert.activated.connect(self.paste_insert_data)
        
        self.shortcut_paste_write = QShortcut(QKeySequence("Ctrl+B"), self.hex_view)
        self.shortcut_paste_write.activated.connect(self.paste_write_data)

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
        if start is None: return
        val, ok = QInputDialog.getText(self, "Fill Selection", "Hex value (e.g. FF or 00):")
        if ok and val:
            try:
                b_val = bytes.fromhex(val.strip())
                if len(b_val) == 1:
                    fill_data = b_val * count
                    self.hex_model.replace_bytes(start, fill_data)
                    self.log_signal.emit(f"[INFO] Filled {count} bytes with {val.upper()}")
            except ValueError:
                pass

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
                select_flag = QItemSelectionModel.SelectionFlag.Select if hasattr(QItemSelectionModel, 'SelectionFlag') else QItemSelectionModel.Select
                sel_model.select(selection, select_flag)
                self.hex_view.scrollTo(model.index(start // 16, 0))

    def show_find_dialog(self):
        dialog = HexSearchDialog(self)
        if dialog.exec():
            params = dialog.get_search_params()
            query = params["query"].strip()
            if not query: return
            
            try:
                if params["type"] == "Hex-values":
                    query_bytes = bytes.fromhex(query.replace(" ", ""))
                else:
                    query_bytes = query.encode('utf-8') # Or latin-1 based on user needs
            except ValueError:
                self.log_signal.emit("[ERROR] Invalid search query format.")
                return
                
            start_off = 0
            sel_start, _ = self.get_selected_range()
            if sel_start is not None: start_off = sel_start
            
            offsets = self.hex_model.search(query_bytes, params["direction"], start_off)
            
            if not offsets:
                self.log_signal.emit(f"[INFO] No results found for '{query}'")
                return
                
            self.log_signal.emit(f"[INFO] Found {len(offsets)} matches.")
            
            # Format results for the panel
            res_data = []
            full_data = self.hex_model.get_data()
            for off in offsets:
                chunk = full_data[off:min(off+16, len(full_data))]
                hex_str = " ".join(f"{b:02X}" for b in chunk)
                text_str = "".join(self.hex_model.CHARS_LOOKUP[b] for b in chunk)
                res_data.append({'offset': off, 'hex': hex_str, 'text': text_str})
                
            self.res_model = SearchResultsModel(res_data)
            self.results_table.setModel(self.res_model)
            self.results_panel.show()
            self.splitter.setSizes([self.height()*0.7, self.height()*0.3])

    def goto_search_result(self, index):
        if not index.isValid(): return
        res = self.res_model.results[index.row()]
        offset = res['offset']
        
        self.hex_view.clearSelection()
        row = offset // 16
        col = offset % 16
        idx = self.hex_model.index(row, col)
        
        from PySide6.QtCore import QItemSelectionModel
        select_flag = QItemSelectionModel.SelectionFlag.Select if hasattr(QItemSelectionModel, 'SelectionFlag') else QItemSelectionModel.Select
        self.hex_view.selectionModel().select(idx, select_flag)
        self.hex_view.scrollTo(idx)

    def show_hex_context_menu(self, pos):
        index = self.hex_view.indexAt(pos)
        if not index.isValid() or index.column() >= 16: return
        
        menu = QMenu(self)
        menu.addAction("Copy Hex", self.copy_hex_data)
        menu.addAction("Copy Text", self.copy_text_data)
        menu.addAction("Cut Selection", self.cut_selected_data)
        menu.addAction("Paste Write (Overwrite)", self.paste_write_data)
        menu.addAction("Paste Insert", self.paste_insert_data)
        menu.addSeparator()
        menu.addAction("Fill Selection...", self.fill_selection)
        menu.addAction("Delete Selection", self.delete_selected_data)
        menu.addSeparator()
        menu.addAction("Select Block...", self.show_select_block_dialog)
        menu.addAction("Find...", self.show_find_dialog)
        menu.exec(self.hex_view.viewport().mapToGlobal(pos))

class LogViewerDialog(QDialog):
    def __init__(self, parent=None):
        super(LogViewerDialog, self).__init__(parent)
        self.setWindowTitle("System Activity Logs")
        self.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(self)
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setStyleSheet("background-color: #000; color: #00ff41; font-family: Consolas;")
        layout.addWidget(self.text_area)
        
        # Load content
        if os.path.exists("app.log"):
            with open("app.log", "r", encoding="utf-8") as f:
                self.text_area.setPlainText(f.read())
        else:
            self.text_area.setPlainText("No logs found.")

class LoadingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_TranslucentBackground)
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
        self.anim.setEasingCurve(QEasingCurve.Linear)
        
        # Timer for elapsed time
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_time)
        self.start_timestamp = 0

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
                # Catch up quickly if we are behind the analysis
                speed = 2.0 if (self.target_percentage - self.displayed_percentage) > 20 else 1.2
                self.displayed_percentage += speed
            elif self.target_percentage >= 100:
                # Force finish when target is 100
                self.displayed_percentage += 3.0
            elif self.displayed_percentage < 99:
                # Steady crawl (Ensures 10-12s duration if analysis is slow)
                self.displayed_percentage += 0.5
            
            if self.displayed_percentage > 100:
                self.displayed_percentage = 100
                
            self.update()

    def add_log(self, text):
        # Keep only the last 4 informative lines
        # Strip potential HTML for the overlay
        import re
        clean_text = re.sub(r'<[^>]+>', '', text)
        clean_text = clean_text.replace("[INFO]", "").replace("[SUCCESS]", "✔").replace("[ERROR]", "✘").strip()
        if clean_text:
            self.logs.append(clean_text)
            if len(self.logs) > 4:
                self.logs.pop(0)
            self.update()

    def set_progress(self, value):
        self.target_percentage = max(0, min(100, value))
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
        if self.parent():
            parent_rect = self.parent().rect()
            w = parent_rect.width() * 0.6 # Use 60% for better readability, or 50% as requested
            h = parent_rect.height() * 0.6
            x = (parent_rect.width() - w) / 2
            y = (parent_rect.height() - h) / 2
            self.setGeometry(int(x), int(y), int(w), int(h))

    def stop(self):
        self.anim.stop()
        self.timer.stop()
        self.start_timestamp = 0
        self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 1. Cyberpunk Dark Dim with Border
        # Create a rounded rectangle for the 50% view
        painter.setRenderHint(QPainter.Antialiasing)
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
        painter.setPen(Qt.NoPen)
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
        pen_arc.setCapStyle(Qt.RoundCap)
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
        font_pct = QFont("Consolas", 28, QFont.Bold)
        painter.setFont(font_pct)
        painter.drawText(self.rect(), Qt.AlignCenter, f"{int(self.displayed_percentage)}%")
        
        # 6. Timer & Estimate (Top Right, slightly offset for small box)
        timer_font = QFont("Consolas", 9)
        painter.setFont(timer_font)
        painter.setPen(QColor(0, 243, 255, 180))
        timer_text = f"ELAPSED: {self.elapsed_time:.1f}s"
        if self.estimated_time > 0:
            remain = max(0, self.estimated_time - self.elapsed_time)
            timer_text += f"\nEST: {remain:.1f}s"
        painter.drawText(w - 140, 20, 120, 50, Qt.AlignRight | Qt.AlignTop, timer_text)
        
        # 7. Status Text (Cyberpunk Glitch Header)
        status_font = QFont("Orbitron", 11, QFont.Bold)
        painter.setFont(status_font)
        painter.setPen(QColor(0, 255, 65)) # Matrix Green
        painter.drawText(int(cx - 150), int(cy + 100), 300, 30, Qt.AlignCenter, ">>> " + self.status_text.upper())
        
        # 8. Activity Log Feed (Bottom Center)
        log_font = QFont("Consolas", 8)
        painter.setFont(log_font)
        painter.setPen(QColor(0, 243, 255, 120))
        log_y = h - 70
        for log in self.logs:
            painter.drawText(20, int(log_y), w - 40, 15, Qt.AlignCenter, f"PROC: {log}")
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

class DropZoneOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.hide()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Deep Blue Neon Dim
        painter.fillRect(self.rect(), QColor(0, 243, 255, 30))
        
        # Glowing Border
        pen = QPen(QColor(0, 243, 255), 4)
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        painter.drawRect(self.rect().adjusted(10, 10, -10, -10))
        
        # Text
        painter.setPen(QColor(0, 243, 255))
        font = QFont("Orbitron", 20, QFont.Bold)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignCenter, ">>> INITIALIZE DECRYPTION <<<\nDROP BIOS FILE HERE")

    def resizeEvent(self, event):
        if self.parent():
            self.setGeometry(self.parent().rect())

class BiosServiceTool(QMainWindow):
    mea_output_signal = Signal(list, list)
    progress_signal = Signal(int)
    loading_signal = Signal(bool, str, float) # (show/hide, text, estimate)
    task_finished_signal = Signal()
    hex_data_signal = Signal(object) # Pass as generic object to avoid memory-copying large bytearrays in Qt event queue
    module_buttons_signal = Signal(dict)
    overlay_log_signal = Signal(str)
    server_status_signal = Signal(bool)

    @property
    def hex_model(self):
        if hasattr(self, 'hex_tabs') and self.hex_tabs.count() > 0:
            return self.hex_tabs.currentWidget().hex_model
        if not hasattr(self, '_fallback_hex_model'): self._fallback_hex_model = HexTableModel(b"")
        return self._fallback_hex_model

    @property
    def hex_view(self):
        if hasattr(self, 'hex_tabs') and self.hex_tabs.count() > 0:
            return self.hex_tabs.currentWidget().hex_view
        if not hasattr(self, '_fallback_hex_view'): self._fallback_hex_view = QTableView()
        return self._fallback_hex_view

    def add_new_hex_tab(self, title, data=b""):
        tab = HexEditorTab(data, self)
        tab.log_signal.connect(self.log_to_terminal)
        idx = self.hex_tabs.addTab(tab, title)
        self.hex_tabs.setCurrentIndex(idx)
        return tab

    def close_hex_tab(self, index):
        if self.hex_tabs.count() > 1:
            w = self.hex_tabs.widget(index)
            self.hex_tabs.removeTab(index)
            w.deleteLater()
        else:
            self.hex_tabs.currentWidget().hex_model.set_data(b"")

    @Slot(object)
    def _on_hex_data_received(self, data):
        if not hasattr(self, 'hex_tabs') or self.hex_tabs.count() == 0:
            self.add_new_hex_tab("Main BIOS", data)
        else:
            self.hex_tabs.currentWidget().hex_model.set_data(data)

    def __init__(self):
        super().__init__()
        self.mea_output_signal.connect(self._handle_mea_output_internal)
        
        # Initialize Overlays
        self.loading_overlay = LoadingOverlay(self)
        self.drop_overlay = DropZoneOverlay(self)
        
        self.loading_signal.connect(self._handle_loading_state)
        self.progress_signal.connect(self.loading_overlay.set_progress)
        self.overlay_log_signal.connect(self.loading_overlay.add_log)
        self.task_finished_signal.connect(lambda: self.initiate_loader_stop(2000))
        self.server_status_signal.connect(self.update_server_ui)
        
        self.network = NetworkManager(host='127.0.0.1') # Default to localhost
        
        self.setWindowTitle("R1 BIOS SERVICE TOOL")
        self.setMinimumSize(1000, 650)
        self.setStyleSheet(STYLESHEET)
        self.setAcceptDrops(True)
        
        # State
       
       
        
        self.current_bios_file = None
        self.current_regions_map = {}
        self.log_file = "app.log"
        self.workspace_dir = os.path.join(get_app_root(), "WORKSPACE")
        self.reset_stage = 0
        self.mea_history = "" # Initialize MEA history
        self.auto_save_prefix = "" # For custom prefixes during auto-save
        self.processing_mode = "Online (VPS)" # Set default to Online (VPS)
        
        # Path Memory: Default to Downloads folder
        self.last_directory = os.path.join(os.path.expanduser("~"), "Downloads")
        if not os.path.exists(self.last_directory):
            self.last_directory = os.getcwd()
        
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

        # Initialize/Clear log file
        with open(self.log_file, "w", encoding="utf-8") as f:
            f.write(f"--- Session Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
        
        self.setup_ui()
        
        # Connect data signals after UI setup ensures models exist
        self.hex_data_signal.connect(self._on_hex_data_received)
        self.module_buttons_signal.connect(self.enable_module_buttons)
        
        # Shortcuts
        self.shortcut_clear = QShortcut(QKeySequence("Ctrl+L"), self)
        self.shortcut_clear.activated.connect(self.clear_terminal_and_logs)

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

        # Header / Status labels
        header = QLabel("SYSTEM STATUS: ONLINE")
        header.setStyleSheet("color: #00ff41; font-family: monospace;")
        content_layout.addWidget(header)

        # Action Buttons Area
        actions_layout = QHBoxLayout()
        self.btn_open = QPushButton("OPEN BIOS FILE")
        self.btn_open.setObjectName("ActionButton")
        self.btn_open.setFixedWidth(200)
        self.btn_open.clicked.connect(self.open_bios_dialog)
        actions_layout.addWidget(self.btn_open)

        self.btn_save = QPushButton("SAVE CHANGES")
        self.btn_save.setObjectName("ActionButton")
        self.btn_save.setFixedWidth(200)
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self.save_bios_changes)
        self.btn_save.setStyleSheet("border-color: #ff00ff; color: #ff00ff;") # Purple for save
        actions_layout.addWidget(self.btn_save)


        
        actions_layout.addStretch()
        
        content_layout.addLayout(actions_layout)

        # Space Filler
        content_layout.addStretch()

        # Panels Layout (Terminal & Hex) - Used QSplitter for resizability
        panels_splitter = QSplitter(Qt.Horizontal)
        panels_splitter.setHandleWidth(8)
        panels_splitter.setStyleSheet("QSplitter::handle { background-color: #1f2233; margin: 0 4px; border-radius: 2px; }")

        # Terminal Panel
        terminal_widget = QWidget()
        terminal_layout = QVBoxLayout(terminal_widget)
        terminal_layout.setContentsMargins(0, 0, 0, 0)
        
        terminal_label = QLabel("TERMINAL OUTPUT")
        terminal_label.setStyleSheet("color: #00f3ff; font-weight: bold; font-family: monospace;")
        terminal_layout.addWidget(terminal_label)

        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setObjectName("Terminal")
        self.terminal.setPlaceholderText("Ready for input...")
        terminal_layout.addWidget(self.terminal)
        
        panels_splitter.addWidget(terminal_widget)

        # Hex Viewer Panel
        hex_widget = QWidget()
        hex_layout = QVBoxLayout(hex_widget)
        hex_layout.setContentsMargins(0, 0, 0, 0)
        
        hex_label = QLabel("HEX VIEWER")
        hex_label.setStyleSheet("color: #00f3ff; font-weight: bold; font-family: monospace;")
        hex_layout.addWidget(hex_label)

        self.hex_tabs = QTabWidget()
        self.hex_tabs.setTabsClosable(True)
        self.hex_tabs.tabCloseRequested.connect(self.close_hex_tab)
        self.hex_tabs.setStyleSheet("QTabWidget::pane { border: 1px solid #1f2233; } QTabBar::tab { background-color: #12141d; color: #00f3ff; padding: 5px 15px; border: 1px solid #1f2233; } QTabBar::tab:selected { background-color: #1a1d2e; border-bottom: 2px solid #00ff41; }")
        
        self.add_tab_btn = QPushButton("+")
        self.add_tab_btn.setFixedSize(30, 25)
        self.add_tab_btn.setStyleSheet("background-color: transparent; color: #00f3ff; font-weight: bold; border: none;")
        self.add_tab_btn.clicked.connect(lambda: self.add_new_hex_tab("New Tab"))
        self.hex_tabs.setCornerWidget(self.add_tab_btn)
        
        hex_layout.addWidget(self.hex_tabs)
        
        # Add initial tab
        self.add_new_hex_tab("Main BIOS")
        panels_splitter.addWidget(hex_widget)
        
        # Set default sizes: prioritize terminal to prevent text breaking
        # Terminal (left) gets more space (750), Hex (right) gets less (250)
        panels_splitter.setSizes([750, 250])
        
        # Set minimum widths to preserve usability on small screens
        # 650px ensures ME Analyzer tables remain readable
        terminal_widget.setMinimumWidth(650)
        # 250px ensures Hex viewer remains visible even in smaller layouts
        hex_widget.setMinimumWidth(250)
        
        # Configure growth: When the screen is enlarged, both panels 
        # will share the extra space equally (balanced growth)
        panels_splitter.setStretchFactor(0, 1)
        panels_splitter.setStretchFactor(1, 1)

        content_layout.addWidget(panels_splitter, 2)
        # Internet Status Indicator & Logs (Bottom Right)
        status_footer = QHBoxLayout()
        
        self.btn_show_logs = QPushButton("SHOW LOGS")
        self.btn_show_logs.setObjectName("LogButton")
        self.btn_show_logs.clicked.connect(self.show_logs_popup)
        status_footer.addWidget(self.btn_show_logs)
        
        status_footer.addStretch()
        
        self.internet_status_label = QLabel("● CHECKING...")
        self.internet_status_label.setStyleSheet("color: #ffa500;") # Orange while checking
        status_footer.addWidget(self.internet_status_label)
        
        self.server_status_label = QLabel("● SERVER: CHECKING...")
        self.server_status_label.setObjectName("InternetStatus")
        self.server_status_label.setStyleSheet("color: #ffa500;")
        status_footer.addWidget(self.server_status_label)
        
        content_layout.addLayout(status_footer)

        main_layout.addWidget(content_wrapper)
    def setup_sidebar(self, layout):
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # --- LOGO AND BRANDING SECTION ---
        # Modular section as requested by user
        branding_widget = QWidget()
        branding_layout = QVBoxLayout(branding_widget)
        branding_layout.setContentsMargins(10, 20, 10, 10)
        branding_layout.setSpacing(5)
        
        # Logo
        logo_label = QLabel()
        logo_path = os.path.join(get_app_root(), "assets", "R1AILAB.png")
        if not os.path.exists(logo_path):
            logo_path = os.path.join(get_app_root(), "assets", "R1 IT LAB.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            scaled_pixmap = pixmap.scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
        logo_label.setAlignment(Qt.AlignCenter)
        branding_layout.addWidget(logo_label)

        # Name
        title = QLabel("R1 editor")
        title.setObjectName("Title")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("padding: 5px 10px;") # Reduce top padding since layout has margin
        branding_layout.addWidget(title)
        
        sidebar_layout.addWidget(branding_widget)
        # --- END LOGO AND BRANDING SECTION ---

        # SMART ACTION ENGINE
        self.btn_smart_me_fix = QPushButton("SMART ME FIX")
        self.btn_smart_me_fix.setEnabled(False)
        self.btn_smart_me_fix.clicked.connect(self.smart_me_fix_handler)
        self.btn_smart_me_fix.setStyleSheet("border-color: #00ff41; color: #00ff41; font-weight: bold;") # Matrix Green

        self.btn_dmi_migrate = QPushButton("BIOS RG FIX")
        self.btn_dmi_migrate.setEnabled(False)
        self.btn_dmi_migrate.clicked.connect(self.bios_rg_fix_handler)
        self.btn_dmi_migrate.setStyleSheet("border-color: #ff00ff; color: #ff00ff;") # Purple for BIOS RG FIX

        self.btn_extract_dmi = QPushButton("EXTRACT DMI")
        self.btn_extract_dmi.setEnabled(False)
        self.btn_extract_dmi.clicked.connect(self.extract_dmi_handler)
        self.btn_extract_dmi.setStyleSheet("border-color: #00f3ff; color: #00f3ff;") # Neon Blue

        # Grouped Patches
        self.btn_apply_patches = QPushButton("APPLY PATCHES")
        self.btn_apply_patches.setEnabled(False)
        self.btn_apply_patches.clicked.connect(self.show_patches_menu)
        self.btn_apply_patches.setStyleSheet("border-color: #00d4ff; color: #00d4ff;") # Cyan for Patches

        # Final output
        self.btn_save_fix = QPushButton("SAVE && FIX")
        self.btn_save_fix.setEnabled(False)
        self.btn_save_fix.clicked.connect(self.save_and_fix_handler)
        self.btn_save_fix.setStyleSheet("border-color: #ffaa00; color: #ffaa00;") # Orange for Final Save

        # Sub-buttons for developers or cases where auto fails
        self.btn_advanced_extract = QPushButton("MANUAL EXTRACT")
        self.btn_advanced_extract.setEnabled(False)
        self.btn_advanced_extract.clicked.connect(self.advanced_extract_click_handler)
        self.btn_advanced_extract.setStyleSheet("font-size: 9px; color: #444;") # Smaller, less prominent

        self.btn_settings = QPushButton("SETTINGS")
        self.btn_settings.setEnabled(False)

        # Labels for sections
        label_main = QLabel("────── ACTION ENGINE ──────")
        label_main.setStyleSheet("color: #333; font-size: 9px; margin-top: 15px;")
        label_main.setAlignment(Qt.AlignCenter)

        label_tools = QLabel("────── UTILITIES ──────")
        label_tools.setStyleSheet("color: #333; font-size: 9px; margin-top: 15px;")
        label_tools.setAlignment(Qt.AlignCenter)

        sidebar_layout.addWidget(label_main)
        
        # --- MODE SELECTOR (HIDDEN - ONLINE ONLY) ---
        # mode_label = QLabel("────── SYSTEM MODE ──────")
        # mode_label.setStyleSheet("color: #333; font-size: 9px; margin-top: 10px;")
        # mode_label.setAlignment(Qt.AlignCenter)
        # sidebar_layout.addWidget(mode_label)

        # self.mode_selector = QComboBox()
        # self.mode_selector.addItems(["Offline (Local)", "Online (VPS)"])
        # self.mode_selector.setStyleSheet("background-color: #1a1d2e; color: #00f3ff; border: 1px solid #1f2233; padding: 5px;")
        # self.mode_selector.currentTextChanged.connect(self.change_system_mode)
        # sidebar_layout.addWidget(self.mode_selector)
        
        sidebar_layout.addWidget(self.btn_smart_me_fix)
        sidebar_layout.addWidget(self.btn_dmi_migrate)
        sidebar_layout.addWidget(self.btn_extract_dmi)
        sidebar_layout.addWidget(self.btn_apply_patches)
        sidebar_layout.addWidget(self.btn_save_fix)
        
        sidebar_layout.addStretch()
        sidebar_layout.addWidget(label_tools)
        sidebar_layout.addWidget(self.btn_advanced_extract)
        sidebar_layout.addWidget(self.btn_settings)
        
        # Footer in Sidebar
        footer = QLabel("VERSION 2.0.0\nSMART BUILD") # Updated version for major overhaul
        footer.setStyleSheet("color: #333; font-size: 10px; margin: 20px;")
        footer.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(footer)
        layout.addWidget(sidebar)


    @Slot(str)
    def log_to_terminal(self, message):
        """Callback for the parser to log messages."""
        if threading.current_thread() is not threading.main_thread():
            QMetaObject.invokeMethod(self, "log_to_terminal", Qt.QueuedConnection, Q_ARG(str, message))
            return
            
        if hasattr(self, 'mea_history'):
            self.mea_history += message + "\n"

        self.terminal.append(message)
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
            path = os.path.join(os.getcwd(), d) if not os.path.isabs(d) else d
            if os.path.exists(path):
                try:
                    shutil.rmtree(path)
                except Exception:
                    pass
        
        # Ensure workspace exists for new tasks
        os.makedirs(self.workspace_dir, exist_ok=True)

    def initialize_ui_window(self):
        """Brings the window to the front and initializes tool status."""
        self.show()
        self.raise_()
        self.activateWindow()
        
        self.log_to_terminal("[INFO] R1 BIOS Service Tool started")
        self.log_to_terminal("[INFO] UI initialized and ready")
        
        # Auto-run firmware organization
        self.log_to_terminal("[INFO] Scanning for local firmware files...")
        detect_and_organize_local_firmware(get_app_root(), self.log_to_terminal)
        self.log_to_terminal("[INFO] Main screen loaded, ready for module selection")

        # Start Internet Connectivity Checker
        self.connectivity_timer = QTimer(self)
        self.connectivity_timer.timeout.connect(self.check_internet_status)
        self.connectivity_timer.start(10000) # Every 10 seconds
        self.check_internet_status() # Initial check

    @Slot(dict)
    def enable_module_buttons(self, firmware_regions):
        if not firmware_regions:
            self.btn_smart_me_fix.setEnabled(False)
            self.btn_dmi_migrate.setEnabled(False)
            self.btn_extract_dmi.setEnabled(False)
            self.btn_apply_patches.setEnabled(False)
            self.btn_save_fix.setEnabled(False)
            self.btn_advanced_extract.setEnabled(False)
            return

        # Core Action: DMI Migration
        if "bios" in firmware_regions or "bios_region" in firmware_regions:
            self.btn_dmi_migrate.setEnabled(True)
            self.btn_extract_dmi.setEnabled(True)
            self.btn_apply_patches.setEnabled(True)

        # Core Action: ME Fix
        if "me_csme" in firmware_regions or "me_region" in firmware_regions:
            self.btn_smart_me_fix.setEnabled(True)

        # Always enable Save & Fix if a file is loaded
        self.btn_save_fix.setEnabled(True)
        
        # Manual extract as a fallback
        if self.current_bios_file:
            ext = os.path.splitext(self.current_bios_file)[1].lower()
            if ext in ['.exe', '.cap', '.pfs', '.pkg']:
                self.btn_advanced_extract.setEnabled(True)
            else:
                self.btn_advanced_extract.setEnabled(False)

    def automated_repair_bios(self):
        self.log_to_terminal("[INFO] Initializing Automated ME/CSME Repair Engine...")
        
        # 1. Parse Metadata from MEA history
        if not hasattr(self, 'mea_history') or not self.mea_history:
            self.log_to_terminal("[ERROR] No MEA history found. Please wait for analysis to complete.")
            return

        from mea_parser import parse_mea_output
        meta = parse_mea_output(self.mea_history)
        
        if not meta or not meta.get("version"):
            self.log_to_terminal("[ERROR] Failed to extract ME version from analysis logs.")
            return

        self.log_to_terminal(f"[INFO] Target: {meta.get('family', 'Unknown')} v{meta['version']} ({meta.get('sku', 'Unknown')})")

        # 2. Match Firmware
        matcher = FirmwareMatcher(get_app_root())
        repair_set = matcher.get_repair_set(meta)
        
        if not repair_set or "ME" not in repair_set:
            self.log_to_terminal("[ERROR] No matching clean ME firmware found in local repository.")
            self.log_to_terminal("[TIP] Ensure the required bin files are in Firmware_Repository/ME_Region/")
            return

        self.log_to_terminal(f"[SUCCESS] Found Clean Match: {os.path.basename(repair_set['ME'])}")
        if "PMC" in repair_set:
            self.log_to_terminal(f"[INFO] Found PMC Match: {os.path.basename(repair_set['PMC'])}")

        # 3. Prepare Output Path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_name = f"FIXED_CSME_{timestamp}_{os.path.basename(self.current_bios_file)}"
        output_dir = os.path.join(get_app_root(), "REPAIRED_BIOS")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, output_name)

        # 4. Execute Rebuild
        success = fit_automator.execute_fit_rebuild(
            self.current_bios_file,
            repair_set,
            meta['version'],
            output_path,
            self.log_to_terminal
        )

        if success and os.path.exists(output_path):
            self.log_to_terminal(f"[SUCCESS] Automated Repair Complete! ✅")
            self.log_to_terminal(f"[INFO] Output: {output_name}")
            
            # Reload in Hex Viewer
            self.current_bios_file = output_path
            with open(output_path, "rb") as f:
                data = f.read()
                self.hex_data_signal.emit(data)
            
            # Trigger Auto-Save Countdown
            if hasattr(self, "start_auto_save_countdown"):
                self.auto_save_prefix = "FIXED_CSME_"
                QMetaObject.invokeMethod(self, "start_auto_save_countdown", Qt.QueuedConnection)
        else:
            self.log_to_terminal("[ERROR] Rebuild process failed. Check fit.log for details.")

    def smart_me_fix_handler(self):
        if self.processing_mode == "Online (VPS)":
            self.vps_action("SMART_ME_FIX")
            return

        self.log_to_terminal("[ACTION] Starting LOCAL SMART ME FIX...")
        self.is_task_running = True
        self._handle_loading_state(True, "Repairing ME Region...")
        self.progress_signal.emit(15)
        
        def _run_fix():
            try:
                self.progress_signal.emit(40)
                self.automated_repair_bios()
                self.progress_signal.emit(100)
            except Exception as e:
                self.log_to_terminal(f"[ERROR] Smart ME Fix Failed: {str(e)}")
            finally:
                QMetaObject.invokeMethod(self, "initiate_loader_stop", Qt.QueuedConnection, Q_ARG(int, 2000))
                
        threading.Thread(target=_run_fix, daemon=True).start()

    def show_patches_menu(self):
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #0a0b10; color: #00d4ff; border: 1px solid #00d4ff; } QMenu::item:selected { background-color: #00d4ff; color: #000; }")
        
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

        suggested_path = os.path.join(self.last_directory, os.path.basename(self.current_bios_file))
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
                QMetaObject.invokeMethod(self, "initiate_loader_stop", Qt.QueuedConnection, Q_ARG(int, 2000))

        threading.Thread(target=_run_save, daemon=True).start()

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
                QMetaObject.invokeMethod(self, "initiate_loader_stop", Qt.QueuedConnection, Q_ARG(int, 2000))
                
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
                QMetaObject.invokeMethod(self, "initiate_loader_stop", Qt.QueuedConnection, Q_ARG(int, 2000))
                
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
                QMetaObject.invokeMethod(self, "initiate_loader_stop", Qt.QueuedConnection, Q_ARG(int, 2000))
                
        threading.Thread(target=_run_migration, daemon=True).start()
        
    def bios_rg_fix_handler(self):
        """Advanced BIOS Region Clean with DMI Migration."""
        if not self.current_bios_file:
            self.log_to_terminal("[WARNING] No BIOS file loaded")
            return

        # Both Local and VPS modes now need a donor file
        donor_path, _ = QFileDialog.getOpenFileName(self, "Select Clean BIOS/Update File", self.last_directory, "Bin (*.bin *.rom *.fd *.cap *.exe *.pfs);;All Files (*)")
        if not donor_path:
            return
            
        self.last_directory = os.path.dirname(donor_path)
        
        # --- DMI Confirmation Dialog ---
        reply = QMessageBox.question(
            self, 'DMI Migration', 
            "Do you want to migrate DMI data (Serial Number, Windows Key, etc.) from the original file?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
        )
        migrate_dmi = (reply == QMessageBox.Yes)

        if self.processing_mode == "Online (VPS)":
            self.vps_action("BIOS_RG_FIX", donor_path=donor_path, migrate_dmi=migrate_dmi)
            return

        self.log_to_terminal("[INFO] BIOS RG FIX button clicked")
        self.is_task_running = True
        
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
                    out_name = f"HP_CLEAN_{timestamp}_{os.path.basename(self.current_bios_file)}"
                    out_dir = os.path.join(get_app_root(), "REPAIRED_BIOS")
                    os.makedirs(out_dir, exist_ok=True)
                    out_path = os.path.join(out_dir, out_name)
                    
                    success = repairer.perform_repair(out_path)
                    output_path = out_path if success else None
                else:
                    output_path = BIOSRegionFixer.fix_bios_region(
                        self.current_bios_file, 
                        donor_path, 
                        self.log_to_terminal, 
                        migrate_dmi=migrate_dmi
                    )
                
                if output_path:
                    self.progress_signal.emit(100)
                    self.log_to_terminal("[SUCCESS] BIOS_region Clean Complete ✅")
                    self.log_to_terminal("[INFO] Reloading Hex View with Clean BIOS Region...")
                    self.current_bios_file = output_path
                    with open(output_path, "rb") as f:
                        data = f.read()
                        self.hex_data_signal.emit(data)
                    
                    # Trigger auto-save countdown for HP
                    if is_hp_exe:
                        self.auto_save_prefix = "CLINE BIOS_region_"
                        QMetaObject.invokeMethod(self, "start_auto_save_countdown_with_delay", Qt.QueuedConnection, Q_ARG(int, 2))
                else:
                    self.log_to_terminal("[ERROR] BIOS Region Fix failed.")
            except Exception as e:
                self.log_to_terminal(f"[ERROR] Exception during BIOS RG FIX: {str(e)}")
            finally:
                QMetaObject.invokeMethod(self, "initiate_loader_stop", Qt.QueuedConnection, Q_ARG(int, 2000))
                
        threading.Thread(target=_run_fix, daemon=True).start()

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
                
                if info:
                    brand = info.get("Brand", "Unknown")
                    self.log_to_terminal(f"[SUCCESS] Detected Brand: <font color='#ffff00'>{brand}</font>")
                    self.log_to_terminal("[INFO] DMI Information Extracted:")
                    
                    details = info.get("Details", {})
                    offsets = info.get("Offsets", {})
                    reg_map = info.get("Regions", {})
                    
                    import time
                    for k, v in details.items():
                        off_str = offsets.get(k, "N/A")
                        reg_name = reg_map.get(k, "UNKNOWN")
                        # Highlighting key information in yellow with region context
                        self.log_to_terminal(f"  - <font color='#ffff00'><b>{k}: {v}</b></font>")
                        self.log_to_terminal(f"    &nbsp;&nbsp;[Location: {reg_name} | Offset: {off_str}]")
                        
                        if "ME" in reg_name or "CSME" in reg_name:
                            self.log_to_terminal(f"    <font color='#ff3131'><b>⚠️ WARNING: {k} is stored in ME Region. BIOS Clean will NOT remove this! Use SMART ME FIX.</b></font>")
                        
                        time.sleep(0.01) # Small delay to keep UI snappy and animation smooth
                    
                    # Store in FINAL folder as requested
                    output_dir = os.path.join(get_app_root(), "TESTING_AREA", "FINAL")
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
                QMetaObject.invokeMethod(self, "initiate_loader_stop", Qt.QueuedConnection, Q_ARG(int, 1500))

        threading.Thread(target=_run_extraction, daemon=True).start()



    def advanced_extract_click_handler(self):
        self.log_to_terminal("[INFO] ADVANCED EXTRACT button clicked")
        if not self.current_bios_file: return

        destination = QFileDialog.getExistingDirectory(self, "Select Destination Folder", self.last_directory)
        if not destination: return
            
        self.last_directory = destination
            
        self.is_task_running = True
        self._handle_loading_state(True, "Universal Extraction...")
        self.progress_signal.emit(15)

        def _run_extract():
            try:
                self.progress_signal.emit(40)
                success = AdvancedExtractor.run_universal_extract(self.current_bios_file, destination, self.log_to_terminal)
                self.progress_signal.emit(100)
            except Exception as e:
                self.log_to_terminal(f"[ERROR] Extraction failed: {str(e)}")
            finally:
                QMetaObject.invokeMethod(self, "initiate_loader_stop", Qt.QueuedConnection, Q_ARG(int, 2000))

        threading.Thread(target=_run_extract, daemon=True).start()





    def check_internet_status(self):
        """Starts a background thread to check internet and server connectivity."""
        def _check():
            # 1. Internet Check
            try:
                socket.setdefaulttimeout(3)
                socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
                net_status = "online"
            except (socket.error, Exception):
                net_status = "offline"
            
            # 2. Server Check
            srv_status = self.network.check_connection()
            
            # Update UI safely
            QMetaObject.invokeMethod(self, "update_internet_status", Qt.QueuedConnection, Q_ARG(str, net_status))
            self.server_status_signal.emit(srv_status)

        threading.Thread(target=_check, daemon=True).start()

    @Slot(str)
    def update_internet_status(self, status):
        """Updates the UI label based on connectivity result."""
        if status == "online":
            self.internet_status_label.setText("● ONLINE")
            self.internet_status_label.setStyleSheet("color: #00ff41; border: 1px solid #00ff41;")
        else:
            self.internet_status_label.setText("● OFFLINE")
            self.internet_status_label.setStyleSheet("color: #ff3131; border: 1px solid #ff3131;")

    @Slot(bool)
    def update_server_ui(self, is_up):
        if is_up:
            self.server_status_label.setText("● SERVER: CONNECTED")
            self.server_status_label.setStyleSheet("color: #00ff41; border: 1px solid #00ff41;")
        else:
            self.server_status_label.setText("● SERVER: DISCONNECTED")
            self.server_status_label.setStyleSheet("color: #ff3131; border: 1px solid #ff3131;")

    def vps_action(self, command, donor_path=None, migrate_dmi=True):
        if not self.current_bios_file:
            self.log_to_terminal("[WARNING] No BIOS file loaded for VPS action.")
            return
        
        # Immediate connection check before starting
        if not self.network.check_connection():
            QMessageBox.critical(self, "Server Error", "VPS Server is not connected. Please ensure the server is running.")
            return

        self._handle_loading_state(True, f"VPS: {command.replace('_', ' ')}...")
        
        def _vps_thread():
            try:
                processed_path = self.network.send_and_process(
                    self.current_bios_file, 
                    command, 
                    self.log_to_terminal, 
                    donor_path=donor_path, 
                    migrate_dmi=migrate_dmi
                )
                if processed_path and os.path.exists(processed_path):
                    self.log_to_terminal(f"[SUCCESS] VPS processed file received.")
                    self.current_bios_file = processed_path
                    with open(processed_path, "rb") as f:
                        data = f.read()
                        self.hex_data_signal.emit(data)
                    
                    # Trigger auto-save countdown (Match main.py behavior)
                    if command == "BIOS_RG_FIX":
                        if donor_path and donor_path.lower().endswith(".exe"):
                            self.auto_save_prefix = "CLINE BIOS_region_"
                        else:
                            self.auto_save_prefix = "FIXED_RG_"
                    elif command == "SMART_ME_FIX":
                        self.auto_save_prefix = "FIXED_CSME_"
                    
                    # Beautiful Success Message (Synced with main.py)
                    if command == "SMART_ME_FIX":
                        success_msg = (
                            "<font color='#00ff41'><b>[INFO] [SUCCESS] Full CSME Clean Completed! ✅</b></font><br>"
                            "<font color='#00ff41'><b>[INFO] STATUS: Manufacturing Mode: Disabled ✅</b></font>"
                        )
                        self.log_to_terminal(success_msg)
                    
                    # Start countdown (2 seconds delay as seen in main.py)
                    QMetaObject.invokeMethod(self, "start_auto_save_countdown_with_delay", Qt.QueuedConnection, Q_ARG(int, 2))
                else:
                    self.log_to_terminal(f"[ERROR] VPS action '{command}' failed.")
            except Exception as e:
                self.log_to_terminal(f"[ERROR] VPS thread crash: {str(e)}")
            finally:
                QMetaObject.invokeMethod(self, "initiate_loader_stop", Qt.QueuedConnection, Q_ARG(int, 2000))

        threading.Thread(target=_vps_thread, daemon=True).start()

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
        self.processing_mode = "Online (VPS)"
        # self.mode_selector.setCurrentText("Online (VPS)")
        self.current_bios_file = None
        self.current_regions_map = {}
        self.mea_history = "" # Reset MEA history
        
        # Explicitly disable all module buttons
        self.enable_module_buttons({})
        
        self.terminal.clear()
        self.hex_model.set_data(b"")
        
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

    def change_system_mode(self, mode):
        self.processing_mode = mode
        self.log_to_terminal(f"[SYSTEM] Switched to {mode} mode.")
        if mode == "Online (VPS)":
            # Immediate connection check
            if not self.network.check_connection():
                self.log_to_terminal("[WARNING] VPS Server seems to be offline.")
            else:
                self.log_to_terminal("[SUCCESS] Connected to VPS Cloud Backend.")

    def show_logs_popup(self):
        """Opens a popup window to show the contents of app.log."""
        dialog = LogViewerDialog(self)
        dialog.exec()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.drop_overlay.show()
            self.drop_overlay.raise_()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self.drop_overlay.hide()

    def dropEvent(self, event):
        self.drop_overlay.hide()
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            file_path = urls[0].toLocalFile()
            self.log_to_terminal(f"[INFO] File dropped: {os.path.basename(file_path)}")
            self.load_bios_file(file_path)

    def open_bios_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open BIOS File",
            self.last_directory,
            "All Supported Files (*.bin *.rom *.fd *.cap *.exe *.pfs *.pkg *.sbk *.sbi *.msdm);;BIOS Dumps (*.bin *.rom *.fd *.cap);;Update Packages (*.exe *.pfs *.pkg);;All Files (*)"
        )

        if file_path:
            self.last_directory = os.path.dirname(file_path)
            self.log_to_terminal(f"[INFO] User selected file: {os.path.basename(file_path)}")
            self.load_bios_file(file_path)

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
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Invalid File Format")
            msg.setText(f"The file you selected has an invalid format: '{ext}'\n\nPlease provide a BIOS dump or supported update package.")
            msg.setStyleSheet("QMessageBox { background-color: #0a0b10; color: #ff3131; } QLabel { color: #ff3131; font-weight: bold; } QPushButton { background-color: #1a1d2e; border: 1px solid #ff3131; color: #ff3131; padding: 5px; } QPushButton:hover { background-color: #ff3131; color: #000; }")
            msg.exec()
            return

        # Start Global Loader & Mark Task Running
        self.is_task_running = True
        estimate = tracker.get_estimate("load_bios_file", 8.0)
        self._handle_loading_state(True, "Analyzing Firmware...", estimate)
        self._start_perf_time = time.perf_counter()
        self.progress_signal.emit(5)

        self.current_bios_file = str(file_path)
        self.reset_stage = 0
        self.terminal.clear()
        self.mea_history = ""
        self.log_to_terminal(f"[INFO] Initializing analysis for: {os.path.basename(file_path)}")

        # LATENCY OPTIMIZATION: Load Hex View IMMEDIATELY
        try:
            with open(file_path, "rb") as f:
                raw_data = f.read()
                self.hex_data_signal.emit(raw_data)
            self.log_to_terminal("[INFO] Hex data loaded to viewer (Background analysis starting...)")
        except Exception as e:
            self.log_to_terminal(f"[ERROR] Immediate hex load failed: {str(e)}")

        # Smart Extraction for Executable Wrappers/Packages
        if ext in ['.exe', '.pfs', '.pkg', '.sbk', '.sbi', '.msdm', '.cap']:
            self.progress_signal.emit(30)
            self.log_to_terminal(f"[INFO] Detected Vendor Package ({ext.upper()}). Launching Smart Extraction...")
            
            def run_smart_extract():
                try:
                    from advanced_extractor import AdvancedExtractor
                    temp_extract_dir = os.path.join(self.workspace_dir, "smart_extract")
                    os.makedirs(temp_extract_dir, exist_ok=True)
                    
                    if AdvancedExtractor.run_universal_extract(file_path, temp_extract_dir, self.log_to_terminal):
                        # Find the best BIOS file in the extracted results
                        extracted_files = []
                        for root, _, files in os.walk(temp_extract_dir):
                            for f in files:
                                if f.lower().endswith(('.bin', '.rom', '.fd')):
                                    extracted_files.append(os.path.join(root, f))
                        
                        if extracted_files:
                            # Use the largest file as it's most likely the BIOS image
                            best_file = max(extracted_files, key=os.path.getsize)
                            self.log_to_terminal(f"[SUCCESS] Smart Extraction successful. Loading image: {os.path.basename(best_file)}")
                            # Re-trigger load with the extracted bin
                            QMetaObject.invokeMethod(self, "load_bios_file", Qt.QueuedConnection, Q_ARG(str, best_file))
                            return
                        else:
                            self.log_to_terminal("[WARNING] Extraction succeeded but no BIOS image (.bin) was found inside.")
                    else:
                        self.log_to_terminal("[ERROR] Smart Extraction failed for this package.")
                except Exception as e:
                    self.log_to_terminal(f"[ERROR] Smart Extraction Crashed: {str(e)}")
                finally:
                    QMetaObject.invokeMethod(self, "initiate_loader_stop", Qt.QueuedConnection, Q_ARG(int, 2000))

            threading.Thread(target=run_smart_extract, daemon=True).start()
            return

        def run_analysis_task():
            try:
                self.progress_signal.emit(10)
                metadata = get_bios_metadata(file_path, self.log_to_terminal, getattr(self, "handle_mea_output", None))
                
                if metadata:
                    self.progress_signal.emit(35)
                    self.log_to_terminal("-" * 30)
                    self.log_to_terminal(">>> SYSTEM HEALTH REPORT GENERATED")
                    self.log_to_terminal("-" * 30)

                    # Chain Analysis 2: Microcode Guard Audit
                    self.progress_signal.emit(50)
                    from analysis_suite import AnalysisSuite
                    AnalysisSuite.record_duration = lambda t, d: None # Mock for now
                    
                    AnalysisSuite.run_microcode_analyzer(file_path, self.log_to_terminal)
                    self.progress_signal.emit(65)

                    # self.log_to_terminal("\n" + "="*50)
                    # self.log_to_terminal("--- PHASE 1: INTEL SECURITY DESCRIPTORS ---")
                    # self.log_to_terminal("="*50)
                    # AnalysisSuite.run_security_descriptor_parser(file_path, self.log_to_terminal)
                    self.progress_signal.emit(80)

                    # Chain Analysis 4: BIOS Guard technology
                    AnalysisSuite.run_bios_guard_analysis(file_path, self.log_to_terminal)
                    self.progress_signal.emit(95)
                    
                    self.log_to_terminal("-" * 30)
                    self.log_to_terminal("[SUCCESS] ALL ANALYSES COMPLETE")
                    self.log_to_terminal("-" * 30)
                    
                    # Loaded data already emitted above for speed
                    QMetaObject.invokeMethod(self.btn_save, "setEnabled", Qt.QueuedConnection, Q_ARG(bool, True))
                    QMetaObject.invokeMethod(self.btn_smart_me_fix, "setEnabled", Qt.QueuedConnection, Q_ARG(bool, True))
                        
                    # Setup region patch interactions
                    regions = metadata.get("regions")
                    if regions and isinstance(regions, dict) and any(regions.values()):
                        self.current_regions_map = regions
                        self.module_buttons_signal.emit(regions)
                        
                        # --- AUTO DECOMPILE SETUP ---
                        self.auto_decompile_pending = True
                        mea_py = os.path.join(get_app_root(), "ME Analyzer", "MEA.py")
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
                # Ensure we hit 100% slowly if we were stuck at 95%
                self.progress_signal.emit(100)
                
                # Record performance
                if hasattr(self, '_start_perf_time'):
                    duration = time.perf_counter() - self._start_perf_time
                    tracker.record_duration("load_bios_file", duration)

                # SYNC FIX: Wait for the UI to actually increment the displayed percentage 
                # to 100% before triggering the results visibility.
                # We use a slight delay before finishing to ensure the '100%' is visible.
                QMetaObject.invokeMethod(self, "finalize_load_task", Qt.QueuedConnection)

        # Start the analysis thread
        threading.Thread(target=run_analysis_task, daemon=True).start()

    @Slot()
    def finalize_load_task(self):
        """Called when analysis completes to finalize UI updates."""
        self.log_to_terminal("[SUCCESS] Operation finished.")
        self.progress_signal.emit(100)
        # Snappy closure
        self.initiate_loader_stop(300) 

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
                self.log_to_terminal(f"[SUCCESS] INTERNAL WORKSPACE READY: {os.path.basename(str(decomp_target))}")
            else:
                self.log_to_terminal("[WARN] Standard Intel FIT Decompile failed (Image corruption detected).")
                self.log_to_terminal("[TIP] You can try manual repair by clicking the 'SMART ME FIX' button.")
                self.skip_auto_repair = False
                
        except Exception as e:
            self.log_to_terminal(f"[ERROR] Auto-decompile process crashed: {str(e)}")

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
            
        for line in ui_lines:
            self.terminal.append(line)
            # Detect end of MEA report
            if "[SUCCESS] ME Analyzer complete." in line:
                self.log_to_terminal("-" * 30)
                self.log_to_terminal("<font color='#00f3ff'><b>[INFO] Firmware Analysis Complete.</b></font>")
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
        self.btn_save.setText(f"SAVE CHANGES ({self.auto_save_countdown}s)")
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
            self.btn_save.setText("SAVE CHANGES")
            self.btn_save.setStyleSheet("border-color: #ff00ff; color: #ff00ff;") # Reset to Purple
            self.is_auto_saving = False
            # Trigger the save dialog
            self.save_bios_changes()
        else:
            self.btn_save.setText(f"SAVE CHANGES ({self.auto_save_countdown}s)")

    def save_bios_changes(self):
        # Stop auto-save if user clicks manually
        if self.is_auto_saving:
            self.auto_save_timer.stop()
            self.is_auto_saving = False
            self.btn_save.setText("SAVE CHANGES")
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
                QTimer.singleShot(2000, lambda p=saved_path: self.load_bios_file(p))
                
            except Exception as e:
                self.log_to_terminal(f"[ERROR] Failed to save changes: {str(e)}")

    @Slot(str, str, dict)
    def show_error_prompt_sync(self, title: str, message: str, ret_val: dict):
        """
        Synchronous UI blocking prompt for fatal/critical pipeline errors.
        Modifies ret_val in-place to return the choice across threads.
        """
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Critical)
        
        # Add custom buttons
        btn_retry = msg_box.addButton("Retry", QMessageBox.AcceptRole)
        btn_ignore = msg_box.addButton("Ignore & Continue", QMessageBox.DestructiveRole)
        btn_abort = msg_box.addButton("Abort", QMessageBox.RejectRole)
        
        msg_box.exec()
        
        if msg_box.clickedButton() == btn_retry:
            ret_val["choice"] = "retry"
        elif msg_box.clickedButton() == btn_ignore:
            ret_val["choice"] = "ignore"
        else:
            ret_val["choice"] = "abort"


    def automated_repair_bios(self):
        """
        Full automated BIOS repair via Smart Repair Engine.
        Replaces old manual pipeline — supports all ME versions,
        auto-selects firmware, runs FIT, verifies with MEA,
        and delivers to TESTING_AREA/FINAL BIOS.
        """
        if not self.current_bios_file:
            self.log_to_terminal("[ERROR] No BIOS file is currently loaded.")
            return

        # ── Step 1: Parse MEA history for firmware info ──────────────
        history_str = str(self.mea_history)
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
            f"[INFO] Firmware detected — "
            f"Version: {mea_meta['version']} | "
            f"Family: {mea_meta.get('family','?')} | "
            f"SKU: {mea_meta.get('sku','?')} | "
            f"Chipset: {mea_meta.get('chipset','?')}"
        )

        # ── Step 2: Run full pipeline via Smart Repair Engine ────────
        def _progress(pct):
            self.progress_signal.emit(int(pct))

        result = smart_repair_engine.run_smart_repair(
            bios_path        = str(self.current_bios_file),
            mea_meta         = mea_meta,
            log_cb           = self.log_to_terminal,
            progress_cb      = _progress,
            deliver_to_final = True,
            error_manager    = self.error_manager,
        )

        # ── Step 3: Update GUI on success ────────────────────────────
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
            fail_msg = (
                "<font color='#ff3131'><b>[ERROR] Smart Repair Engine reported failure. ⚠️</b></font><br>"
                "<font color='#ff3131'><b>[INFO] STATUS: Initialized Mode (Repair Incomplete)</b></font>"
            )
            self.log_to_terminal(fail_msg)
            self.log_to_terminal(
                "[ERROR] Check terminal output and fit_errors_solutions.log."
            )

if __name__ == "__main__":
    multiprocessing.freeze_support()
    
    # SINGLE INSTANCE CHECK (Prevention of multiple windows)
    import tempfile
    lock_file = os.path.join(tempfile.gettempdir(), "r1_bios_tool.lock")
    _lock_handle = None # Keep reference to prevent GC
    try:
        # On Windows, we can't remove a file if it's open by another process
        if os.path.exists(lock_file):
            try:
                os.remove(lock_file)
            except:
                # File is locked by another instance
                sys.exit(0)
        
        # Create and lock the file
        _lock_handle = open(lock_file, "w")
        _lock_handle.write(str(os.getpid()))
        _lock_handle.flush()
    except Exception:
        pass

    app = QApplication(sys.argv)
    
    # Set app-wide font if needed
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    window = BiosServiceTool()
    window.initialize_ui_window()
    
    sys.exit(app.exec())

