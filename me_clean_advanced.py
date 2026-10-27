from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, 
                               QHBoxLayout, QFileDialog, QFrame, QStyle, QScrollArea, QWidget)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
import os

class ComponentDropZone(QFrame):
    file_selected = Signal(str, str) # component_name, file_path
    
    def __init__(self, component_name, is_dark_mode=True, parent=None):
        super().__init__(parent)
        self.component_name = component_name
        self.is_dark_mode = is_dark_mode
        self.selected_file_path = None
        
        self.setFrameShape(QFrame.StyledPanel)
        self.setAcceptDrops(True)
        
        self.init_ui()
        self.apply_style()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.lbl_title = QLabel(f"[{self.component_name}] Drop Region File")
        self.lbl_title.setAlignment(Qt.AlignCenter)
        self.lbl_title.setStyleSheet("font-weight: bold;")
        
        self.lbl_status = QLabel("No file selected\n(Click to browse)")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(self.lbl_title)
        layout.addWidget(self.lbl_status)
        
    def apply_style(self):
        if self.is_dark_mode:
            self.setStyleSheet("""
                QFrame { border: 2px dashed #2d363f; border-radius: 8px; background-color: #14171a; }
                QFrame:hover { border: 2px dashed #0ef6fd; background-color: #1a1e22; }
                QLabel { color: #4cd3e3; border: none; background: transparent; }
            """)
        else:
            self.setStyleSheet("""
                QFrame { border: 2px dashed #9ca3af; border-radius: 8px; background-color: #ffffff; }
                QFrame:hover { border: 2px dashed #3b82f6; background-color: #f3f4f6; }
                QLabel { color: #1f2937; border: none; background: transparent; }
            """)
            
    def mousePressEvent(self, event):
        file_path, _ = QFileDialog.getOpenFileName(
            self, f"Select Clean {self.component_name} File", "", "Firmware Files (*.bin *.rom *.cap *.fd);;All Files (*)"
        )
        if file_path:
            self.set_file(file_path)
            
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and len(urls) == 1:
                file_path = urls[0].toLocalFile()
                ext = os.path.splitext(file_path)[1].lower()
                if ext in ['.bin', '.rom', '.cap', '.fd']:
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            self.set_file(file_path)
            
    def set_file(self, file_path):
        self.selected_file_path = file_path
        filename = os.path.basename(file_path)
        self.lbl_status.setText(f"Selected: {filename}")
        self.lbl_status.setStyleSheet("color: #00ff88; font-weight: bold; border: none; background: transparent;" if self.is_dark_mode else "color: #10b981; font-weight: bold; border: none; background: transparent;")
        self.file_selected.emit(self.component_name, file_path)


class AdvancedMECleanDialog(QDialog):
    # Emits a dictionary mapping component names (ME, PMC, etc) to file paths
    files_selected = Signal(dict)

    def __init__(self, parent=None, is_dark_mode=True, required_components=None):
        super().__init__(parent)
        self.setWindowTitle("Manual Component Injection")
        self.setMinimumWidth(500)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        self.is_dark_mode = is_dark_mode
        self.required_components = required_components or ["ME"]
        self.selected_files = {} # dict mapping component to path
        
        self.init_ui()
        self.apply_style()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        self.title_label = QLabel("Drag & Drop Required Clean Files Below")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(self.title_label)
        
        desc_label = QLabel("Only 'ME' is strictly mandatory for older platforms. If other required components are left empty, the tool will attempt to pull them from the internal repository.")
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc_label)

        # Scroll area for multiple components
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        scroll_content = QWidget()
        self.zones_layout = QVBoxLayout(scroll_content)
        self.zones_layout.setSpacing(10)
        
        for comp in self.required_components:
            zone = ComponentDropZone(comp, self.is_dark_mode, self)
            zone.file_selected.connect(self.on_file_selected)
            self.zones_layout.addWidget(zone)
            
        self.zones_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)

        # Status Label
        self.status_label = QLabel(f"Selected: 0/{len(self.required_components)} components")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_start = QPushButton("Start Clean")
        self.btn_start.setObjectName("BtnStartClean")
        self.btn_start.clicked.connect(self.start_cleaning)
        self.btn_start.setEnabled(False) 
        
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_start)
        
        layout.addLayout(btn_layout)

    def apply_style(self):
        if self.is_dark_mode:
            self.setStyleSheet("""
                QDialog { background-color: #171a1d; color: #e2e8f0; }
                QLabel { color: #e2e8f0; font-family: 'Segoe UI', sans-serif; }
                QPushButton { background-color: #252a2e; color: #ffffff; border: 1px solid #3c444d; padding: 8px 18px; border-radius: 6px; font-weight: bold; font-family: 'Segoe UI', sans-serif; }
                QPushButton:hover { background-color: #2e353b; border-color: #4cd3e3; color: #ffffff; }
                QPushButton:disabled { background-color: #1b2024; color: #475569; border: 1px solid #272e36; }
                QPushButton#BtnStartClean {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8fe3ea, stop:0.5 #3598a6, stop:1 #247d8a);
                    color: #0b151a;
                    border: none;
                    font-weight: 900;
                }
                QPushButton#BtnStartClean:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #bbf2f6, stop:0.5 #45b1bf, stop:1 #2ca0b0);
                    color: #000000;
                }
                QPushButton#BtnStartClean:disabled {
                    background: #1b2024;
                    color: #475569;
                    border: 1px solid #272e36;
                }
                QScrollArea { background-color: transparent; }
                QScrollArea > QWidget > QWidget { background-color: transparent; }
            """)
        else:
            self.setStyleSheet("""
                QDialog { background-color: #f0f2f5; color: #1f2937; }
                QLabel { color: #1f2937; }
                QPushButton { background-color: #ffffff; color: #1f2937; border: 1px solid #9ca3af; padding: 8px 15px; border-radius: 4px; font-weight: bold; }
                QPushButton:hover { background-color: #3b82f6; color: #ffffff; border-color: #3b82f6; }
                QPushButton:disabled { background-color: #e5e7eb; color: #9ca3af; border: 1px solid #d1d5db; }
                QScrollArea { background-color: transparent; }
                QScrollArea > QWidget > QWidget { background-color: transparent; }
            """)

    def on_file_selected(self, component_name, file_path):
        self.selected_files[component_name] = file_path
        count = len(self.selected_files)
        total = len(self.required_components)
        self.status_label.setText(f"Selected: {count}/{total} components")
        
        if count == total:
            self.status_label.setStyleSheet("color: #00ff88; font-weight:bold;" if self.is_dark_mode else "color: #10b981; font-weight:bold;")
        else:
            self.status_label.setStyleSheet("")
            
        # At least ME must be selected to enable start (if ME is in required components)
        if "ME" in self.required_components and "ME" not in self.selected_files:
            self.btn_start.setEnabled(False)
        else:
            self.btn_start.setEnabled(True)

    def start_cleaning(self):
        if self.selected_files:
            self.files_selected.emit(self.selected_files)
            self.accept()
