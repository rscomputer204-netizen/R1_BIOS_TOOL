import os
import sys
import re
import json
import time
import zipfile
import shutil
import subprocess
import requests
from pathlib import Path

try:
    from PySide6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QProgressBar, QTextEdit, QFrame, QMessageBox, QApplication
    )
    from PySide6.QtCore import Qt, QThread, Signal as pyqtSignal, QTimer
    from PySide6.QtGui import QFont
except ImportError:
    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QProgressBar, QTextEdit, QFrame, QMessageBox, QApplication
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
    from PyQt6.QtGui import QFont

# --- CONSTANTS ---
DEFAULT_UPDATE_URL = "https://raw.githubusercontent.com/rscomputer204-netizen/R1_BIOS_TOOL/main/version.json"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_local_version():
    """Reads current software version from version.txt or version.json."""
    ver_txt = os.path.join(BASE_DIR, "version.txt")
    if os.path.exists(ver_txt):
        try:
            with open(ver_txt, "r", encoding="utf-8") as f:
                v = f.read().strip()
                if v:
                    if not v.startswith("R1"):
                        v = f"R1.{v.lstrip('v.')}"
                    return v
        except Exception:
            pass
    ver_json = os.path.join(BASE_DIR, "version.json")
    if os.path.exists(ver_json):
        try:
            with open(ver_json, "r", encoding="utf-8") as f:
                data = json.load(f)
                v = str(data.get("version", "R1.1.0.0")).strip()
                if not v.startswith("R1"):
                    v = f"R1.{v.lstrip('v.')}"
                return v
        except Exception:
            pass
    return "R1.1.0.0"

def is_newer_version(remote_ver, current_ver):
    """Compares version numbers robustly (e.g., R1.0.0.7 vs R1.0.0.6)."""
    try:
        def parse(v):
            cleaned = re.sub(r'[^0-9.]', '', str(v))
            return [int(x) for x in cleaned.split('.') if x.isdigit()]
        r = parse(remote_ver)
        c = parse(current_ver)
        if not c:
            return True
        return r > c
    except Exception:
        return str(remote_ver) > str(current_ver)


class UpdateCheckWorker(QThread):
    """Checks GitHub for version.json in background thread."""
    check_finished = pyqtSignal(bool, dict, str)

    def __init__(self, update_url=None):
        super().__init__()
        self.update_url = update_url or DEFAULT_UPDATE_URL

    def run(self):
        try:
            nocache_url = f"{self.update_url}?t={int(time.time())}"
            headers = {
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
            res = requests.get(nocache_url, headers=headers, timeout=12)
            if res.status_code == 200:
                data = res.json()
                self.check_finished.emit(True, data, "")
            else:
                self.check_finished.emit(False, {}, f"Server returned HTTP {res.status_code}")
        except Exception as e:
            self.check_finished.emit(False, {}, str(e))


class UpdateDownloadWorker(QThread):
    """Downloads update.zip and extracts payload in background thread."""
    progress = pyqtSignal(int, str)
    completed = pyqtSignal(bool, str)

    def __init__(self, download_url):
        super().__init__()
        self.download_url = download_url

    def run(self):
        try:
            cache_dir = os.path.join(BASE_DIR, "update_cache")
            if os.path.exists(cache_dir):
                shutil.rmtree(cache_dir, ignore_errors=True)
            os.makedirs(cache_dir, exist_ok=True)

            local_zip = os.path.join(cache_dir, "update.zip")

            self.progress.emit(5, "Connecting to GitHub server...")

            # GitHub blob URL fix
            url = self.download_url
            if "github.com" in url and "/blob/" in url:
                url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")

            res = requests.get(url, stream=True, timeout=60)
            res.raise_for_status()

            total_size = int(res.headers.get('content-length', 0))
            downloaded = 0

            with open(local_zip, "wb") as f:
                for chunk in res.iter_content(chunk_size=64 * 1024):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = int((downloaded / total_size) * 85)
                            self.progress.emit(5 + percent, f"Downloading... {int((downloaded / total_size) * 100)}%")

            self.progress.emit(90, "Validating update package...")

            if not zipfile.is_zipfile(local_zip):
                raise ValueError("Downloaded file is not a valid ZIP archive.")

            with zipfile.ZipFile(local_zip, "r") as zf:
                namelist = zf.namelist()
                if "manifest.json" not in namelist:
                    raise ValueError("Security error: Missing manifest.json in package.")
                if "version.txt" not in namelist:
                    raise ValueError("Security error: Missing version.txt in package.")

                # Traversal validation
                for item in namelist:
                    if ".." in item or item.startswith("/") or item.startswith("\\"):
                        raise ValueError(f"Security error: Invalid path detected ({item})")

                self.progress.emit(95, "Unpacking update components...")
                zf.extractall(cache_dir)

            self.progress.emit(100, "Update package ready!")
            self.completed.emit(True, "Update ready")
        except Exception as e:
            self.completed.emit(False, str(e))


class UpdateDialog(QDialog):
    """Sleek Cyberpunk/Stealth Auto-Update Dialog."""
    def __init__(self, parent=None, update_url=None):
        super().__init__(parent)
        self.update_url = update_url or DEFAULT_UPDATE_URL
        self.current_version = get_local_version()
        self.remote_version = None
        self.download_url = None
        self.changelog = ""

        self.setWindowTitle("R1 BIOS TOOL - SYSTEM AUTO UPDATE")
        self.setFixedSize(480, 360)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        self.init_ui()
        self.start_check()

    def init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #010409;
                border: 1px solid #00f2ff;
                border-radius: 8px;
            }
            QLabel {
                color: #e6edf3;
                font-family: 'Segoe UI', sans-serif;
            }
            QProgressBar {
                border: 1px solid #30363d;
                border-radius: 4px;
                text-align: center;
                color: #ffffff;
                background-color: #0d1117;
                font-size: 11px;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0088cc, stop:1 #00f2ff);
                border-radius: 3px;
            }
            QTextEdit {
                background-color: #0d1117;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 6px;
                font-family: 'Segoe UI', Consolas, monospace;
                font-size: 11px;
                padding: 6px;
            }
            QPushButton {
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
                font-weight: bold;
                border-radius: 4px;
                padding: 7px 16px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        # Header Title
        title_lbl = QLabel("SYSTEM AUTO UPDATE")
        title_lbl.setStyleSheet("color: #00f2ff; font-size: 15px; font-weight: 800; letter-spacing: 1.5px;")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_lbl)

        # Current Version Subtitle
        self.ver_lbl = QLabel(f"Current Installed Version: {self.current_version}")
        self.ver_lbl.setStyleSheet("color: #8b949e; font-size: 11px;")
        self.ver_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.ver_lbl)

        # Separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #21262d;")
        layout.addWidget(sep)

        # Status text
        self.status_lbl = QLabel("Connecting to GitHub server...")
        self.status_lbl.setStyleSheet("color: #58a6ff; font-size: 12px; font-weight: bold;")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_lbl)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(18)
        self.progress_bar.setRange(0, 0) # Indeterminate initially
        layout.addWidget(self.progress_bar)

        # Changelog area (initially hidden)
        self.changelog_lbl = QLabel("What's New in This Version:")
        self.changelog_lbl.setStyleSheet("color: #8b949e; font-size: 10px; font-weight: bold; text-transform: uppercase;")
        self.changelog_lbl.hide()
        layout.addWidget(self.changelog_lbl)

        self.changelog_box = QTextEdit()
        self.changelog_box.setReadOnly(True)
        self.changelog_box.setFixedHeight(100)
        self.changelog_box.hide()
        layout.addWidget(self.changelog_box)

        # Action Button Row
        self.btn_layout = QHBoxLayout()
        self.btn_layout.setSpacing(10)

        self.btn_action = QPushButton("DOWNLOAD & UPDATE")
        self.btn_action.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_action.setStyleSheet("""
            QPushButton {
                background-color: #00f2ff;
                color: #010409;
                border: none;
            }
            QPushButton:hover {
                background-color: #38f8ff;
            }
        """)
        self.btn_action.hide()
        self.btn_action.clicked.connect(self.start_download)
        self.btn_layout.addWidget(self.btn_action)

        self.btn_close = QPushButton("CANCEL")
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setStyleSheet("""
            QPushButton {
                background-color: #161b22;
                color: #c9d1d9;
                border: 1px solid #30363d;
            }
            QPushButton:hover {
                background-color: #21262d;
                color: #ffffff;
            }
        """)
        self.btn_close.clicked.connect(self.reject)
        self.btn_layout.addWidget(self.btn_close)

        layout.addLayout(self.btn_layout)

    def start_check(self):
        self.status_lbl.setText("Checking for updates on GitHub...")
        self.status_lbl.setStyleSheet("color: #58a6ff; font-size: 12px; font-weight: bold;")
        self.progress_bar.setRange(0, 0)
        self.progress_bar.show()

        self.check_worker = UpdateCheckWorker(self.update_url)
        self.check_worker.check_finished.connect(self.on_check_finished)
        self.check_worker.start()

    def on_check_finished(self, success, data, error_msg):
        self.progress_bar.hide()
        if not success:
            self.status_lbl.setText(f"CHECK FAILED: {error_msg}")
            self.status_lbl.setStyleSheet("color: #f85149; font-size: 11px; font-weight: bold;")
            self.btn_close.setText("CLOSE")
            return

        remote_ver = str(data.get("version", "0.0.0")).strip()
        self.remote_version = remote_ver
        self.download_url = data.get("url", "")
        self.changelog = data.get("changelog", "Bug fixes and enhancements.")

        if is_newer_version(remote_ver, self.current_version):
            self.status_lbl.setText(f"★ NEW VERSION AVAILABLE: {remote_ver}")
            self.status_lbl.setStyleSheet("color: #00f2ff; font-size: 13px; font-weight: 800;")

            self.changelog_lbl.show()
            self.changelog_box.setText(self.changelog)
            self.changelog_box.show()

            self.btn_action.show()
            self.btn_close.setText("LATER")
        else:
            self.status_lbl.setText(f"✓ YOU ARE ON THE LATEST VERSION ({self.current_version})")
            self.status_lbl.setStyleSheet("color: #00FFCC; font-size: 12px; font-weight: bold;")
            self.btn_close.setText("CLOSE")

    def start_download(self):
        if not self.download_url:
            QMessageBox.warning(self, "Error", "Download URL not provided by update server.")
            return

        self.btn_action.setEnabled(False)
        self.btn_close.setEnabled(False)
        self.status_lbl.setText("Starting download...")
        self.status_lbl.setStyleSheet("color: #58a6ff; font-size: 12px; font-weight: bold;")

        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.show()

        self.download_worker = UpdateDownloadWorker(self.download_url)
        self.download_worker.progress.connect(self.on_download_progress)
        self.download_worker.completed.connect(self.on_download_completed)
        self.download_worker.start()

    def on_download_progress(self, percent, msg):
        self.progress_bar.setValue(percent)
        self.status_lbl.setText(msg)

    def on_download_completed(self, success, msg):
        if not success:
            self.status_lbl.setText(f"DOWNLOAD FAILED: {msg}")
            self.status_lbl.setStyleSheet("color: #f85149; font-size: 11px; font-weight: bold;")
            self.btn_action.setEnabled(True)
            self.btn_close.setEnabled(True)
            self.btn_close.setText("CLOSE")
            return

        self.status_lbl.setText("Update verified! Restarting application in 1s...")
        self.status_lbl.setStyleSheet("color: #00FFCC; font-size: 12px; font-weight: bold;")
        self.progress_bar.setValue(100)

        # Trigger restart after 1.2s
        QTimer.singleShot(1200, self.launch_updater_and_exit)

    def launch_updater_and_exit(self):
        """Spawns updater and cleanly terminates current application."""
        pid = os.getpid()
        updater_exe = os.path.join(BASE_DIR, "updater.exe")
        updater_py = os.path.join(BASE_DIR, "updater.py")

        try:
            if os.path.exists(updater_exe):
                subprocess.Popen([updater_exe, str(pid)], cwd=BASE_DIR)
            elif os.path.exists(updater_py):
                if sys.platform == "win32":
                    subprocess.Popen(
                        [sys.executable, updater_py, str(pid)],
                        cwd=BASE_DIR,
                        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
                    )
                else:
                    subprocess.Popen([sys.executable, updater_py, str(pid)], cwd=BASE_DIR)
            else:
                QMessageBox.critical(self, "Error", f"Updater component missing at:\n{updater_py}")
                return

            # Terminate this application so updater can replace files
            QApplication.quit()
            sys.exit(0)
        except Exception as e:
            QMessageBox.critical(self, "Launch Error", f"Failed to start updater: {e}")
