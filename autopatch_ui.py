"""
R1 BIOS TOOL — AUTOPATCH UI
===========================
Modern PySide6 interface for dynamic BIOS patch browsing, brand auto-filtering,
safety verification, and one-click patching.
"""

import os
import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QFrame, QTextEdit, QFileDialog,
    QCheckBox, QMessageBox, QSplitter, QWidget, QButtonGroup
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QColor, QFont, QIcon, QDragEnterEvent, QDropEvent

from autopatch_engine import AutoPatchEngine


CYBER_STYLE = """
QDialog {
    background-color: #0b1017;
    color: #e2e8f0;
    font-family: 'Segoe UI', sans-serif;
}
QFrame#Card {
    background-color: #0e1520;
    border: 1px solid #1a2536;
    border-radius: 8px;
}
QFrame#BadgeFrame {
    background-color: #131d2b;
    border: 1px solid #00f3ff;
    border-radius: 6px;
}
QLabel {
    color: #cbd5e1;
}
QLineEdit {
    background-color: #080c12;
    border: 1px solid #1e293b;
    border-radius: 6px;
    padding: 8px 12px;
    color: #00f3ff;
    font-size: 13px;
    selection-background-color: #00adb5;
}
QLineEdit:focus {
    border: 1px solid #00f3ff;
}
QListWidget {
    background-color: #080c12;
    border: 1px solid #1a2536;
    border-radius: 6px;
    padding: 4px;
    outline: none;
}
QListWidget::item {
    background-color: #0e1520;
    border: 1px solid #1e293b;
    border-radius: 6px;
    margin: 3px 2px;
    padding: 8px;
}
QListWidget::item:hover {
    background-color: #131d2b;
    border: 1px solid #00adb5;
}
QListWidget::item:selected {
    background-color: #172437;
    border: 1px solid #00f3ff;
}
QPushButton#PillBtn {
    background-color: #101824;
    color: #94a3b8;
    border: 1px solid #1e293b;
    border-radius: 14px;
    padding: 5px 14px;
    font-size: 11px;
    font-weight: bold;
}
QPushButton#PillBtn:hover {
    background-color: #162233;
    color: #e2e8f0;
    border-color: #00adb5;
}
QPushButton#PillBtn:checked {
    background-color: #00adb5;
    color: #0b1017;
    border-color: #00f3ff;
}
QPushButton#ExecuteBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00adb5, stop:1 #00f3ff);
    color: #0b1017;
    font-weight: bold;
    font-size: 13px;
    letter-spacing: 1px;
    border: none;
    border-radius: 6px;
    padding: 10px 20px;
}
QPushButton#ExecuteBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00c4cc, stop:1 #38bdf8);
}
QPushButton#ExecuteBtn:disabled {
    background: #1e293b;
    color: #64748b;
}
QPushButton#SecondaryBtn {
    background-color: #131d2b;
    color: #cbd5e1;
    border: 1px solid #1e293b;
    border-radius: 6px;
    padding: 8px 14px;
    font-size: 12px;
}
QPushButton#SecondaryBtn:hover {
    background-color: #1c2b3f;
    border-color: #00f3ff;
    color: #ffffff;
}
QTextEdit {
    background-color: #080c12;
    border: 1px solid #1a2536;
    border-radius: 6px;
    color: #94a3b8;
    font-family: 'Consolas', monospace;
    font-size: 11px;
    padding: 6px;
}
QCheckBox {
    color: #cbd5e1;
    font-size: 12px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 1px solid #334155;
    background: #0e1520;
}
QCheckBox::indicator:checked {
    background: #00f3ff;
    border-color: #00f3ff;
}
"""


class DropLineEdit(QLineEdit):
    """Line edit that accepts dragged BIOS files."""
    file_dropped = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
        else:
            e.ignore()

    def dropEvent(self, e: QDropEvent):
        for url in e.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.isfile(file_path):
                self.setText(file_path)
                self.file_dropped.emit(file_path)
                break


class AutoPatchDialog(QDialog):
    def __init__(self, parent=None, initial_file=None, dmi_hint=None):
        super().__init__(parent)
        self.setWindowTitle("AutoPatch — Dynamic BIOS Firmware Fix Engine")
        self.resize(1060, 720)
        self.setMinimumSize(920, 600)
        self.setStyleSheet(CYBER_STYLE)

        self.engine = AutoPatchEngine()
        self.current_file = initial_file or ""
        self.dmi_hint = dmi_hint or {}
        self.detected_brand = "UNKNOWN"
        self.detected_model = ""
        self.selected_patch = None

        self.setup_ui()
        self.initialize_state()

    def setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 16, 18, 16)
        root_layout.setSpacing(12)

        # ── 1. Top Header & Detection Badge ────────────────────────────────
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title_lbl = QLabel("AUTOPATCH ENGINE")
        title_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #00f3ff; letter-spacing: 1px;")
        sub_lbl = QLabel("Dynamic cloud-synchronized BIOS problem solver & byte modification engine")
        sub_lbl.setStyleSheet("font-size: 11px; color: #64748b;")
        title_box.addWidget(title_lbl)
        title_box.addWidget(sub_lbl)
        header_layout.addLayout(title_box)

        header_layout.addStretch()

        # Detected Target Badge
        self.badge_frame = QFrame()
        self.badge_frame.setObjectName("BadgeFrame")
        badge_layout = QHBoxLayout(self.badge_frame)
        badge_layout.setContentsMargins(12, 6, 12, 6)
        self.lbl_detect_status = QLabel("Target: Detecting...")
        self.lbl_detect_status.setStyleSheet("font-size: 12px; font-weight: bold; color: #00f3ff;")
        badge_layout.addWidget(self.lbl_detect_status)
        header_layout.addWidget(self.badge_frame)

        btn_sync = QPushButton("☁ Sync Cloud")
        btn_sync.setObjectName("SecondaryBtn")
        btn_sync.clicked.connect(self.sync_cloud_patches)
        header_layout.addWidget(btn_sync)

        root_layout.addLayout(header_layout)

        # ── 2. Brand Filters & Search Bar ─────────────────────────────────
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(8)

        self.brand_group = QButtonGroup(self)
        self.brand_buttons = {}
        brands = [("ALL", "All Brands"), ("AUTO", "Auto-Filtered"), ("DELL", "Dell"), ("LENOVO", "Lenovo"), ("HP", "HP"), ("ASUS", "Asus"), ("ACER", "Acer"), ("UNIVERSAL", "Universal")]
        
        for key, text in brands:
            btn = QPushButton(text)
            btn.setObjectName("PillBtn")
            btn.setCheckable(True)
            self.brand_group.addButton(btn)
            filter_bar.addWidget(btn)
            self.brand_buttons[key] = btn
            btn.clicked.connect(lambda checked, b=key: self.on_brand_filter_clicked(b))

        self.brand_buttons["AUTO"].setChecked(True)

        filter_bar.addStretch()

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Search by Model, Board Code (NM-B481), Symptom...")
        self.txt_search.setFixedWidth(280)
        self.txt_search.textChanged.connect(self.refresh_patch_list)
        filter_bar.addWidget(self.txt_search)

        root_layout.addLayout(filter_bar)

        # ── 3. Main Splitter (Left: List, Right: Details & Patch) ──────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background: #1a2536; width: 2px; }")

        # LEFT PANE: Patch List
        left_card = QFrame()
        left_card.setObjectName("Card")
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(10, 10, 10, 10)

        list_header = QHBoxLayout()
        self.lbl_catalog_title = QLabel("Available Patches")
        self.lbl_catalog_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #00f3ff;")
        list_header.addWidget(self.lbl_catalog_title)
        list_header.addStretch()
        self.lbl_count = QLabel("0 found")
        self.lbl_count.setStyleSheet("font-size: 11px; color: #64748b;")
        list_header.addWidget(self.lbl_count)
        left_layout.addLayout(list_header)

        self.list_patches = QListWidget()
        self.list_patches.itemSelectionChanged.connect(self.on_patch_selected)
        left_layout.addWidget(self.list_patches)

        splitter.addWidget(left_card)
        splitter.setStretchFactor(0, 4)

        # RIGHT PANE: Details, File Selector & Action
        right_card = QFrame()
        right_card.setObjectName("Card")
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(14, 14, 14, 14)
        right_layout.setSpacing(10)

        # Patch Title & Meta
        self.lbl_patch_title = QLabel("Select a patch from the list")
        self.lbl_patch_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        right_layout.addWidget(self.lbl_patch_title)

        self.lbl_patch_meta = QLabel("Brand: — | Model: — | Author: —")
        self.lbl_patch_meta.setStyleSheet("font-size: 11px; color: #38bdf8;")
        right_layout.addWidget(self.lbl_patch_meta)

        # Symptom Box
        lbl_symp_head = QLabel("SYMPTOM / OBSERVED ISSUE:")
        lbl_symp_head.setStyleSheet("font-size: 10px; font-weight: bold; color: #eab308; letter-spacing: 0.5px; margin-top: 4px;")
        right_layout.addWidget(lbl_symp_head)

        self.lbl_symptom = QLabel("N/A")
        self.lbl_symptom.setWordWrap(True)
        self.lbl_symptom.setStyleSheet("font-size: 12px; color: #fef08a; background: #161c18; padding: 8px; border-radius: 4px; border-left: 3px solid #eab308;")
        right_layout.addWidget(self.lbl_symptom)

        # Description Box
        lbl_desc_head = QLabel("TECHNICAL DESCRIPTION:")
        lbl_desc_head.setStyleSheet("font-size: 10px; font-weight: bold; color: #94a3b8; letter-spacing: 0.5px; margin-top: 4px;")
        right_layout.addWidget(lbl_desc_head)

        self.txt_description = QTextEdit()
        self.txt_description.setReadOnly(True)
        self.txt_description.setFixedHeight(75)
        right_layout.addWidget(self.txt_description)

        # Target BIOS File Selection
        lbl_file_head = QLabel("TARGET BIOS IMAGE (DRAG & DROP OR BROWSE):")
        lbl_file_head.setStyleSheet("font-size: 10px; font-weight: bold; color: #00f3ff; letter-spacing: 0.5px; margin-top: 6px;")
        right_layout.addWidget(lbl_file_head)

        file_row = QHBoxLayout()
        self.txt_bios_path = DropLineEdit()
        self.txt_bios_path.setPlaceholderText("Select or drop BIOS .bin / .rom file here...")
        self.txt_bios_path.file_dropped.connect(self.on_file_changed)
        self.txt_bios_path.textChanged.connect(self.on_file_changed)
        file_row.addWidget(self.txt_bios_path)

        btn_browse = QPushButton("Browse...")
        btn_browse.setObjectName("SecondaryBtn")
        btn_browse.clicked.connect(self.browse_bios_file)
        file_row.addWidget(btn_browse)
        right_layout.addLayout(file_row)

        # Safety Verification Banner
        self.lbl_verify_status = QLabel("Verification: Please select a patch and target file")
        self.lbl_verify_status.setStyleSheet("font-size: 11px; padding: 6px 10px; border-radius: 4px; background: #101927; color: #7e8f9f;")
        right_layout.addWidget(self.lbl_verify_status)

        # Options
        self.chk_backup = QCheckBox("Create automatic backup before patching (_ORIGINAL_BACKUP.bin)")
        self.chk_backup.setChecked(True)
        right_layout.addWidget(self.chk_backup)

        right_layout.addStretch()

        # Action Buttons
        act_row = QHBoxLayout()
        self.btn_execute = QPushButton("⚡ EXECUTE AUTO PATCH")
        self.btn_execute.setObjectName("ExecuteBtn")
        self.btn_execute.setEnabled(False)
        self.btn_execute.clicked.connect(self.execute_patch_action)
        act_row.addWidget(self.btn_execute)

        right_layout.addLayout(act_row)

        splitter.addWidget(right_card)
        splitter.setStretchFactor(1, 5)

        root_layout.addWidget(splitter)

        # ── 4. Bottom Terminal Log ─────────────────────────────────────────
        self.txt_log = QTextEdit()
        self.txt_log.setFixedHeight(85)
        self.txt_log.setReadOnly(True)
        root_layout.addWidget(self.txt_log)

    def log(self, text: str, color: str = "#00f3ff"):
        self.txt_log.append(f"<font color='{color}'>&gt; {text}</font>")
        self.txt_log.verticalScrollBar().setValue(self.txt_log.verticalScrollBar().maximum())

    def initialize_state(self):
        """Initializes file and brand detection."""
        if self.current_file and os.path.exists(self.current_file):
            self.txt_bios_path.setText(self.current_file)
            self.analyze_file(self.current_file)
        else:
            self.lbl_detect_status.setText("Target: No File Loaded")
            self.refresh_patch_list()

    def analyze_file(self, file_path: str):
        """Analyzes loaded file and identifies brand/model."""
        self.current_file = file_path
        brand, model = self.engine.detect_brand(file_path, self.dmi_hint)
        self.detected_brand = brand
        self.detected_model = model or ""

        if brand != "UNKNOWN":
            display_text = f"🎯 Target: {brand}"
            if model:
                display_text += f" ({model})"
            self.lbl_detect_status.setText(display_text)
            self.badge_frame.setStyleSheet("QFrame#BadgeFrame { background-color: #0b2229; border: 1px solid #00f3ff; border-radius: 6px; }")
            self.log(f"Detected target brand: {brand}" + (f" - Model: {model}" if model else ""))
        else:
            self.lbl_detect_status.setText("Target: Unknown Brand (Showing All)")
            self.badge_frame.setStyleSheet("QFrame#BadgeFrame { background-color: #1a1625; border: 1px solid #a855f7; border-radius: 6px; }")

        # Automatically select AUTO filter
        if self.brand_buttons["AUTO"].isChecked():
            self.refresh_patch_list()
        else:
            self.brand_buttons["AUTO"].setChecked(True)
            self.refresh_patch_list()

        self.update_verification_status()

    def on_file_changed(self, path: str):
        clean_path = path.strip().strip('"')
        if os.path.isfile(clean_path):
            self.analyze_file(clean_path)
        else:
            self.current_file = ""
            self.update_verification_status()

    def browse_bios_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select BIOS Image File", "",
            "BIOS Files (*.bin *.rom *.fd *.cap *.wph);;All Files (*.*)"
        )
        if file_path:
            self.txt_bios_path.setText(file_path)

    def on_brand_filter_clicked(self, brand_key: str):
        self.refresh_patch_list()

    def get_active_brand_filter(self) -> str:
        for key, btn in self.brand_buttons.items():
            if btn.isChecked():
                if key == "AUTO":
                    return self.detected_brand if self.detected_brand != "UNKNOWN" else "ALL"
                return key
        return "ALL"

    def refresh_patch_list(self):
        active_brand = self.get_active_brand_filter()
        query = self.txt_search.text().strip()

        patches = self.engine.get_filtered_patches(brand=active_brand, search_query=query)
        self.list_patches.clear()

        # Update title
        brand_name = "All Brands" if active_brand in ("ALL", "UNKNOWN") else active_brand
        self.lbl_catalog_title.setText(f"Available Patches ({brand_name})")
        self.lbl_count.setText(f"{len(patches)} patch{'es' if len(patches) != 1 else ''} available")

        for p in patches:
            item = QListWidgetItem()
            # Set size hint
            item.setSizeHint(QSize(280, 68))
            item.setData(Qt.ItemDataRole.UserRole, p)

            # Build custom widget
            w = QWidget()
            layout = QVBoxLayout(w)
            layout.setContentsMargins(6, 4, 6, 4)
            layout.setSpacing(2)

            top_row = QHBoxLayout()
            title_lbl = QLabel(p.get("title", "Untitled"))
            title_lbl.setStyleSheet("font-weight: bold; font-size: 13px; color: #ffffff;")
            top_row.addWidget(title_lbl)
            top_row.addStretch()

            brand_tag = QLabel(p.get("brand", "ALL"))
            brand_tag.setStyleSheet("font-size: 9px; font-weight: bold; background: #1e293b; color: #38bdf8; padding: 2px 6px; border-radius: 3px;")
            top_row.addWidget(brand_tag)
            layout.addLayout(top_row)

            model_lbl = QLabel(f"Model: {p.get('model', 'Universal')} | {p.get('board_code', '')}")
            model_lbl.setStyleSheet("font-size: 11px; color: #94a3b8;")
            layout.addWidget(model_lbl)

            symp_lbl = QLabel(f"Issue: {p.get('symptom', 'N/A')}")
            symp_lbl.setStyleSheet("font-size: 10px; color: #fde047; font-style: italic;")
            layout.addWidget(symp_lbl)

            self.list_patches.addItem(item)
            self.list_patches.setItemWidget(item, w)

        if len(patches) > 0:
            self.list_patches.setCurrentRow(0)
        else:
            self.selected_patch = None
            self.lbl_patch_title.setText("No patches matching filter")
            self.lbl_patch_meta.setText("Try selecting 'All Brands' or clearing search.")
            self.lbl_symptom.setText("N/A")
            self.txt_description.clear()
            self.btn_execute.setEnabled(False)

    def on_patch_selected(self):
        items = self.list_patches.selectedItems()
        if not items:
            return
        p = items[0].data(Qt.ItemDataRole.UserRole)
        if not p:
            return

        self.selected_patch = p
        self.lbl_patch_title.setText(p.get("title", ""))
        self.lbl_patch_meta.setText(
            f"Brand: {p.get('brand')} | Model: {p.get('model')} | Board: {p.get('board_code')} | Version: {p.get('version', '1.0')}"
        )
        self.lbl_symptom.setText(p.get("symptom", "N/A"))
        self.txt_description.setText(
            f"Description:\n{p.get('description', '')}\n\nAuthor: {p.get('author', 'R1 LAB')}\nScript: {p.get('script_file', '')}"
        )

        self.update_verification_status()

    def update_verification_status(self):
        """Checks if current file matches selected patch."""
        if not self.selected_patch:
            self.lbl_verify_status.setText("Verification: Please select a patch")
            self.lbl_verify_status.setStyleSheet("font-size: 11px; padding: 6px 10px; border-radius: 4px; background: #101927; color: #7e8f9f;")
            self.btn_execute.setEnabled(False)
            return

        if not self.current_file or not os.path.exists(self.current_file):
            self.lbl_verify_status.setText("Verification: Please select or drop a target BIOS file")
            self.lbl_verify_status.setStyleSheet("font-size: 11px; padding: 6px 10px; border-radius: 4px; background: #181d24; color: #eab308;")
            self.btn_execute.setEnabled(False)
            return

        # Pre-verify file
        try:
            with open(self.current_file, "rb") as f:
                data = bytearray(f.read())
            ok, msg = self.engine.verify_patch(self.selected_patch, data)
            if ok:
                self.lbl_verify_status.setText(f"✓ Ready: {msg}")
                self.lbl_verify_status.setStyleSheet("font-size: 11px; padding: 6px 10px; border-radius: 4px; background: #0c2b20; color: #4ade80; border: 1px solid #16a34a;")
                self.btn_execute.setEnabled(True)
            else:
                self.lbl_verify_status.setText(f"⚠ Mismatch: {msg}")
                self.lbl_verify_status.setStyleSheet("font-size: 11px; padding: 6px 10px; border-radius: 4px; background: #2d1818; color: #f87171; border: 1px solid #dc2626;")
                self.btn_execute.setEnabled(False)
        except Exception as e:
            self.lbl_verify_status.setText(f"Error checking file: {e}")
            self.btn_execute.setEnabled(False)

    def execute_patch_action(self):
        if not self.selected_patch or not self.current_file:
            return

        patch_title = self.selected_patch.get("title")
        model = self.selected_patch.get("model")
        
        reply = QMessageBox.question(
            self,
            "Confirm AutoPatch Execution",
            f"Are you ready to apply patch:\n\n'{patch_title}' for {model}?\n\nTarget File: {os.path.basename(self.current_file)}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.log(f"Starting execution of '{patch_title}' on {os.path.basename(self.current_file)}...")
        self.btn_execute.setEnabled(False)

        backup = self.chk_backup.isChecked()
        ok, out_path, msg = self.engine.execute_patch(self.selected_patch, self.current_file, create_backup=backup)

        if ok:
            self.log(f"SUCCESS: {msg}", color="#4ade80")
            self.log(f"Output saved to: {out_path}", color="#38bdf8")
            QMessageBox.information(
                self,
                "AutoPatch Completed",
                f"Patch successfully applied!\n\nMessage: {msg}\n\nSaved to:\n{out_path}\n\nFolder opened automatically in Explorer."
            )
        else:
            self.log(f"FAILED: {msg}", color="#f87171")
            QMessageBox.critical(
                self,
                "AutoPatch Error",
                f"Could not apply patch:\n\n{msg}"
            )

        self.btn_execute.setEnabled(True)

    def sync_cloud_patches(self):
        self.log("Syncing patch catalog with GitHub...")
        ok, msg = self.engine.sync_from_github()
        if ok:
            self.log(msg, color="#4ade80")
            self.refresh_patch_list()
            QMessageBox.information(self, "Cloud Sync", msg)
        else:
            self.log(msg, color="#f87171")
            QMessageBox.warning(self, "Cloud Sync", f"Sync notice:\n{msg}")


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    dlg = AutoPatchDialog()
    dlg.show()
    sys.exit(app.exec())

