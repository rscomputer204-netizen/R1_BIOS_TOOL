"""
R1 BIOS TOOL — AUTOPATCH UI (LOCKED LIST & BIG DROP ZONE)
=========================================================
1. Top Section: 2-line patch banner (Title on line 1, Description on line 2).
2. Left Section: Locked fixed-width patch list (cannot be resized or shrunk).
3. Right Section: Massive interactive Drag & Drop box (clickable + drop),
   with the Execute button enabled ONLY when both file and patch are loaded.
"""

import os
import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QFrame, QFileDialog,
    QCheckBox, QMessageBox, QWidget, QComboBox
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QColor, QFont, QCursor, QDragEnterEvent, QDropEvent

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
QFrame#TopBannerFrame {
    background-color: #0c141f;
    border: 1px solid #1a2536;
    border-radius: 8px;
    padding: 8px 14px;
}
QFrame#BigDropZone {
    background-color: #080d14;
    border: 2px dashed #00adb5;
    border-radius: 12px;
}
QFrame#BigDropZone:hover {
    border: 2px dashed #00f3ff;
    background-color: #0c1624;
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
    min-width: 120px;
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
    padding: 8px;
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
    font-size: 14px;
    letter-spacing: 1px;
    border: none;
    border-radius: 8px;
    padding: 14px 24px;
}
QPushButton#ExecuteBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00c4cc, stop:1 #38bdf8);
}
QPushButton#ExecuteBtn:disabled {
    background: #141b24;
    color: #475569;
    border: 1px solid #1e293b;
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


class ClickableDropZone(QFrame):
    """Large interactive drop zone that also opens file dialog when clicked."""
    file_dropped = Signal(str)
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("BigDropZone")
        self.setAcceptDrops(True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

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

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(e)


class AutoPatchDialog(QDialog):
    def __init__(self, parent=None, initial_file=None, dmi_hint=None):
        super().__init__(parent)
        self.setWindowTitle("AutoPatch — Smart BIOS Firmware Fixer")
        self.resize(1060, 680)
        self.setMinimumSize(940, 600)
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
        root_layout.setSpacing(12)

        # ── 1. Top Bar: Title & Cloud Sync ─────────────────────────────────
        top_row = QHBoxLayout()
        title_box = QVBoxLayout()
        title_lbl = QLabel("AUTO PATCH")
        title_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #00f3ff; letter-spacing: 1.5px;")
        sub_lbl = QLabel("Automated brand matching and targeted BIOS problem solver")
        sub_lbl.setStyleSheet("font-size: 11px; color: #64748b;")
        title_box.addWidget(title_lbl)
        title_box.addWidget(sub_lbl)
        top_row.addLayout(title_box)

        top_row.addStretch()

        # Cloud sync button
        btn_sync = QPushButton("☁ Sync Cloud")
        btn_sync.setObjectName("SecondaryBtn")
        btn_sync.clicked.connect(self.sync_cloud_patches)
        top_row.addWidget(btn_sync)

        root_layout.addLayout(top_row)

        # ── 2. Top Info Banner: 2 Lines for Selected Patch Information ─────
        # (This replaces the old drop bar, as requested by the user!)
        self.banner_frame = QFrame()
        self.banner_frame.setObjectName("TopBannerFrame")
        banner_layout = QHBoxLayout(self.banner_frame)
        banner_layout.setContentsMargins(14, 8, 14, 8)
        banner_layout.setSpacing(12)

        patch_info_vbox = QVBoxLayout()
        patch_info_vbox.setSpacing(3)

        # Line 1: Patch Title & Brand Tag
        self.lbl_top_title = QLabel("Select a patch from the list")
        self.lbl_top_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #00f3ff;")
        patch_info_vbox.addWidget(self.lbl_top_title)

        # Line 2: Patch 1-line Description / How it works
        self.lbl_top_desc = QLabel("Choose any patch on the left to inspect and apply to your BIOS image.")
        self.lbl_top_desc.setStyleSheet("font-size: 11px; color: #94a3b8;")
        self.lbl_top_desc.setWordWrap(True)
        patch_info_vbox.addWidget(self.lbl_top_desc)

        banner_layout.addLayout(patch_info_vbox, stretch=4)

        # Right side of banner: Target detected badge & discreet filter
        right_meta_layout = QHBoxLayout()
        right_meta_layout.setSpacing(8)

        self.lbl_brand_badge = QLabel("Target: No File")
        self.lbl_brand_badge.setStyleSheet(
            "font-size: 11px; font-weight: bold; color: #64748b; background: #080c12; padding: 5px 10px; border-radius: 4px; border: 1px solid #1a2536;"
        )
        right_meta_layout.addWidget(self.lbl_brand_badge)

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
        right_meta_layout.addWidget(self.cmb_filter)

        banner_layout.addLayout(right_meta_layout)
        root_layout.addWidget(self.banner_frame)

        # ── 3. Main Center Split (Left: Locked 380px, Right: Big Drop Zone) ─
        main_h_layout = QHBoxLayout()
        main_h_layout.setSpacing(14)

        # ── LEFT PANEL: Fixed & Locked Width (Cannot be resized) ───────────
        left_card = QFrame()
        left_card.setObjectName("Card")
        left_card.setFixedWidth(380)  # <-- LOCKED SIZE AS REQUESTED
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

        main_h_layout.addWidget(left_card)

        # ── RIGHT PANEL: Big Interactive Drop Zone & Execute Button ────────
        right_card = QFrame()
        right_card.setObjectName("Card")
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(12)

        # Big Interactive Drop Area
        self.drop_zone = ClickableDropZone()
        self.drop_zone.file_dropped.connect(self.on_file_selected)
        self.drop_zone.clicked.connect(self.browse_file)

        drop_vbox = QVBoxLayout(self.drop_zone)
        drop_vbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_vbox.setSpacing(8)

        # Icon
        self.lbl_drop_icon = QLabel("📥")
        self.lbl_drop_icon.setStyleSheet("font-size: 42px; background: transparent;")
        self.lbl_drop_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_vbox.addWidget(self.lbl_drop_icon)

        # Main text
        self.lbl_drop_title = QLabel("DRAG & DROP BIOS FILE HERE")
        self.lbl_drop_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #00f3ff; letter-spacing: 0.5px; background: transparent;")
        self.lbl_drop_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_vbox.addWidget(self.lbl_drop_title)

        # Subtitle
        self.lbl_drop_sub = QLabel("or click anywhere inside this box to browse from your computer")
        self.lbl_drop_sub.setStyleSheet("font-size: 11px; color: #64748b; background: transparent;")
        self.lbl_drop_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_vbox.addWidget(self.lbl_drop_sub)

        # Loaded File Details Box (Shown when file is loaded)
        self.file_details_box = QFrame()
        self.file_details_box.setStyleSheet(
            "background: #0b1522; border: 1px solid #1a324b; border-radius: 6px; padding: 6px 14px; margin-top: 10px;"
        )
        self.file_details_box.hide()
        f_box_layout = QVBoxLayout(self.file_details_box)
        f_box_layout.setSpacing(3)
        self.lbl_loaded_filename = QLabel("📁 No File")
        self.lbl_loaded_filename.setStyleSheet("font-size: 13px; font-weight: bold; color: #00f3ff; background: transparent;")
        f_box_layout.addWidget(self.lbl_loaded_filename)
        self.lbl_loaded_meta = QLabel("")
        self.lbl_loaded_meta.setStyleSheet("font-size: 11px; color: #38bdf8; background: transparent;")
        f_box_layout.addWidget(self.lbl_loaded_meta)
        drop_vbox.addWidget(self.file_details_box)

        right_layout.addWidget(self.drop_zone, stretch=1)

        # Safety Verification Banner
        self.lbl_verify_status = QLabel("Status: Please select a patch and provide a BIOS file")
        self.lbl_verify_status.setStyleSheet("font-size: 11px; padding: 7px 10px; border-radius: 4px; background: #101927; color: #7e8f9f;")
        self.lbl_verify_status.setWordWrap(True)
        right_layout.addWidget(self.lbl_verify_status)

        # Backup Checkbox
        self.chk_backup = QCheckBox("Create automatic backup before patching (_ORIGINAL_BACKUP.bin)")
        self.chk_backup.setChecked(True)
        right_layout.addWidget(self.chk_backup)

        # Big Action Button (Enabled ONLY when both file and patch are ready)
        self.btn_execute = QPushButton("⚡ EXECUTE AUTO PATCH")
        self.btn_execute.setObjectName("ExecuteBtn")
        self.btn_execute.setEnabled(False)  # <-- DISABLED BY DEFAULT
        self.btn_execute.clicked.connect(self.execute_patch_action)
        right_layout.addWidget(self.btn_execute)

        main_h_layout.addWidget(right_card, stretch=1)
        root_layout.addLayout(main_h_layout, stretch=1)

        # ── 4. Bottom Status Bar ───────────────────────────────────────────
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

        # Update Big Drop Zone visuals
        self.lbl_drop_title.setText("FILE READY FOR PATCHING")
        self.lbl_drop_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #4ade80; letter-spacing: 0.5px; background: transparent;")
        self.lbl_drop_sub.setText("Click anywhere to change or choose another file")
        self.lbl_drop_icon.setText("✅")

        # Show loaded file details card
        self.file_details_box.show()
        self.lbl_loaded_filename.setText(f"📁 {file_name}")

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
                "font-size: 11px; font-weight: bold; color: #00f3ff; background: #0c202a; padding: 5px 10px; border-radius: 4px; border: 1px solid #00f3ff;"
            )
            self.lbl_loaded_meta.setText(f"Size: {file_size_mb:.2f} MB  •  Detected Platform: {brand} {model}")
            self.lbl_status.setText(f"Auto-detected brand: {brand}. Patch list filtered automatically.")
        else:
            self.lbl_brand_badge.setText("Target: Unknown")
            self.lbl_brand_badge.setStyleSheet(
                "font-size: 11px; font-weight: bold; color: #a855f7; background: #1a1625; padding: 5px 10px; border-radius: 4px; border: 1px solid #a855f7;"
            )
            self.lbl_loaded_meta.setText(f"Size: {file_size_mb:.2f} MB  •  Platform: Unknown")
            self.lbl_status.setText("Brand could not be determined automatically. Showing all patches.")

        # Refresh patches with Auto filter
        self.cmb_filter.setCurrentIndex(0)
        self.refresh_patch_list()
        self.update_verification_and_button_state()

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
        self.lbl_count.setText(f"{len(patches)} available")

        for p in patches:
            item = QListWidgetItem()
            item.setSizeHint(QSize(350, 62))
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
            brand_tag.setStyleSheet("font-size: 9px; font-weight: bold; background: #132030; color: #38bdf8; padding: 2px 6px; border-radius: 3px;")
            top_row.addWidget(brand_tag)
            layout.addLayout(top_row)

            # Sub line: Model & Symptom preview
            sub_text = f"{p.get('model', 'Universal')}  •  {p.get('symptom', '')}"
            if len(sub_text) > 52:
                sub_text = sub_text[:49] + "..."
            sub_lbl = QLabel(sub_text)
            sub_lbl.setStyleSheet("font-size: 10px; color: #94a3b8;")
            layout.addWidget(sub_lbl)

            self.list_patches.addItem(item)
            self.list_patches.setItemWidget(item, w)

        if len(patches) > 0:
            self.list_patches.setCurrentRow(0)
        else:
            self.selected_patch = None
            self.lbl_top_title.setText("No patches available for this filter")
            self.lbl_top_desc.setText("Select 'All Brands' in the dropdown above to view all patches.")
            self.update_verification_and_button_state()

    def on_patch_selected(self):
        items = self.list_patches.selectedItems()
        if not items:
            return
        p = items[0].data(Qt.ItemDataRole.UserRole)
        if not p:
            return

        self.selected_patch = p

        # ── Update Top 2-Line Banner ──
        # Line 1: Title & Brand/Model
        brand = p.get('brand', 'Universal')
        model = p.get('model', '')
        meta_str = f"[{brand} - {model}]" if model else f"[{brand}]"
        self.lbl_top_title.setText(f"{p.get('title', '')}  {meta_str}")

        # Line 2: 1-line description / how it works
        desc_line = p.get('description', '') or p.get('symptom', '') or "Standard binary patch."
        # Keep it clean and concise
        first_line = desc_line.split('\n')[0].strip()
        self.lbl_top_desc.setText(f"Action: {first_line}")

        self.update_verification_and_button_state()

    def update_verification_and_button_state(self):
        """
        Validation Rule:
        Execute button is enabled ONLY when BOTH a file is provided AND a patch is selected.
        """
        has_patch = self.selected_patch is not None
        has_file = bool(self.current_file and os.path.exists(self.current_file))

        if not has_patch and not has_file:
            self.lbl_verify_status.setText("Status: Please select a patch and drop a BIOS file")
            self.lbl_verify_status.setStyleSheet("font-size: 11px; padding: 7px 10px; border-radius: 4px; background: #101927; color: #7e8f9f;")
            self.btn_execute.setEnabled(False)
            return

        if not has_patch:
            self.lbl_verify_status.setText("Status: File loaded. Please select a patch from the left list")
            self.lbl_verify_status.setStyleSheet("font-size: 11px; padding: 7px 10px; border-radius: 4px; background: #181d24; color: #eab308;")
            self.btn_execute.setEnabled(False)
            return

        if not has_file:
            self.lbl_verify_status.setText("Status: Patch selected. Please drop or browse a target BIOS file")
            self.lbl_verify_status.setStyleSheet("font-size: 11px; padding: 7px 10px; border-radius: 4px; background: #181d24; color: #eab308;")
            self.btn_execute.setEnabled(False)
            return

        # Both patch and file are present! Pre-verify signature
        try:
            with open(self.current_file, "rb") as f:
                data = bytearray(f.read())
            ok, msg = self.engine.verify_patch(self.selected_patch, data)
            if ok:
                self.lbl_verify_status.setText(f"✓ Ready: {msg}")
                self.lbl_verify_status.setStyleSheet(
                    "font-size: 11px; padding: 7px 10px; border-radius: 4px; background: #0c2b20; color: #4ade80; border: 1px solid #16a34a;"
                )
                self.btn_execute.setEnabled(True)  # <-- ENABLED!
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
