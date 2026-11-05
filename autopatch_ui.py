"""
R1 BIOS TOOL — AUTOPATCH UI (CLEAN & MODERN)
===========================================
Streamlined, distraction-free interface for dynamic BIOS patch browsing,
fully automated brand detection, safety verification, and one-click patching.
"""

import os
import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QFrame, QTextEdit, QFileDialog,
    QCheckBox, QMessageBox, QSplitter, QWidget, QComboBox
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
QFrame#FileDropFrame {
    background-color: #0c141f;
    border: 1px dashed #00adb5;
    border-radius: 8px;
    padding: 6px 12px;
}
QFrame#FileDropFrame:hover {
    border: 1px dashed #00f3ff;
    background-color: #0e1927;
}
QLabel {
    color: #cbd5e1;
}
QLineEdit {
    background-color: #080c12;
    border: 1px solid #1e293b;
    border-radius: 6px;
    padding: 7px 10px;
    color: #00f3ff;
    font-size: 12px;
}
QLineEdit:focus {
    border: 1px solid #00f3ff;
}
QComboBox {
    background-color: #0e1520;
    color: #00f3ff;
    border: 1px solid #1e293b;
    border-radius: 6px;
    padding: 5px 10px;
    font-size: 11px;
    font-weight: bold;
    min-width: 130px;
}
QComboBox:hover {
    border-color: #00adb5;
}
QComboBox QAbstractItemView {
    background-color: #0e1520;
    color: #e2e8f0;
    selection-background-color: #00adb5;
    selection-color: #0b1017;
    border: 1px solid #1e293b;
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
    padding: 6px 8px;
}
QListWidget::item:hover {
    background-color: #131d2b;
    border: 1px solid #00adb5;
}
QListWidget::item:selected {
    background-color: #162438;
    border: 1px solid #00f3ff;
}
QPushButton#ExecuteBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00adb5, stop:1 #00f3ff);
    color: #0b1017;
    font-weight: bold;
    font-size: 13px;
    letter-spacing: 1px;
    border: none;
    border-radius: 6px;
    padding: 12px 24px;
}
QPushButton#ExecuteBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00c4cc, stop:1 #38bdf8);
}
QPushButton#ExecuteBtn:disabled {
    background: #17212e;
    color: #475569;
}
QPushButton#SecondaryBtn {
    background-color: #131d2b;
    color: #cbd5e1;
    border: 1px solid #1e293b;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 11px;
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
    font-family: 'Segoe UI', sans-serif;
    font-size: 11px;
    padding: 8px;
}
QCheckBox {
    color: #cbd5e1;
    font-size: 11px;
}
QCheckBox::indicator {
    width: 15px;
    height: 15px;
    border-radius: 3px;
    border: 1px solid #334155;
    background: #0e1520;
}
QCheckBox::indicator:checked {
    background: #00f3ff;
    border-color: #00f3ff;
}
"""


class DropAreaWidget(QFrame):
    """Clean drop area for BIOS file."""
    file_dropped = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("FileDropFrame")
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
                self.file_dropped.emit(file_path)
                break


class AutoPatchDialog(QDialog):
    def __init__(self, parent=None, initial_file=None, dmi_hint=None):
        super().__init__(parent)
        self.setWindowTitle("AutoPatch — Smart BIOS Firmware Fixer")
        self.resize(1000, 640)
        self.setMinimumSize(880, 560)
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
        root_layout.setContentsMargins(18, 14, 18, 14)
        root_layout.setSpacing(10)

        # ── 1. Header (Clean & Minimalist) ─────────────────────────────────
        header_row = QHBoxLayout()
        title_box = QVBoxLayout()
        title_lbl = QLabel("AUTO PATCH")
        title_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #00f3ff; letter-spacing: 1.5px;")
        sub_lbl = QLabel("Automated brand matching and targeted BIOS problem solver")
        sub_lbl.setStyleSheet("font-size: 11px; color: #64748b;")
        title_box.addWidget(title_lbl)
        title_box.addWidget(sub_lbl)
        header_row.addLayout(title_box)

        header_row.addStretch()

        # Cloud sync button
        btn_sync = QPushButton("☁ Sync Cloud")
        btn_sync.setObjectName("SecondaryBtn")
        btn_sync.clicked.connect(self.sync_cloud_patches)
        header_row.addWidget(btn_sync)

        root_layout.addLayout(header_row)

        # ── 2. Top File Bar with Auto-Detection & Discreet Filter ──────────
        self.drop_bar = DropAreaWidget()
        self.drop_bar.file_dropped.connect(self.on_file_selected)
        bar_layout = QHBoxLayout(self.drop_bar)
        bar_layout.setContentsMargins(8, 4, 8, 4)
        bar_layout.setSpacing(10)

        # File Icon & Path / Prompt
        self.lbl_file_display = QLabel("Drop BIOS file here or click Browse...")
        self.lbl_file_display.setStyleSheet("font-size: 12px; color: #94a3b8;")
        bar_layout.addWidget(self.lbl_file_display, stretch=3)

        btn_browse = QPushButton("Browse File...")
        btn_browse.setObjectName("SecondaryBtn")
        btn_browse.clicked.connect(self.browse_file)
        bar_layout.addWidget(btn_browse)

        # Vertical separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: #1a2536;")
        bar_layout.addWidget(sep)

        # Auto-Detected Brand Badge
        self.lbl_brand_badge = QLabel("Target: No File")
        self.lbl_brand_badge.setStyleSheet(
            "font-size: 11px; font-weight: bold; color: #64748b; background: #080c12; padding: 4px 10px; border-radius: 4px; border: 1px solid #1a2536;"
        )
        bar_layout.addWidget(self.lbl_brand_badge)

        # Discreet Internal Filter Dropdown (Tucked inside, no outside clutter!)
        lbl_filter_tag = QLabel("Filter:")
        lbl_filter_tag.setStyleSheet("font-size: 11px; color: #64748b;")
        bar_layout.addWidget(lbl_filter_tag)

        self.cmb_filter = QComboBox()
        self.cmb_filter.addItems([
            "Auto (Detected)",
            "All Brands",
            "Dell",
            "Lenovo",
            "HP",
            "Asus",
            "Acer",
            "Universal"
        ])
        self.cmb_filter.currentIndexChanged.connect(self.refresh_patch_list)
        bar_layout.addWidget(self.cmb_filter)

        root_layout.addWidget(self.drop_bar)

        # ── 3. Main Splitter (Left: Patch List, Right: Details & Patch) ─────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background: #1a2536; width: 2px; }")

        # LEFT PANE: Patch List & Search
        left_card = QFrame()
        left_card.setObjectName("Card")
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(6)

        # Search Bar & Count
        search_row = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Search issue, model, or board code...")
        self.txt_search.textChanged.connect(self.refresh_patch_list)
        search_row.addWidget(self.txt_search)

        self.lbl_count = QLabel("0 available")
        self.lbl_count.setStyleSheet("font-size: 10px; color: #64748b;")
        search_row.addWidget(self.lbl_count)
        left_layout.addLayout(search_row)

        # Patch List
        self.list_patches = QListWidget()
        self.list_patches.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_patches.itemSelectionChanged.connect(self.on_patch_selected)
        left_layout.addWidget(self.list_patches)

        splitter.addWidget(left_card)
        splitter.setStretchFactor(0, 4)

        # RIGHT PANE: Details, Safety Check & Patch Action
        right_card = QFrame()
        right_card.setObjectName("Card")
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(16, 14, 16, 14)
        right_layout.setSpacing(8)

        # Patch Title
        self.lbl_patch_title = QLabel("Select a patch from the list")
        self.lbl_patch_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        self.lbl_patch_title.setWordWrap(True)
        right_layout.addWidget(self.lbl_patch_title)

        # Meta tags row
        self.lbl_patch_meta = QLabel("Brand: —  |  Model: —  |  Author: —")
        self.lbl_patch_meta.setStyleSheet("font-size: 11px; color: #38bdf8;")
        right_layout.addWidget(self.lbl_patch_meta)

        # Clean Unified Issue & Details Card
        lbl_symp_head = QLabel("PROBLEM SYMPTOM:")
        lbl_symp_head.setStyleSheet("font-size: 10px; font-weight: bold; color: #eab308; letter-spacing: 0.5px; margin-top: 4px;")
        right_layout.addWidget(lbl_symp_head)

        self.lbl_symptom = QLabel("N/A")
        self.lbl_symptom.setWordWrap(True)
        self.lbl_symptom.setStyleSheet(
            "font-size: 11px; color: #fef08a; background: #131a15; padding: 7px 10px; border-radius: 4px; border-left: 3px solid #eab308;"
        )
        right_layout.addWidget(self.lbl_symptom)

        lbl_desc_head = QLabel("HOW IT WORKS:")
        lbl_desc_head.setStyleSheet("font-size: 10px; font-weight: bold; color: #94a3b8; letter-spacing: 0.5px; margin-top: 4px;")
        right_layout.addWidget(lbl_desc_head)

        self.txt_description = QTextEdit()
        self.txt_description.setReadOnly(True)
        self.txt_description.setFixedHeight(85)
        right_layout.addWidget(self.txt_description)

        # Safety Verification Banner
        self.lbl_verify_status = QLabel("Verification: Please select a patch and target file")
        self.lbl_verify_status.setStyleSheet("font-size: 11px; padding: 7px 10px; border-radius: 4px; background: #101927; color: #7e8f9f;")
        self.lbl_verify_status.setWordWrap(True)
        right_layout.addWidget(self.lbl_verify_status)

        # Backup Checkbox
        self.chk_backup = QCheckBox("Create automatic backup before patching (_ORIGINAL_BACKUP.bin)")
        self.chk_backup.setChecked(True)
        right_layout.addWidget(self.chk_backup)

        right_layout.addStretch()

        # Big Action Button
        self.btn_execute = QPushButton("⚡ EXECUTE AUTO PATCH")
        self.btn_execute.setObjectName("ExecuteBtn")
        self.btn_execute.setEnabled(False)
        self.btn_execute.clicked.connect(self.execute_patch_action)
        right_layout.addWidget(self.btn_execute)

        splitter.addWidget(right_card)
        splitter.setStretchFactor(1, 5)

        root_layout.addWidget(splitter)

        # ── 4. Bottom Sleek Status Bar ─────────────────────────────────────
        self.lbl_status = QLabel("Ready.")
        self.lbl_status.setStyleSheet("font-size: 11px; color: #64748b; padding-left: 2px;")
        root_layout.addWidget(self.lbl_status)

    def initialize_state(self):
        if self.current_file and os.path.exists(self.current_file):
            self.on_file_selected(self.current_file)
        else:
            self.refresh_patch_list()

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select BIOS Image File", "",
            "BIOS Files (*.bin *.rom *.fd *.cap *.wph);;All Files (*.*)"
        )
        if file_path:
            self.on_file_selected(file_path)

    def on_file_selected(self, file_path: str):
        clean_path = file_path.strip().strip('"')
        if not os.path.isfile(clean_path):
            return

        self.current_file = clean_path
        file_name = os.path.basename(clean_path)
        file_size_mb = os.path.getsize(clean_path) / (1024 * 1024)

        # Update file label
        self.lbl_file_display.setText(f"📁 {file_name} ({file_size_mb:.1f} MB)")
        self.lbl_file_display.setStyleSheet("font-size: 12px; font-weight: bold; color: #00f3ff;")

        # Run Brand Detection
        brand, model = self.engine.detect_brand(clean_path, self.dmi_hint)
        self.detected_brand = brand
        self.detected_model = model or ""

        if brand != "UNKNOWN":
            txt = f"🎯 {brand}"
            if model:
                txt += f" ({model})"
            self.lbl_brand_badge.setText(txt)
            self.lbl_brand_badge.setStyleSheet(
                "font-size: 11px; font-weight: bold; color: #00f3ff; background: #0c202a; padding: 4px 10px; border-radius: 4px; border: 1px solid #00f3ff;"
            )
            self.lbl_status.setText(f"Auto-detected brand: {brand}. List automatically filtered.")
        else:
            self.lbl_brand_badge.setText("Target: Unknown")
            self.lbl_brand_badge.setStyleSheet(
                "font-size: 11px; font-weight: bold; color: #a855f7; background: #1a1625; padding: 4px 10px; border-radius: 4px; border: 1px solid #a855f7;"
            )
            self.lbl_status.setText("Brand could not be determined. Showing all available patches.")

        # Ensure filter is on "Auto (Detected)"
        self.cmb_filter.setCurrentIndex(0)
        self.refresh_patch_list()
        self.update_verification_status()

    def get_selected_brand_filter(self) -> str:
        idx = self.cmb_filter.currentIndex()
        if idx == 0:  # Auto (Detected)
            return self.detected_brand if self.detected_brand != "UNKNOWN" else "ALL"
        elif idx == 1:  # All Brands
            return "ALL"
        else:
            return self.cmb_filter.currentText().strip().upper()

    def refresh_patch_list(self):
        active_brand = self.get_selected_brand_filter()
        query = self.txt_search.text().strip()

        patches = self.engine.get_filtered_patches(brand=active_brand, search_query=query)
        self.list_patches.clear()
        self.lbl_count.setText(f"{len(patches)} patch{'es' if len(patches) != 1 else ''}")

        for p in patches:
            item = QListWidgetItem()
            item.setSizeHint(QSize(240, 56))
            item.setData(Qt.ItemDataRole.UserRole, p)

            # Compact custom widget
            w = QWidget()
            layout = QVBoxLayout(w)
            layout.setContentsMargins(4, 3, 4, 3)
            layout.setSpacing(2)

            top_row = QHBoxLayout()
            title_lbl = QLabel(p.get("title", "Untitled"))
            title_lbl.setStyleSheet("font-weight: bold; font-size: 12px; color: #ffffff;")
            top_row.addWidget(title_lbl)
            top_row.addStretch()

            brand_tag = QLabel(p.get("brand", "ALL"))
            brand_tag.setStyleSheet("font-size: 9px; font-weight: bold; background: #132030; color: #38bdf8; padding: 1px 5px; border-radius: 3px;")
            top_row.addWidget(brand_tag)
            layout.addLayout(top_row)

            # Sub line: Model & Symptom preview
            sub_text = f"{p.get('model', 'Universal')}  •  {p.get('symptom', '')}"
            if len(sub_text) > 55:
                sub_text = sub_text[:52] + "..."
            sub_lbl = QLabel(sub_text)
            sub_lbl.setStyleSheet("font-size: 10px; color: #94a3b8;")
            layout.addWidget(sub_lbl)

            self.list_patches.addItem(item)
            self.list_patches.setItemWidget(item, w)

        if len(patches) > 0:
            self.list_patches.setCurrentRow(0)
        else:
            self.selected_patch = None
            self.lbl_patch_title.setText("No patches available for this filter")
            self.lbl_patch_meta.setText("Select 'All Brands' in the filter dropdown above to see other patches.")
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
            f"Brand: {p.get('brand')}  |  Model: {p.get('model')}  |  Board: {p.get('board_code')}  |  v{p.get('version', '1.0')}"
        )
        self.lbl_symptom.setText(p.get("symptom", "N/A"))
        self.txt_description.setText(
            f"{p.get('description', '')}\n\n[Script: {p.get('script_file', '')} | Author: {p.get('author', 'R1 LAB')}]"
        )

        self.update_verification_status()

    def update_verification_status(self):
        if not self.selected_patch:
            self.lbl_verify_status.setText("Verification: Please select a patch from the list")
            self.lbl_verify_status.setStyleSheet("font-size: 11px; padding: 7px 10px; border-radius: 4px; background: #101927; color: #7e8f9f;")
            self.btn_execute.setEnabled(False)
            return

        if not self.current_file or not os.path.exists(self.current_file):
            self.lbl_verify_status.setText("Verification: Please drop or select a target BIOS file above")
            self.lbl_verify_status.setStyleSheet("font-size: 11px; padding: 7px 10px; border-radius: 4px; background: #181d24; color: #eab308;")
            self.btn_execute.setEnabled(False)
            return

        # Pre-verify signature
        try:
            with open(self.current_file, "rb") as f:
                data = bytearray(f.read())
            ok, msg = self.engine.verify_patch(self.selected_patch, data)
            if ok:
                self.lbl_verify_status.setText(f"✓ Ready: {msg}")
                self.lbl_verify_status.setStyleSheet(
                    "font-size: 11px; padding: 7px 10px; border-radius: 4px; background: #0c2b20; color: #4ade80; border: 1px solid #16a34a;"
                )
                self.btn_execute.setEnabled(True)
            else:
                self.lbl_verify_status.setText(f"⚠ Mismatch: {msg}")
                self.lbl_verify_status.setStyleSheet(
                    "font-size: 11px; padding: 7px 10px; border-radius: 4px; background: #2d1818; color: #f87171; border: 1px solid #dc2626;"
                )
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
            "Confirm AutoPatch",
            f"Are you ready to apply:\n\n'{patch_title}' for {model}?\n\nTarget File: {os.path.basename(self.current_file)}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.lbl_status.setText(f"Applying '{patch_title}'...")
        self.btn_execute.setEnabled(False)

        backup = self.chk_backup.isChecked()
        ok, out_path, msg = self.engine.execute_patch(self.selected_patch, self.current_file, create_backup=backup)

        if ok:
            self.lbl_status.setText(f"SUCCESS: {msg}")
            QMessageBox.information(
                self,
                "AutoPatch Completed",
                f"Patch successfully applied!\n\nDetails: {msg}\n\nSaved to:\n{out_path}\n\nTarget folder opened automatically."
            )
        else:
            self.lbl_status.setText(f"FAILED: {msg}")
            QMessageBox.critical(
                self,
                "AutoPatch Error",
                f"Could not apply patch:\n\n{msg}"
            )

        self.btn_execute.setEnabled(True)

    def sync_cloud_patches(self):
        self.lbl_status.setText("Syncing patch catalog with GitHub...")
        ok, msg = self.engine.sync_from_github()
        if ok:
            self.lbl_status.setText(msg)
            self.refresh_patch_list()
            QMessageBox.information(self, "Cloud Sync", msg)
        else:
            self.lbl_status.setText(f"Sync error: {msg}")
            QMessageBox.warning(self, "Cloud Sync", f"Sync notice:\n{msg}")


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    dlg = AutoPatchDialog()
    dlg.show()
    sys.exit(app.exec())
