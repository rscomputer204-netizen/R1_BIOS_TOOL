import os
import math
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QListWidget, QPushButton, QHBoxLayout, QMessageBox
from PySide6.QtCore import Qt

class ExtractedFileListDialog(QDialog):
    def __init__(self, extracted_files, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select BIOS Candidate")
        self.setFixedSize(500, 400)
        self.setStyleSheet("background-color: #0f172a; color: #ffffff;")
        
        self.selected_file = None
        self.extracted_files = extracted_files
        
        layout = QVBoxLayout(self)
        
        title = QLabel("Extracted Files Found")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #38bdf8; margin-bottom: 10px;")
        layout.addWidget(title)
        
        desc = QLabel("Please select the valid BIOS Region file from the list below:")
        desc.setStyleSheet("color: #94a3b8;")
        layout.addWidget(desc)
        
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(
            "QListWidget { background-color: #1e293b; border: 1px solid #334155; border-radius: 4px; padding: 5px; }"
            "QListWidget::item { padding: 8px; border-bottom: 1px solid #334155; }"
            "QListWidget::item:selected { background-color: #0284c7; }"
        )
        def format_size(size_bytes):
            if size_bytes == 0:
                return "0 B"
            size_name = ("B", "KB", "MB", "GB", "TB")
            i = int(math.floor(math.log(size_bytes, 1024)))
            p = math.pow(1024, i)
            s = round(size_bytes / p, 2)
            return f"{s} {size_name[i]}"

        for f in self.extracted_files:
            try:
                size_bytes = os.path.getsize(f)
                size_str = format_size(size_bytes)
            except Exception:
                size_str = "Unknown Size"
            
            display_text = f"{os.path.basename(f)}   [{size_str}]"
            self.list_widget.addItem(display_text)
            
        layout.addWidget(self.list_widget)
        
        btn_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_select = QPushButton("Select File")
        
        btn_style = "QPushButton { padding: 8px 16px; font-weight: bold; border-radius: 4px; } "
        self.btn_cancel.setStyleSheet(btn_style + "background-color: #334155; color: white;")
        self.btn_select.setStyleSheet(btn_style + "background-color: #0ea5e9; color: white;")
        
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_select.clicked.connect(self.on_select)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_select)
        
        layout.addLayout(btn_layout)
        
    def on_select(self):
        row = self.list_widget.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Selection Required", "Please select a file from the list.")
            return
            
        self.selected_file = self.extracted_files[row]
        self.accept()
