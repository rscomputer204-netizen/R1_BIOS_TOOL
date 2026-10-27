"""
merge_dialog.py - BIOS Merge Tool Dialog
Allows the user to select two firmware/binary files (via browse or drag-and-drop)
and merge them into a single output file.

After merge completes in memory, a Save As dialog automatically opens
with the Downloads folder pre-selected and a default filename.
"""

import os
import threading
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFileDialog, QFrame, QMessageBox,
    QProgressBar, QComboBox, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QObject


# -----------------------------------------------------------------
#  Worker signal bridge (thread-safe UI updates)
# -----------------------------------------------------------------
class _WorkerBridge(QObject):
    # finished now carries the raw merged bytes (as bytes object via a holder)
    ready    = Signal(object)  # merged bytes object wrapper
    failed   = Signal(str)     # error message
    progress = Signal(int)     # 0-100


class _BytesHolder:
    """Simple wrapper to pass bytes through a Signal(object)."""
    def __init__(self, data: bytes):
        self.data = data


# -----------------------------------------------------------------
#  Drop Zone Widget
# -----------------------------------------------------------------
class _DropZone(QFrame):
    """A drag-and-drop capable file drop zone."""

    file_dropped = Signal(str)

    IDLE_STYLE = """
        QFrame {
            background-color: #171a1d;
            border: 2px dashed #2d363f;
            border-radius: 10px;
            min-height: 130px;
        }
    """
    HOVER_STYLE = """
        QFrame {
            background-color: #1c2228;
            border: 2px dashed #0ef6fd;
            border-radius: 10px;
            min-height: 130px;
        }
    """
    LOADED_STYLE = """
        QFrame {
            background-color: #172221;
            border: 2px solid #2ac4db;
            border-radius: 10px;
            min-height: 130px;
        }
    """

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setStyleSheet(self.IDLE_STYLE)

        self._file_path = ""

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(6)

        self._icon_lbl = QLabel("📂")
        self._icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_lbl.setStyleSheet(
            "font-size: 30px; background: transparent; border: none;"
        )

        self._title_lbl = QLabel(label)
        self._title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_lbl.setStyleSheet(
            "color: #4cd3e3; font-size: 11px; font-weight: bold; "
            "background: transparent; border: none; font-family: 'Segoe UI', sans-serif;"
        )

        self._hint_lbl = QLabel("Drop file here or click Browse")
        self._hint_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint_lbl.setStyleSheet(
            "color: #64748b; font-size: 10px; background: transparent; border: none; font-family: 'Segoe UI', sans-serif;"
        )

        self._file_lbl = QLabel("")
        self._file_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._file_lbl.setWordWrap(True)
        self._file_lbl.setStyleSheet(
            "color: #00ff88; font-size: 10px; background: transparent; "
            "border: none; font-family: 'Consolas', monospace;"
        )

        layout.addWidget(self._icon_lbl)
        layout.addWidget(self._title_lbl)
        layout.addWidget(self._hint_lbl)
        layout.addWidget(self._file_lbl)

    # ── Drag events ────────────────────────────────────────────────────
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(self.HOVER_STYLE)

    def dragLeaveEvent(self, event):
        self.setStyleSheet(
            self.IDLE_STYLE if not self._file_path else self.LOADED_STYLE
        )

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            self._set_file(urls[0].toLocalFile())

    # ── Public API ─────────────────────────────────────────────────────
    def set_file(self, path: str):
        self._set_file(path)

    def get_file(self) -> str:
        return self._file_path

    def clear(self):
        self._file_path = ""
        self._file_lbl.setText("")
        self._icon_lbl.setText("📂")
        self._hint_lbl.setText("Drop file here or click Browse")
        self.setStyleSheet(self.IDLE_STYLE)

    # ── Private ────────────────────────────────────────────────────────
    def _set_file(self, path: str):
        if not os.path.isfile(path):
            return
        self._file_path = path
        name = os.path.basename(path)
        size_b = os.path.getsize(path)
        size_str = (
            f"{size_b/1024:.1f} KB"
            if size_b < 1024 * 1024
            else f"{size_b/1024/1024:.2f} MB"
        )
        self._file_lbl.setText(f"✅ {name}\n({size_str})")
        self._icon_lbl.setText("🔒")
        self._hint_lbl.setText("File loaded")
        self.setStyleSheet(self.LOADED_STYLE)
        self.file_dropped.emit(path)


# -----------------------------------------------------------------
#  Main Merge Dialog
# -----------------------------------------------------------------
class MergeDialog(QDialog):
    """Dialog for merging two firmware/binary files into one."""

    _STYLE = """
        QDialog {
            background-color: #171a1d;
            color: #e2e8f0;
        }
        QLabel#TitleLabel {
            color: #4cd3e3;
            font-size: 18px;
            font-weight: 800;
            font-family: 'Segoe UI', sans-serif;
            letter-spacing: 2px;
        }
        QLabel#SubLabel {
            color: #94a3b8;
            font-size: 11px;
            font-family: 'Segoe UI', sans-serif;
        }
        QLabel {
            color: #94a3b8;
            font-size: 11px;
            font-family: 'Segoe UI', sans-serif;
        }
        QPushButton {
            background-color: #252a2e;
            color: #e2e8f0;
            border: 1px solid #3c444d;
            border-radius: 6px;
            padding: 7px 16px;
            font-family: 'Segoe UI', sans-serif;
            font-size: 11px;
            font-weight: 600;
        }
        QPushButton:hover {
            background-color: #2e353b;
            border-color: #4cd3e3;
            color: #ffffff;
        }
        QPushButton#MergeBtn {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8fe3ea, stop:0.5 #3598a6, stop:1 #247d8a);
            color: #0b151a;
            border: none;
            font-size: 13px;
            padding: 10px 32px;
            border-radius: 8px;
            font-family: 'Segoe UI', sans-serif;
            font-weight: 900;
            letter-spacing: 1px;
        }
        QPushButton#MergeBtn:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #bbf2f6, stop:0.5 #45b1bf, stop:1 #2ca0b0);
            color: #000000;
        }
        QPushButton#MergeBtn:disabled {
            background: #1b2024;
            color: #475569;
            border: 1px solid #272e36;
        }
        QPushButton#ClearBtn {
            background-color: transparent;
            color: #ef4444;
            border: 1px solid #451a1a;
            font-size: 11px;
            padding: 4px 10px;
            border-radius: 4px;
        }
        QPushButton#ClearBtn:hover {
            background-color: #2a1515;
            border-color: #ef4444;
        }
        QComboBox {
            background-color: #252a2e;
            color: #f1f5f9;
            border: 1px solid #3c444d;
            border-radius: 6px;
            padding: 6px 12px;
            font-family: 'Segoe UI', sans-serif;
            font-size: 11px;
        }
        QComboBox::drop-down { border: none; }
        QComboBox QAbstractItemView {
            background-color: #252a2e;
            color: #f1f5f9;
            selection-background-color: #3598a6;
            selection-color: #ffffff;
        }
        QProgressBar {
            background-color: #14171a;
            border: 1px solid #283038;
            border-radius: 6px;
            min-height: 14px;
            max-height: 14px;
            text-align: center;
            color: transparent;
        }
        QProgressBar::chunk {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2ac4db, stop:1 #0ef6fd);
            border-radius: 5px;
        }
        QFrame#Divider {
            background-color: #283038;
            max-height: 1px;
        }
        QLabel#StatusLabel {
            color: #64748b;
            font-size: 10px;
            font-family: 'Consolas', monospace;
        }
        QLabel#InfoBox {
            color: #38bdf8;
            font-size: 11px;
            font-family: 'Consolas', monospace;
            background-color: #101316;
            border: 1px solid #22272e;
            border-radius: 6px;
            padding: 8px 12px;
        }
    """

    # ── Default download folder helper ────────────────────────────────
    @staticmethod
    def _downloads_dir() -> str:
        """Return the user's Downloads folder path."""
        home = os.path.expanduser("~")
        dl = os.path.join(home, "Downloads")
        return dl if os.path.isdir(dl) else home

    # ── Default output filename helper ───────────────────────────────
    @staticmethod
    def _default_name(f1: str, f2: str) -> str:
        """Generate a sensible default output filename from the two input names."""
        n1 = os.path.splitext(os.path.basename(f1))[0] if f1 else "FILE1"
        n2 = os.path.splitext(os.path.basename(f2))[0] if f2 else "FILE2"
        # Keep it short — just use 'merged_BIOS_output.bin' as default
        return "merged_BIOS_output.bin"

    # ── Constructor ───────────────────────────────────────────────────
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚡ MERGE — BIOS Tool")
        self.setStyleSheet(self._STYLE)
        self.setMinimumSize(700, 530)
        self.setWindowFlags(
            self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint
        )

        # Merged data is kept here until saved
        self._merged_bytes: bytes | None = None

        self._bridge = _WorkerBridge()
        self._bridge.ready.connect(self._on_merge_ready)
        self._bridge.failed.connect(self._on_merge_failed)
        self._bridge.progress.connect(self._on_progress)

        self._build_ui()
        self._update_state()

    # ── UI Construction ────────────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 22)
        root.setSpacing(14)

        # Title
        title = QLabel("⚡ FIRMWARE MERGE TOOL")
        title.setObjectName("TitleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)

        sub = QLabel(
            "Select or drag & drop two firmware/binary files to merge them into one"
        )
        sub.setObjectName("SubLabel")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(sub)

        # Divider
        root.addWidget(self._divider())

        # ── Drop zones ────────────────────────────────────────────────
        zones_row = QHBoxLayout()
        zones_row.setSpacing(14)

        # File 1
        f1_col = QVBoxLayout()
        lbl1 = QLabel("FILE 1  (Base)")
        lbl1.setStyleSheet(
            "color:#00f3ff; font-weight:bold; font-size:10px; font-family:'Consolas',monospace;"
        )
        lbl1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._zone1 = _DropZone("FILE 1 — Base Firmware")
        self._zone1.file_dropped.connect(self._update_state)
        browse1 = QPushButton("Browse...")
        browse1.clicked.connect(lambda: self._browse(self._zone1))
        clear1 = QPushButton("✕ Clear")
        clear1.setObjectName("ClearBtn")
        clear1.clicked.connect(lambda: self._clear_zone(self._zone1))
        f1_col.addWidget(lbl1)
        f1_col.addWidget(self._zone1)
        br1 = QHBoxLayout()
        br1.addWidget(browse1)
        br1.addWidget(clear1)
        f1_col.addLayout(br1)

        # Plus sign
        plus = QLabel("+")
        plus.setAlignment(Qt.AlignmentFlag.AlignCenter)
        plus.setStyleSheet("color:#00f3ff; font-size:36px; font-weight:bold; padding:0 4px;")
        plus.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        # File 2
        f2_col = QVBoxLayout()
        lbl2 = QLabel("FILE 2  (Patch / Donor)")
        lbl2.setStyleSheet(
            "color:#00f3ff; font-weight:bold; font-size:10px; font-family:'Consolas',monospace;"
        )
        lbl2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._zone2 = _DropZone("FILE 2 — Patch / Donor Firmware")
        self._zone2.file_dropped.connect(self._update_state)
        browse2 = QPushButton("Browse...")
        browse2.clicked.connect(lambda: self._browse(self._zone2))
        clear2 = QPushButton("✕ Clear")
        clear2.setObjectName("ClearBtn")
        clear2.clicked.connect(lambda: self._clear_zone(self._zone2))
        f2_col.addWidget(lbl2)
        f2_col.addWidget(self._zone2)
        br2 = QHBoxLayout()
        br2.addWidget(browse2)
        br2.addWidget(clear2)
        f2_col.addLayout(br2)

        zones_row.addLayout(f1_col)
        zones_row.addWidget(plus)
        zones_row.addLayout(f2_col)
        root.addLayout(zones_row)

        root.addWidget(self._divider())

        # ── Merge mode ────────────────────────────────────────────────
        mode_row = QHBoxLayout()
        mode_lbl = QLabel("Merge Mode:")
        mode_lbl.setStyleSheet("color:#8899aa; font-size:11px;")
        self._mode_combo = QComboBox()
        self._mode_combo.addItems([
            "Append  (File1 + File2)",
            "Prepend (File2 + File1)",
        ])
        mode_row.addWidget(mode_lbl)
        mode_row.addWidget(self._mode_combo)
        mode_row.addStretch()
        root.addLayout(mode_row)

        # ── Save info box ─────────────────────────────────────────────
        self._info_lbl = QLabel(
            f"💾  After merging, a Save dialog will open automatically.\n"
            f"    Default location: {self._downloads_dir()}\n"
            f"    Default filename:  merged_BIOS_output.bin"
        )
        self._info_lbl.setObjectName("InfoBox")
        root.addWidget(self._info_lbl)

        # ── Progress bar ──────────────────────────────────────────────
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setVisible(False)
        root.addWidget(self._progress)

        # ── Status label ──────────────────────────────────────────────
        self._status_lbl = QLabel("Select two files to begin.")
        self._status_lbl.setObjectName("StatusLabel")
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._status_lbl)

        # ── Action buttons ────────────────────────────────────────────
        btn_row = QHBoxLayout()
        self._merge_btn = QPushButton("⚡  MERGE")
        self._merge_btn.setObjectName("MergeBtn")
        self._merge_btn.clicked.connect(self._start_merge)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        btn_row.addStretch()
        btn_row.addWidget(self._merge_btn)
        btn_row.addSpacing(12)
        btn_row.addWidget(close_btn)
        btn_row.addStretch()
        root.addLayout(btn_row)

    # ── Helpers ────────────────────────────────────────────────────────
    def _divider(self) -> QFrame:
        f = QFrame()
        f.setObjectName("Divider")
        return f

    # ── Actions ────────────────────────────────────────────────────────
    def _browse(self, zone: _DropZone):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Firmware File", "",
            "Firmware Files (*.bin *.rom *.cap *.fd *.img *.exe *.zip);;All Files (*)"
        )
        if path:
            zone.set_file(path)
            self._update_state()

    def _clear_zone(self, zone: _DropZone):
        zone.clear()
        self._update_state()

    def _update_state(self, *_):
        f1 = self._zone1.get_file()
        f2 = self._zone2.get_file()
        ready = bool(f1 and f2)
        self._merge_btn.setEnabled(ready)

        if ready:
            s1 = os.path.getsize(f1)
            s2 = os.path.getsize(f2)
            total = s1 + s2

            def _fmt(b):
                return (
                    f"{b/1024:.1f} KB"
                    if b < 1024 * 1024
                    else f"{b/1024/1024:.2f} MB"
                )

            self._status_lbl.setStyleSheet(
                "color: #5a7080; font-size:10px; font-family:'Consolas',monospace;"
            )
            self._status_lbl.setText(
                f"Ready — estimated output size: ~{_fmt(total)}  "
                f"({_fmt(s1)} + {_fmt(s2)})"
            )

            # Update default filename in info box
            default_name = self._default_name(f1, f2)
            self._info_lbl.setText(
                f"💾  After merging, a Save dialog will open automatically.\n"
                f"    Default location: {self._downloads_dir()}\n"
                f"    Default filename:  {default_name}"
            )
        else:
            self._status_lbl.setText("Select two files to begin.")

    def _start_merge(self):
        """Read both files and merge them in a background thread (no disk write yet)."""
        f1 = self._zone1.get_file()
        f2 = self._zone2.get_file()
        mode = self._mode_combo.currentIndex()  # 0=append, 1=prepend

        self._merge_btn.setEnabled(False)
        self._progress.setVisible(True)
        self._progress.setValue(0)
        self._status_lbl.setStyleSheet(
            "color: #8899aa; font-size:10px; font-family:'Consolas',monospace;"
        )
        self._status_lbl.setText("⏳  Merging in memory…")

        def _worker():
            try:
                self._bridge.progress.emit(15)
                with open(f1, "rb") as fh:
                    data1 = fh.read()
                self._bridge.progress.emit(45)
                with open(f2, "rb") as fh:
                    data2 = fh.read()
                self._bridge.progress.emit(75)
                merged = (data1 + data2) if mode == 0 else (data2 + data1)
                self._bridge.progress.emit(100)
                self._bridge.ready.emit(_BytesHolder(merged))
            except Exception as exc:
                self._bridge.failed.emit(str(exc))

        threading.Thread(target=_worker, daemon=True).start()

    # ── Signal callbacks (main thread) ────────────────────────────────
    def _on_progress(self, val: int):
        self._progress.setValue(val)

    def _on_merge_ready(self, holder: _BytesHolder):
        """Merge done in memory — now open Save As dialog automatically."""
        self._merged_bytes = holder.data
        self._progress.setVisible(False)
        self._merge_btn.setEnabled(True)

        f1 = self._zone1.get_file()
        f2 = self._zone2.get_file()
        default_name = self._default_name(f1, f2)
        default_path = os.path.join(self._downloads_dir(), default_name)

        # ── Auto-open Save As dialog ──────────────────────────────────
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "💾  Save Merged Firmware As",
            default_path,
            "Binary Files (*.bin);;ROM Files (*.rom);;All Files (*.*)",
        )

        if not save_path:
            # User cancelled the save dialog
            self._status_lbl.setStyleSheet(
                "color: #f59e0b; font-size:10px; font-family:'Consolas',monospace;"
            )
            self._status_lbl.setText(
                "⚠️  Save cancelled.  Click MERGE again to retry."
            )
            self._merged_bytes = None
            return

        # ── Write to disk ─────────────────────────────────────────────
        try:
            with open(save_path, "wb") as fout:
                fout.write(self._merged_bytes)
        except Exception as exc:
            self._on_merge_failed(str(exc))
            return

        size = len(self._merged_bytes)
        size_str = (
            f"{size/1024:.1f} KB"
            if size < 1024 * 1024
            else f"{size/1024/1024:.2f} MB"
        )
        self._merged_bytes = None

        self._status_lbl.setStyleSheet(
            "color:#00ff88; font-size:10px; font-family:'Consolas',monospace;"
        )
        self._status_lbl.setText(
            f"✅  Saved: {os.path.basename(save_path)}  ({size_str})"
        )

        QMessageBox.information(
            self,
            "✅ Merge Successful",
            f"Files merged and saved successfully!\n\n"
            f"📄 Output : {save_path}\n"
            f"📦 Size    : {size_str}",
        )

    def _on_merge_failed(self, error: str):
        self._progress.setVisible(False)
        self._merge_btn.setEnabled(True)
        self._merged_bytes = None
        self._status_lbl.setStyleSheet(
            "color:#ff4444; font-size:10px; font-family:'Consolas',monospace;"
        )
        self._status_lbl.setText(f"❌  Error: {error}")
        QMessageBox.critical(
            self, "❌ Merge Failed", f"An error occurred:\n\n{error}"
        )
