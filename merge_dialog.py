"""
merge_dialog.py - Compact BIOS Firmware Merge Tool
Allows selecting two firmware/binary files by clicking or drag-and-drop,
and merging them into a single output file with automatic Save As prompt.
Clean, modern, and compact interface with zero emojis.
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
    ready    = Signal(object)  # merged bytes object wrapper
    failed   = Signal(str)     # error message
    progress = Signal(int)     # 0-100


class _BytesHolder:
    """Simple wrapper to pass bytes through a Signal(object)."""
    def __init__(self, data: bytes):
        self.data = data


# -----------------------------------------------------------------
#  Interactive Clickable Drop Zone Widget
# -----------------------------------------------------------------
class _DropZone(QFrame):
    """Clickable and drag-and-drop file selection box."""

    file_dropped = Signal(str)
    clicked = Signal()

    IDLE_STYLE = """
        QFrame {
            background-color: #0c1017;
            border: 1.5px dashed #1e293b;
            border-radius: 10px;
            min-height: 105px;
        }
        QFrame:hover {
            background-color: #101722;
            border: 1.5px dashed #38bdf8;
        }
    """
    HOVER_STYLE = """
        QFrame {
            background-color: #0f1c2e;
            border: 2px dashed #00f3ff;
            border-radius: 10px;
            min-height: 105px;
        }
    """
    LOADED_STYLE = """
        QFrame {
            background-color: #0b1724;
            border: 1.5px solid #0284c7;
            border-radius: 10px;
            min-height: 105px;
        }
        QFrame:hover {
            background-color: #0d1e30;
            border: 1.5px solid #38bdf8;
        }
    """

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(self.IDLE_STYLE)

        self._label_text = label
        self._file_path = ""

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(4)

        self._title_lbl = QLabel(label)
        self._title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_lbl.setStyleSheet(
            "color: #38bdf8; font-size: 11px; font-weight: bold; "
            "background: transparent; border: none; font-family: 'Segoe UI', sans-serif;"
        )

        self._hint_lbl = QLabel("Drop file here or click to browse")
        self._hint_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint_lbl.setStyleSheet(
            "color: #64748b; font-size: 10px; background: transparent; border: none; font-family: 'Segoe UI', sans-serif;"
        )

        self._file_lbl = QLabel("")
        self._file_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._file_lbl.setWordWrap(True)
        self._file_lbl.setStyleSheet(
            "color: #00f3ff; font-size: 11px; font-weight: bold; background: transparent; "
            "border: none; font-family: 'Consolas', monospace;"
        )

        layout.addWidget(self._title_lbl)
        layout.addWidget(self._hint_lbl)
        layout.addWidget(self._file_lbl)

    # ── Click & Drag events ───────────────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

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
        self._title_lbl.setText(self._label_text)
        self._title_lbl.setStyleSheet(
            "color: #38bdf8; font-size: 11px; font-weight: bold; "
            "background: transparent; border: none; font-family: 'Segoe UI', sans-serif;"
        )
        self._hint_lbl.setText("Drop file here or click to browse")
        self._hint_lbl.setStyleSheet(
            "color: #64748b; font-size: 10px; background: transparent; border: none; font-family: 'Segoe UI', sans-serif;"
        )
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
        self._title_lbl.setText(f"{self._label_text} [LOADED]")
        self._title_lbl.setStyleSheet(
            "color: #22c55e; font-size: 10px; font-weight: bold; "
            "background: transparent; border: none; font-family: 'Segoe UI', sans-serif;"
        )
        self._file_lbl.setText(f"{name}\n({size_str})")
        self._hint_lbl.setText("Click or drop to replace")
        self._hint_lbl.setStyleSheet(
            "color: #94a3b8; font-size: 9px; background: transparent; border: none; font-family: 'Segoe UI', sans-serif;"
        )
        self.setStyleSheet(self.LOADED_STYLE)
        self.file_dropped.emit(path)


# -----------------------------------------------------------------
#  Main Merge Dialog (Compact & Minimalist)
# -----------------------------------------------------------------
class MergeDialog(QDialog):
    """Compact dialog for merging two firmware/binary files into one."""

    _STYLE = """
        QDialog {
            background-color: #0b0f15;
            color: #e2e8f0;
        }
        QLabel#TitleLabel {
            color: #00f3ff;
            font-size: 15px;
            font-weight: 800;
            font-family: 'Segoe UI', sans-serif;
            letter-spacing: 1.5px;
        }
        QLabel#SubLabel {
            color: #64748b;
            font-size: 10px;
            font-family: 'Segoe UI', sans-serif;
        }
        QLabel {
            color: #94a3b8;
            font-size: 11px;
            font-family: 'Segoe UI', sans-serif;
        }
        QPushButton {
            background-color: #1e293b;
            color: #94a3b8;
            border: 1px solid #334155;
            border-radius: 6px;
            padding: 6px 18px;
            font-family: 'Segoe UI', sans-serif;
            font-size: 11px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #334155;
            color: #ffffff;
        }
        QComboBox {
            background-color: #161e2e;
            color: #f1f5f9;
            border: 1px solid #334155;
            border-radius: 6px;
            padding: 5px 10px;
            font-family: 'Segoe UI', sans-serif;
            font-size: 11px;
        }
        QComboBox::drop-down { border: none; }
        QComboBox QAbstractItemView {
            background-color: #161e2e;
            color: #f1f5f9;
            selection-background-color: #0284c7;
            selection-color: #ffffff;
        }
        QProgressBar {
            background-color: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 4px;
            min-height: 8px;
            max-height: 8px;
            text-align: center;
        }
        QProgressBar::chunk {
            background: #38bdf8;
            border-radius: 3px;
        }
        QFrame#Divider {
            background-color: #1e293b;
            max-height: 1px;
        }
    """

    # ── Default download folder helper ────────────────────────────────
    @staticmethod
    def _downloads_dir() -> str:
        home = os.path.expanduser("~")
        dl = os.path.join(home, "Downloads")
        return dl if os.path.isdir(dl) else home

    # ── Default output filename helper ───────────────────────────────
    @staticmethod
    def _default_name(f1: str, f2: str) -> str:
        return "merged_BIOS_output.bin"

    # ── Constructor ───────────────────────────────────────────────────
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("MERGE — BIOS Tool")
        self.setStyleSheet(self._STYLE)
        self.setFixedSize(540, 395)
        self.setWindowFlags(
            self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint
        )

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
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(10)

        # Header Title
        title = QLabel("FIRMWARE MERGE TOOL")
        title.setObjectName("TitleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)

        sub = QLabel("Drop or click to select two binary files to merge into one")
        sub.setObjectName("SubLabel")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(sub)

        # Divider
        divider = QFrame()
        divider.setObjectName("Divider")
        root.addWidget(divider)

        # ── Drop zones Row (Clickable & Drag-and-drop) ─────────────────
        zones_row = QHBoxLayout()
        zones_row.setSpacing(10)

        # Zone 1 (Base)
        self._zone1 = _DropZone("FILE 1 — Base")
        self._zone1.clicked.connect(lambda: self._browse(self._zone1))
        self._zone1.file_dropped.connect(self._update_state)

        # Plus Sign Separator
        plus = QLabel("+")
        plus.setAlignment(Qt.AlignmentFlag.AlignCenter)
        plus.setStyleSheet("color: #00f3ff; font-size: 26px; font-weight: bold;")
        plus.setFixedWidth(28)

        # Zone 2 (Patch / Donor)
        self._zone2 = _DropZone("FILE 2 — Patch / Donor")
        self._zone2.clicked.connect(lambda: self._browse(self._zone2))
        self._zone2.file_dropped.connect(self._update_state)

        zones_row.addWidget(self._zone1, stretch=1)
        zones_row.addWidget(plus)
        zones_row.addWidget(self._zone2, stretch=1)
        root.addLayout(zones_row)

        # ── Merge mode Row ────────────────────────────────────────────
        mode_row = QHBoxLayout()
        mode_row.setSpacing(8)
        mode_lbl = QLabel("Merge Mode:")
        mode_lbl.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: bold;")
        self._mode_combo = QComboBox()
        self._mode_combo.addItems([
            "Append  (File1 + File2)",
            "Prepend (File2 + File1)",
        ])
        mode_row.addWidget(mode_lbl)
        mode_row.addWidget(self._mode_combo)
        mode_row.addStretch()
        root.addLayout(mode_row)

        # ── Compact Info / Status Strip ───────────────────────────────
        self._info_lbl = QLabel("Select two binary files to begin.")
        self._info_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._info_lbl.setWordWrap(True)
        root.addWidget(self._info_lbl)

        # ── Progress bar ──────────────────────────────────────────────
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setVisible(False)
        root.addWidget(self._progress)

        # ── Action buttons ────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        close_btn = QPushButton("Cancel")
        close_btn.setFixedHeight(36)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.reject)

        self._merge_btn = QPushButton("MERGE")
        self._merge_btn.setFixedHeight(36)
        self._merge_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._merge_btn.setEnabled(False)
        self._apply_merge_btn_style(False)
        self._merge_btn.clicked.connect(self._start_merge)

        btn_row.addWidget(close_btn)
        btn_row.addStretch()
        btn_row.addWidget(self._merge_btn)
        root.addLayout(btn_row)

    # ── Style Helper for MERGE Button ─────────────────────────────────
    def _apply_merge_btn_style(self, enabled: bool):
        if enabled:
            self._merge_btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #38bdf8, stop:0.5 #0ea5e9, stop:1 #0284c7);
                    color: #041018;
                    border: 1px solid #7dd3fc;
                    border-radius: 6px;
                    font-size: 12px;
                    font-weight: 900;
                    letter-spacing: 1.5px;
                    padding: 0 28px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #7dd3fc, stop:0.5 #38bdf8, stop:1 #0ea5e9);
                    color: #000000;
                    border-color: #bae6fd;
                }
                QPushButton:pressed {
                    background: #0369a1;
                }
            """)
        else:
            self._merge_btn.setStyleSheet("""
                QPushButton {
                    background: #161e2e;
                    color: #475569;
                    border: 1px solid #1e293b;
                    border-radius: 6px;
                    font-size: 12px;
                    font-weight: 900;
                    letter-spacing: 1.5px;
                    padding: 0 28px;
                }
            """)

    # ── Actions ────────────────────────────────────────────────────────
    def _browse(self, zone: _DropZone):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Firmware File", "",
            "Firmware Files (*.bin *.rom *.cap *.fd *.img *.exe *.zip);;All Files (*)"
        )
        if path:
            zone.set_file(path)
            self._update_state()

    def _update_state(self, *_):
        f1 = self._zone1.get_file()
        f2 = self._zone2.get_file()
        ready = bool(f1 and f2)
        self._merge_btn.setEnabled(ready)
        self._apply_merge_btn_style(ready)

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

            default_name = self._default_name(f1, f2)
            self._info_lbl.setText(
                f"Ready to merge: ~{_fmt(total)} ({_fmt(s1)} + {_fmt(s2)})\n"
                f"Auto-save location: Downloads / {default_name}"
            )
            self._info_lbl.setStyleSheet("""
                QLabel {
                    color: #38bdf8;
                    font-size: 10px;
                    font-family: 'Consolas', monospace;
                    background-color: #081523;
                    border: 1px solid #0284c7;
                    border-radius: 6px;
                    padding: 6px 10px;
                }
            """)
        else:
            self._info_lbl.setText("Select two binary files to merge them into one.")
            self._info_lbl.setStyleSheet("""
                QLabel {
                    color: #64748b;
                    font-size: 10px;
                    font-family: 'Segoe UI', sans-serif;
                    background-color: #0a0e16;
                    border: 1px solid #1a2332;
                    border-radius: 6px;
                    padding: 6px 10px;
                }
            """)

    def _start_merge(self):
        """Read both files and merge them in a background thread."""
        f1 = self._zone1.get_file()
        f2 = self._zone2.get_file()
        mode = self._mode_combo.currentIndex()  # 0=append, 1=prepend

        self._merge_btn.setEnabled(False)
        self._progress.setVisible(True)
        self._progress.setValue(0)
        self._info_lbl.setText("Merging in memory...")

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
            "Save Merged Firmware As",
            default_path,
            "Binary Files (*.bin);;ROM Files (*.rom);;All Files (*.*)",
        )

        if not save_path:
            self._info_lbl.setText("Save cancelled. Click MERGE again to retry.")
            self._info_lbl.setStyleSheet("color: #f59e0b; font-size: 10px; font-family: 'Consolas', monospace; background-color: #081523; border: 1px solid #f59e0b; border-radius: 6px; padding: 6px 10px;")
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

        self._info_lbl.setText(f"Saved: {os.path.basename(save_path)}  ({size_str})")
        self._info_lbl.setStyleSheet("color: #00ff88; font-size: 10px; font-family: 'Consolas', monospace; background-color: #081523; border: 1px solid #00ff88; border-radius: 6px; padding: 6px 10px;")

        QMessageBox.information(
            self,
            "Merge Successful",
            f"Files merged and saved successfully!\n\n"
            f"Output : {save_path}\n"
            f"Size   : {size_str}",
        )

    def _on_merge_failed(self, error: str):
        self._progress.setVisible(False)
        self._merge_btn.setEnabled(True)
        self._merged_bytes = None
        self._info_lbl.setText(f"Error: {error}")
        self._info_lbl.setStyleSheet("color: #ff4444; font-size: 10px; font-family: 'Consolas', monospace; background-color: #081523; border: 1px solid #ff4444; border-radius: 6px; padding: 6px 10px;")
        QMessageBox.critical(
            self, "Merge Failed", f"An error occurred:\n\n{error}"
        )
