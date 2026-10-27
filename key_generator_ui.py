import sys
import os
import json
import base64
import uuid
import urllib.request
import urllib.error
from datetime import datetime, timezone
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QDateEdit, QTimeEdit, QMessageBox, QGroupBox,
    QDialog, QCheckBox, QFileDialog, QFrame, QScrollArea, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QSizePolicy,
    QRadioButton, QMenu
)
from PySide6.QtCore import QDate, QTime, Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QColor, QShortcut, QKeySequence
from license_manager import encrypt_payload, decrypt_payload

# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------
def clean_repo_name(raw_repo):
    """Clean full URL or raw string to strictly 'owner/repo' format."""
    raw = (raw_repo or "").strip()
    if "github.com/" in raw:
        after_domain = raw.split("github.com/")[-1]
        parts = [p for p in after_domain.split("/") if p and p not in ("edit", "blob", "tree", "raw")]
        if len(parts) >= 2:
            return f"{parts[0]}/{parts[1]}"
    # Remove leading/trailing slashes
    cleaned = raw.strip("/")
    parts = [p for p in cleaned.split("/") if p]
    if len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"
    return cleaned

def parse_expiry_status(expiry_str):
    """Determine if an expiry string is Active or Expired."""
    if not expiry_str or expiry_str == "Unknown":
        return "UNKNOWN"
    formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]
    for fmt in formats:
        try:
            exp_dt = datetime.strptime(expiry_str.strip(), fmt)
            # Compare with local time
            if datetime.now() > exp_dt:
                return "EXPIRED"
            return "ACTIVE"
        except Exception:
            continue
    return "ACTIVE"


# ---------------------------------------------------------------------------
# Configuration Manager
# ---------------------------------------------------------------------------
CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")
CONFIG_FILE = os.path.join(CONFIG_DIR, "key_generator_config.json")
APPDATA_DIR = os.path.join(os.environ.get("APPDATA", ""), "R1_BIOS_TOOL")
APPDATA_CONFIG_FILE = os.path.join(APPDATA_DIR, "key_generator_config.json")

DEFAULT_CONFIG = {
    "github_token": "",
    "repo": "rscomputer204-netizen/license_keys.txt",
    "branch": "main",
    "file_path": "license_keys.txt",
    "local_file_path": os.path.join(os.path.dirname(os.path.abspath(__file__)), "license_keys.txt"),
    "auto_push": False
}

def load_config():
    # Try project config first, then APPDATA
    for path in [CONFIG_FILE, APPDATA_CONFIG_FILE]:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    merged = DEFAULT_CONFIG.copy()
                    merged.update(cfg)
                    merged["repo"] = clean_repo_name(merged.get("repo", ""))
                    return merged
            except Exception:
                pass
    return DEFAULT_CONFIG.copy()

def save_config(cfg):
    cfg["repo"] = clean_repo_name(cfg.get("repo", ""))
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)
    except Exception as e:
        print(f"Failed to save to project config: {e}")

    try:
        os.makedirs(APPDATA_DIR, exist_ok=True)
        with open(APPDATA_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)
    except Exception as e:
        print(f"Failed to save to APPDATA config: {e}")


# ---------------------------------------------------------------------------
# Background GitHub API Worker
# ---------------------------------------------------------------------------
class GitHubSyncWorker(QThread):
    finished = Signal(bool, str, dict)

    def __init__(self, action, config, payload=None):
        super().__init__()
        self.action = action  # "test", "push", "fetch_list", "remove_key"
        self.config = config
        self.payload = payload or {}

    def run(self):
        token = self.config.get("github_token", "").strip()
        repo = clean_repo_name(self.config.get("repo", "").strip())
        branch = self.config.get("branch", "main").strip()
        file_path = self.config.get("file_path", "license_keys.txt").strip()

        if not token:
            self.finished.emit(False, "GitHub Personal Access Token is missing. Click 'GitHub Settings' to configure.", {})
            return

        if not repo:
            self.finished.emit(False, "Repository name is missing (e.g. owner/repo).", {})
            return

        api_url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "R1-BIOS-TOOL-KeyGen",
            "X-GitHub-Api-Version": "2022-11-28"
        }

        # -------------------------------------------------------------------
        # 1. TEST CONNECTION
        # -------------------------------------------------------------------
        if self.action == "test":
            try:
                test_url = f"https://api.github.com/repos/{repo}"
                req = urllib.request.Request(test_url, headers=headers, method="GET")
                with urllib.request.urlopen(req, timeout=12) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    repo_full_name = data.get("full_name", repo)
                    permissions = data.get("permissions", {})
                    can_push = permissions.get("push", True)
                    
                    if can_push:
                        msg = f"Connected! Repository: {repo_full_name} (Write Permission OK)"
                    else:
                        msg = f"Connected to {repo_full_name}, but token lacks write permission."
                    self.finished.emit(True, msg, data)
            except urllib.error.HTTPError as e:
                err_msg = self._format_http_error(e)
                self.finished.emit(False, f"Disconnected: {err_msg}", {})
            except Exception as e:
                self.finished.emit(False, f"Connection Error: {str(e)}", {})
            return

        # -------------------------------------------------------------------
        # 2. PUSH LICENSE KEY
        # -------------------------------------------------------------------
        if self.action == "push":
            line_to_add = self.payload.get("github_line", "").strip()
            company = self.payload.get("company", "User").strip()
            secret_key = self.payload.get("secret_key", "").strip()

            if not line_to_add:
                self.finished.emit(False, "No license line data to push.", {})
                return

            try:
                file_get_url = f"{api_url}?ref={branch}"
                req = urllib.request.Request(file_get_url, headers=headers, method="GET")
                existing_sha = None
                existing_content = ""

                try:
                    with urllib.request.urlopen(req, timeout=15) as resp:
                        file_data = json.loads(resp.read().decode("utf-8"))
                        existing_sha = file_data.get("sha")
                        encoded_body = file_data.get("content", "")
                        raw_bytes = base64.b64decode(encoded_body.replace("\n", ""))
                        existing_content = raw_bytes.decode("utf-8", errors="replace")
                except urllib.error.HTTPError as e:
                    if e.code == 404:
                        existing_sha = None
                        existing_content = "# R1 BIOS TOOL LICENSE KEYS\n# Format: KEY|ISSUED|EXPIRY|COMPANY\n\n"
                    else:
                        raise e

                # Check if key is already present
                if secret_key and secret_key in existing_content:
                    self.finished.emit(True, "Key is already present in GitHub repository (Duplicate skipped).", {"duplicate": True})
                    return

                # Append new line
                if existing_content and not existing_content.endswith("\n"):
                    new_full_content = existing_content + "\n" + line_to_add + "\n"
                else:
                    new_full_content = existing_content + line_to_add + "\n"

                b64_new_content = base64.b64encode(new_full_content.encode("utf-8")).decode("utf-8")
                commit_message = f"Add license for {company} (Issued: {datetime.now().strftime('%Y-%m-%d')})"

                put_data = {
                    "message": commit_message,
                    "content": b64_new_content,
                    "branch": branch
                }
                if existing_sha:
                    put_data["sha"] = existing_sha

                put_req = urllib.request.Request(
                    api_url,
                    data=json.dumps(put_data).encode("utf-8"),
                    headers=headers,
                    method="PUT"
                )

                with urllib.request.urlopen(put_req, timeout=15) as put_resp:
                    res_body = json.loads(put_resp.read().decode("utf-8"))
                    commit_info = res_body.get("commit", {})
                    commit_sha = commit_info.get("sha", "")[:7]
                    self.finished.emit(
                        True,
                        f"Successfully pushed to GitHub! Commit: {commit_sha}",
                        {"commit_sha": commit_sha, "url": commit_info.get("html_url", "")}
                    )

            except urllib.error.HTTPError as e:
                err_msg = self._format_http_error(e)
                self.finished.emit(False, f"GitHub Push Failed: {err_msg}", {})
            except Exception as e:
                self.finished.emit(False, f"Push Error: {str(e)}", {})
            return

        # -------------------------------------------------------------------
        # 3. FETCH LICENSES LIST
        # -------------------------------------------------------------------
        if self.action == "fetch_list":
            try:
                file_get_url = f"{api_url}?ref={branch}"
                req = urllib.request.Request(file_get_url, headers=headers, method="GET")
                with urllib.request.urlopen(req, timeout=15) as resp:
                    file_data = json.loads(resp.read().decode("utf-8"))
                    encoded_body = file_data.get("content", "")
                    raw_bytes = base64.b64decode(encoded_body.replace("\n", ""))
                    content = raw_bytes.decode("utf-8", errors="replace")

                licenses = []
                for line in content.splitlines():
                    line_clean = line.strip()
                    if not line_clean or line_clean.startswith("#"):
                        continue
                    parts = line_clean.split("|")
                    key = parts[0].strip()
                    issued = parts[1].strip() if len(parts) > 1 else "-"
                    expiry = parts[2].strip() if len(parts) > 2 else "-"
                    company = parts[3].strip().replace("_", " ") if len(parts) > 3 else "Unknown"
                    note = parts[4].strip().replace("_", " ") if len(parts) > 4 else ""
                    hwids = parts[5].strip() if len(parts) > 5 else "ANY"
                    if not hwids:
                        hwids = "ANY"

                    # Fallback decoding from key payload if metadata missing
                    if company in ("Unknown", "-") or expiry == "-":
                        try:
                            dec = decrypt_payload(key)
                            if dec:
                                company = dec.get("company", company)
                                if "expiry_ts" in dec:
                                    exp_dt = datetime.fromtimestamp(dec["expiry_ts"], tz=timezone.utc).astimezone()
                                    expiry = exp_dt.strftime("%Y-%m-%d %H:%M:%S")
                                if dec.get("is_hwid_locked") and hwids == "ANY":
                                    hwids = dec.get("hwid", "ANY")
                        except Exception:
                            pass

                    status = parse_expiry_status(expiry)
                    licenses.append({
                        "key": key,
                        "company": company,
                        "issued": issued,
                        "expiry": expiry,
                        "hwids": hwids,
                        "note": note,
                        "status": status,
                        "raw_line": line_clean
                    })

                self.finished.emit(True, f"Loaded {len(licenses)} licenses from GitHub.", {"licenses": licenses})

            except urllib.error.HTTPError as e:
                if e.code == 404:
                    self.finished.emit(True, "File license_keys.txt does not exist yet on GitHub (0 licenses).", {"licenses": []})
                else:
                    err_msg = self._format_http_error(e)
                    self.finished.emit(False, f"Failed to fetch licenses: {err_msg}", {})
            except Exception as e:
                self.finished.emit(False, f"Fetch Error: {str(e)}", {})
            return

        # -------------------------------------------------------------------
        # 4. REMOVE / REVOKE LICENSE KEY
        # -------------------------------------------------------------------
        if self.action == "remove_key":
            key_to_remove = self.payload.get("key", "").strip()
            company_to_remove = self.payload.get("company", "Customer").strip()

            if not key_to_remove:
                self.finished.emit(False, "No key specified for removal.", {})
                return

            try:
                # Step A: Fetch current content and SHA
                file_get_url = f"{api_url}?ref={branch}"
                req = urllib.request.Request(file_get_url, headers=headers, method="GET")
                with urllib.request.urlopen(req, timeout=15) as resp:
                    file_data = json.loads(resp.read().decode("utf-8"))
                    existing_sha = file_data.get("sha")
                    encoded_body = file_data.get("content", "")
                    raw_bytes = base64.b64decode(encoded_body.replace("\n", ""))
                    content = raw_bytes.decode("utf-8", errors="replace")

                lines = content.splitlines()
                remaining_lines = []
                found = False

                for line in lines:
                    line_clean = line.strip()
                    if not line_clean or line_clean.startswith("#"):
                        remaining_lines.append(line)
                        continue
                    
                    if key_to_remove in line_clean:
                        found = True
                        continue  # Skip this line to remove it
                    remaining_lines.append(line)

                if not found:
                    self.finished.emit(False, "Key was not found in GitHub file (Already removed or not registered).", {})
                    return

                new_full_content = "\n".join(remaining_lines) + "\n"
                b64_new_content = base64.b64encode(new_full_content.encode("utf-8")).decode("utf-8")
                commit_message = f"Revoke license: {company_to_remove}"

                put_data = {
                    "message": commit_message,
                    "content": b64_new_content,
                    "branch": branch,
                    "sha": existing_sha
                }

                put_req = urllib.request.Request(
                    api_url,
                    data=json.dumps(put_data).encode("utf-8"),
                    headers=headers,
                    method="PUT"
                )

                with urllib.request.urlopen(put_req, timeout=15) as put_resp:
                    res_body = json.loads(put_resp.read().decode("utf-8"))
                    commit_info = res_body.get("commit", {})
                    commit_sha = commit_info.get("sha", "")[:7]
                    self.finished.emit(
                        True,
                        f"License for '{company_to_remove}' successfully revoked and removed from GitHub! (Commit: {commit_sha})",
                        {"commit_sha": commit_sha, "removed_key": key_to_remove}
                    )

            except urllib.error.HTTPError as e:
                err_msg = self._format_http_error(e)
                self.finished.emit(False, f"Revoke Failed: {err_msg}", {})
            except Exception as e:
                self.finished.emit(False, f"Revoke Error: {str(e)}", {})
            return

        # -------------------------------------------------------------------
        # 5. RENEW LICENSE KEY (Replace old line with new line on GitHub)
        # -------------------------------------------------------------------
        if self.action == "renew_key":
            old_key = self.payload.get("old_key", "").strip()
            new_line = self.payload.get("new_line", "").strip()
            company = self.payload.get("company", "Customer").strip()
            new_expiry_str = self.payload.get("new_expiry_str", "").strip()

            if not new_line:
                self.finished.emit(False, "No renewed license data provided.", {})
                return

            try:
                file_get_url = f"{api_url}?ref={branch}"
                req = urllib.request.Request(file_get_url, headers=headers, method="GET")
                with urllib.request.urlopen(req, timeout=15) as resp:
                    file_data = json.loads(resp.read().decode("utf-8"))
                    existing_sha = file_data.get("sha")
                    encoded_body = file_data.get("content", "")
                    raw_bytes = base64.b64decode(encoded_body.replace("\n", ""))
                    content = raw_bytes.decode("utf-8", errors="replace")

                lines = content.splitlines()
                new_lines = []
                replaced = False

                for line in lines:
                    line_clean = line.strip()
                    if not line_clean or line_clean.startswith("#"):
                        new_lines.append(line)
                        continue
                    if old_key and old_key in line_clean:
                        new_lines.append(new_line)
                        replaced = True
                    else:
                        new_lines.append(line)

                if not replaced:
                    new_lines.append(new_line)

                new_full_content = "\n".join(new_lines) + "\n"
                b64_new_content = base64.b64encode(new_full_content.encode("utf-8")).decode("utf-8")
                commit_message = f"Renew license for {company} (Expires: {new_expiry_str})"

                put_data = {
                    "message": commit_message,
                    "content": b64_new_content,
                    "branch": branch,
                    "sha": existing_sha
                }

                put_req = urllib.request.Request(
                    api_url,
                    data=json.dumps(put_data).encode("utf-8"),
                    headers=headers,
                    method="PUT"
                )

                with urllib.request.urlopen(put_req, timeout=15) as put_resp:
                    res_body = json.loads(put_resp.read().decode("utf-8"))
                    commit_info = res_body.get("commit", {})
                    commit_sha = commit_info.get("sha", "")[:7]
                    self.finished.emit(
                        True,
                        f"License for '{company}' successfully renewed and updated on GitHub! (Commit: {commit_sha})",
                        {"commit_sha": commit_sha, "new_line": new_line}
                    )

            except urllib.error.HTTPError as e:
                err_msg = self._format_http_error(e)
                self.finished.emit(False, f"Renewal Failed: {err_msg}", {})
            except Exception as e:
                self.finished.emit(False, f"Renewal Error: {str(e)}", {})
            return

        # -------------------------------------------------------------------
        # 6. RESET DEVICE LOCK (Reset registered HWID to UNBOUND on GitHub)
        # -------------------------------------------------------------------
        if self.action == "reset_device":
            target_key = self.payload.get("key", "").strip()
            company = self.payload.get("company", "Customer").strip()

            if not target_key:
                self.finished.emit(False, "No key specified to reset device lock.", {})
                return

            try:
                file_get_url = f"{api_url}?ref={branch}"
                req = urllib.request.Request(file_get_url, headers=headers, method="GET")
                with urllib.request.urlopen(req, timeout=15) as resp:
                    file_data = json.loads(resp.read().decode("utf-8"))
                    existing_sha = file_data.get("sha")
                    encoded_body = file_data.get("content", "")
                    raw_bytes = base64.b64decode(encoded_body.replace("\n", ""))
                    content = raw_bytes.decode("utf-8", errors="replace")

                lines = content.splitlines()
                new_lines = []
                reset_done = False

                for line in lines:
                    line_clean = line.strip()
                    if not line_clean or line_clean.startswith("#"):
                        new_lines.append(line)
                        continue

                    if target_key in line_clean:
                        parts = line_clean.split("|")
                        if len(parts) >= 6:
                            k = parts[0]
                            iss = parts[1]
                            exp = parts[2]
                            cmp = parts[3]
                            not_ = parts[4]
                            max_dev = parts[5]
                            new_lines.append(f"{k}|{iss}|{exp}|{cmp}|{not_}|{max_dev}|UNBOUND")
                        else:
                            new_lines.append(f"{line_clean}|1|UNBOUND")
                        reset_done = True
                    else:
                        new_lines.append(line)

                if not reset_done:
                    self.finished.emit(False, "Key was not found in remote file.", {})
                    return

                new_full_content = "\n".join(new_lines) + "\n"
                b64_new_content = base64.b64encode(new_full_content.encode("utf-8")).decode("utf-8")
                commit_message = f"Reset device lock for {company}"

                put_data = {
                    "message": commit_message,
                    "content": b64_new_content,
                    "branch": branch,
                    "sha": existing_sha
                }

                put_req = urllib.request.Request(
                    api_url,
                    data=json.dumps(put_data).encode("utf-8"),
                    headers=headers,
                    method="PUT"
                )

                with urllib.request.urlopen(put_req, timeout=15) as put_resp:
                    res_body = json.loads(put_resp.read().decode("utf-8"))
                    commit_info = res_body.get("commit", {})
                    commit_sha = commit_info.get("sha", "")[:7]
                    self.finished.emit(
                        True,
                        f"Device lock for '{company}' reset to UNBOUND! Customer can now activate on a new PC. (Commit: {commit_sha})",
                        {"commit_sha": commit_sha}
                    )

            except urllib.error.HTTPError as e:
                err_msg = self._format_http_error(e)
                self.finished.emit(False, f"Reset Failed: {err_msg}", {})
            except Exception as e:
                self.finished.emit(False, f"Reset Error: {str(e)}", {})
            return

    def _format_http_error(self, err):
        code = err.code
        try:
            body = json.loads(err.read().decode("utf-8"))
            detail = body.get("message", "")
        except Exception:
            detail = err.reason

        if code == 401:
            return "Unauthorized (401). Invalid or expired GitHub Token. Check Settings."
        elif code == 403:
            return f"Forbidden (403). Token lacks write permission or repository access ({detail})."
        elif code == 404:
            return f"Not Found (404). Repository or file path does not exist ({detail})."
        elif code == 409:
            return "Conflict (409). Remote file was modified concurrently. Try again."
        return f"HTTP {code}: {detail}"


# ---------------------------------------------------------------------------
# GitHub Settings Dialog
# ---------------------------------------------------------------------------
class GitHubSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GitHub Synchronization Settings")
        self.setFixedWidth(480)
        self.setStyleSheet("""
            QDialog { background-color: #1e1e24; color: #ffffff; font-family: 'Segoe UI', sans-serif; }
            QLabel { font-size: 12px; color: #d0d0d8; }
            QLineEdit {
                background-color: #2b2b36; border: 1px solid #444455; border-radius: 4px; padding: 6px; color: #ffffff;
            }
            QLineEdit:focus { border: 1px solid #00ff41; }
            QPushButton {
                background-color: #383848; color: #ffffff; font-weight: bold; padding: 8px 14px; border-radius: 4px; border: none;
            }
            QPushButton:hover { background-color: #48485c; }
        """)

        self.cfg = load_config()
        self.worker = None

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title_lbl = QLabel("GitHub Account & Repository Configuration")
        title_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #00ff41;")
        layout.addWidget(title_lbl)

        # Personal Access Token
        layout.addWidget(QLabel("Personal Access Token (PAT):"))
        token_layout = QHBoxLayout()
        self.txt_token = QLineEdit(self.cfg.get("github_token", ""))
        self.txt_token.setEchoMode(QLineEdit.Password)
        self.txt_token.setPlaceholderText("ghp_xxxxxxxxxxxxxxxxxxxx")
        token_layout.addWidget(self.txt_token)

        self.btn_toggle_token = QPushButton("Show")
        self.btn_toggle_token.setFixedWidth(60)
        self.btn_toggle_token.clicked.connect(self.toggle_token_visibility)
        token_layout.addWidget(self.btn_toggle_token)
        layout.addLayout(token_layout)

        help_lbl = QLabel("Token must have 'repo' or 'contents:write' scope permissions.")
        help_lbl.setStyleSheet("color: #8a8a9e; font-size: 11px;")
        layout.addWidget(help_lbl)

        # Repository
        layout.addWidget(QLabel("Repository (owner/repo):"))
        self.txt_repo = QLineEdit(clean_repo_name(self.cfg.get("repo", "rscomputer204-netizen/license_keys.txt")))
        self.txt_repo.setPlaceholderText("e.g. rscomputer204-netizen/license_keys.txt")
        layout.addWidget(self.txt_repo)

        # Branch
        layout.addWidget(QLabel("Branch:"))
        self.txt_branch = QLineEdit(self.cfg.get("branch", "main"))
        layout.addWidget(self.txt_branch)

        # File path
        layout.addWidget(QLabel("File Path inside Repository:"))
        self.txt_file = QLineEdit(self.cfg.get("file_path", "license_keys.txt"))
        layout.addWidget(self.txt_file)

        layout.addSpacing(5)

        # Test Connection Button & Status
        self.btn_test = QPushButton("Test GitHub Connection")
        self.btn_test.clicked.connect(self.test_connection)
        layout.addWidget(self.btn_test)

        self.lbl_status = QLabel("")
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setStyleSheet("font-size: 11px; padding: 6px; border-radius: 4px;")
        layout.addWidget(self.lbl_status)

        layout.addSpacing(10)

        # Dialog Buttons
        btn_box = QHBoxLayout()
        self.btn_save = QPushButton("Save Settings")
        self.btn_save.setStyleSheet("background-color: #00ff41; color: black; font-weight: bold;")
        self.btn_save.clicked.connect(self.save_and_close)
        btn_box.addWidget(self.btn_save)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(self.btn_cancel)
        layout.addLayout(btn_box)

    def toggle_token_visibility(self):
        if self.txt_token.echoMode() == QLineEdit.Password:
            self.txt_token.setEchoMode(QLineEdit.Normal)
            self.btn_toggle_token.setText("Hide")
        else:
            self.txt_token.setEchoMode(QLineEdit.Password)
            self.btn_toggle_token.setText("Show")

    def test_connection(self):
        token = self.txt_token.text().strip()
        repo = clean_repo_name(self.txt_repo.text().strip())

        if not token:
            self.lbl_status.setStyleSheet("background-color: #3d1b1b; color: #ff5252; padding: 6px; border-radius: 4px;")
            self.lbl_status.setText("Please enter a GitHub Personal Access Token.")
            return

        self.btn_test.setEnabled(False)
        self.btn_test.setText("Testing Connection...")
        self.lbl_status.setStyleSheet("background-color: #3b3518; color: #ffd600; padding: 6px; border-radius: 4px;")
        self.lbl_status.setText("Connecting to GitHub API...")

        test_cfg = {
            "github_token": token,
            "repo": repo,
            "branch": self.txt_branch.text().strip() or "main",
            "file_path": self.txt_file.text().strip() or "license_keys.txt"
        }

        self.worker = GitHubSyncWorker("test", test_cfg)
        self.worker.finished.connect(self.on_test_finished)
        self.worker.start()

    def on_test_finished(self, success, message, details):
        self.btn_test.setEnabled(True)
        self.btn_test.setText("Test GitHub Connection")
        if success:
            self.lbl_status.setStyleSheet("background-color: #1b3d22; color: #00ff41; font-weight: bold; padding: 6px; border-radius: 4px;")
            self.lbl_status.setText(f"[CONNECTED] {message}")
        else:
            self.lbl_status.setStyleSheet("background-color: #3d1b1b; color: #ff5252; padding: 6px; border-radius: 4px;")
            self.lbl_status.setText(f"[ERROR] {message}")

    def save_and_close(self):
        self.cfg["github_token"] = self.txt_token.text().strip()
        self.cfg["repo"] = clean_repo_name(self.txt_repo.text().strip())
        self.cfg["branch"] = self.txt_branch.text().strip()
        self.cfg["file_path"] = self.txt_file.text().strip()
        save_config(self.cfg)
        self.accept()


# ---------------------------------------------------------------------------
# License Renewal Dialog
# ---------------------------------------------------------------------------
class LicenseRenewalDialog(QDialog):
    def __init__(self, parent, license_data, config):
        super().__init__(parent)
        self.license_data = license_data
        self.config = config
        self.company = license_data.get("company", "Customer")
        self.old_key = license_data.get("key", "")
        self.old_expiry = license_data.get("expiry", "")
        self.generated_new_key = ""
        self.worker = None

        self.setWindowTitle(f"Renew License - {self.company}")
        self.setFixedWidth(520)
        self.setStyleSheet("""
            QDialog { background-color: #1a1a22; color: #ffffff; font-family: 'Segoe UI', sans-serif; }
            QLabel { font-size: 12px; color: #d0d0d8; font-weight: 600; }
            QLineEdit, QTextEdit, QDateEdit, QTimeEdit {
                background-color: #272734; border: 1px solid #3d3d52; border-radius: 4px; padding: 6px; color: #ffffff; font-size: 12px;
            }
            QLineEdit:focus, QTextEdit:focus, QDateEdit:focus, QTimeEdit:focus {
                border: 1px solid #00ff41;
            }
            QPushButton {
                background-color: #2e2e3e; color: #ffffff; font-weight: bold; padding: 8px 12px; border-radius: 4px; border: 1px solid #3d3d52;
            }
            QPushButton:hover { background-color: #3d3d54; }
            QPushButton#btn_renew_action {
                background-color: #0288d1; color: #ffffff; font-weight: bold; border: none; padding: 10px; font-size: 13px;
            }
            QPushButton#btn_renew_action:hover { background-color: #039be5; }
            QPushButton#btn_copy {
                background-color: #238636; color: #ffffff; font-weight: bold; border: none; padding: 8px;
            }
            QPushButton#btn_copy:hover { background-color: #2ea043; }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title = QLabel(f"License Renewal for: {self.company}")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #00ff41;")
        layout.addWidget(title)

        status_info = QLabel(f"Current Expiry Date: {self.old_expiry}")
        status_info.setStyleSheet("color: #ffd600; font-size: 12px;")
        layout.addWidget(status_info)

        # Quick Add Buttons
        layout.addWidget(QLabel("Extend Validity by:"))
        ext_layout = QHBoxLayout()
        ext_presets = [
            ("+1 Month", 1),
            ("+3 Months", 3),
            ("+6 Months", 6),
            ("+1 Year", 12),
        ]
        for label, months in ext_presets:
            btn = QPushButton(label)
            btn.clicked.connect(lambda checked=False, m=months: self.add_months(m))
            ext_layout.addWidget(btn)
        ext_layout.addStretch()
        layout.addLayout(ext_layout)

        # Expiry Date & Time inputs
        dt_layout = QHBoxLayout()
        date_vbox = QVBoxLayout()
        date_vbox.addWidget(QLabel("New Expiry Date:"))
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate().addMonths(1))
        date_vbox.addWidget(self.date_edit)
        dt_layout.addLayout(date_vbox)

        time_vbox = QVBoxLayout()
        time_vbox.addWidget(QLabel("New Expiry Time:"))
        self.time_edit = QTimeEdit()
        self.time_edit.setTime(QTime(23, 59, 59))
        time_vbox.addWidget(self.time_edit)
        dt_layout.addLayout(time_vbox)
        layout.addLayout(dt_layout)

        layout.addWidget(QLabel("Device HWID (Lock to PC / Comma-separated for 2 PCs / ANY):"))
        self.txt_hwid = QLineEdit(self.license_data.get("hwids", "ANY"))
        self.txt_hwid.setStyleSheet("font-family: 'Consolas', monospace; font-weight: bold;")
        self.txt_hwid.setPlaceholderText("e.g. R1-HW-1344-46E3 or ANY")
        layout.addWidget(self.txt_hwid)

        layout.addWidget(QLabel("Note (optional):"))
        self.txt_note = QLineEdit()
        self.txt_note.setText(f"Renewed_{datetime.now().strftime('%Y-%m-%d')}")
        layout.addWidget(self.txt_note)

        # Action Button: Renew & Update GitHub
        self.btn_action = QPushButton("Renew & Update GitHub")
        self.btn_action.setObjectName("btn_renew_action")
        self.btn_action.clicked.connect(self.perform_renewal)
        layout.addWidget(self.btn_action)

        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("font-size: 11px; padding: 4px;")
        layout.addWidget(self.lbl_status)

        # Output Section (revealed after success)
        self.output_group = QGroupBox("New Software License Key")
        self.output_group.setVisible(False)
        out_layout = QVBoxLayout(self.output_group)
        
        lbl_inst = QLabel("Give this new key to customer:")
        lbl_inst.setStyleSheet("font-size: 11px; color: #a0a0b5;")
        out_layout.addWidget(lbl_inst)

        self.txt_new_key = QTextEdit()
        self.txt_new_key.setReadOnly(True)
        self.txt_new_key.setMaximumHeight(54)
        self.txt_new_key.setStyleSheet("font-family: 'Consolas', 'Courier New', monospace; font-size: 14px; font-weight: bold; color: #00ff41; padding: 4px;")
        out_layout.addWidget(self.txt_new_key)

        btn_copy_new = QPushButton("Copy New Key")
        btn_copy_new.setObjectName("btn_copy")
        btn_copy_new.clicked.connect(self.copy_new_key)
        out_layout.addWidget(btn_copy_new)
        layout.addWidget(self.output_group)

        # Close button
        self.btn_close = QPushButton("Done / Close")
        self.btn_close.clicked.connect(self.accept)
        layout.addWidget(self.btn_close)

    def add_months(self, months):
        base_date = QDate.currentDate()
        try:
            exp_clean = self.old_expiry.split()[0]
            parts = [int(p) for p in exp_clean.split("-")]
            qd = QDate(parts[0], parts[1], parts[2])
            if qd > base_date:
                base_date = qd
        except Exception:
            pass
        self.date_edit.setDate(base_date.addMonths(months))

    def perform_renewal(self):
        dt = self.date_edit.date()
        tm = self.time_edit.time()

        expiry_dt = datetime(dt.year(), dt.month(), dt.day(), tm.hour(), tm.minute(), tm.second())
        expiry_ts = expiry_dt.replace(tzinfo=datetime.now().astimezone().tzinfo).astimezone(timezone.utc).timestamp()
        issued_ts = datetime.now(timezone.utc).timestamp()

        hwid_str = self.txt_hwid.text().strip().upper() or "ANY"
        first_hwid = hwid_str.split(",")[0].strip() if hwid_str != "ANY" else None

        payload = {
            "company": self.company,
            "expiry_ts": expiry_ts,
            "issued_ts": issued_ts,
            "hwid": first_hwid,
            "uuid": str(uuid.uuid4())
        }

        new_secret_key = encrypt_payload(payload)
        expiry_str = expiry_dt.strftime("%Y-%m-%d %H:%M:%S")
        issued_str = datetime.now().strftime("%Y-%m-%d")
        note = self.txt_note.text().strip() or "Renewed"
        note = note.replace("|", "_").replace(" ", "_")
        company_clean = self.company.replace("|", "_").replace(" ", "_")

        new_line = f"{new_secret_key}|{issued_str}|{expiry_str}|{company_clean}|{note}|{hwid_str}"
        self.generated_new_key = new_secret_key

        self.btn_action.setEnabled(False)
        self.btn_action.setText("Updating GitHub...")
        self.lbl_status.setStyleSheet("color: #ffd600;")
        self.lbl_status.setText("Committing renewal to GitHub repository...")

        worker_payload = {
            "old_key": self.old_key,
            "new_line": new_line,
            "company": self.company,
            "new_expiry_str": expiry_str
        }

        self.worker = GitHubSyncWorker("renew_key", self.config, worker_payload)
        self.worker.finished.connect(self.on_renewal_finished)
        self.worker.start()

    def on_renewal_finished(self, success, message, details):
        self.btn_action.setEnabled(True)
        self.btn_action.setText("Renew & Update GitHub")

        if success:
            self.lbl_status.setStyleSheet("color: #00ff41; font-weight: bold;")
            self.lbl_status.setText("Renewal Successful! Key updated on GitHub.")
            self.txt_new_key.setText(self.generated_new_key)
            self.output_group.setVisible(True)
            QMessageBox.information(self, "Renewal Successful", f"License renewed successfully for '{self.company}'!\n\nSend the new key to the customer.")
        else:
            self.lbl_status.setStyleSheet("color: #ff5252;")
            self.lbl_status.setText(message)
            QMessageBox.critical(self, "Renewal Failed", message)

    def copy_new_key(self):
        if self.generated_new_key:
            QApplication.clipboard().setText(self.generated_new_key)
            QMessageBox.information(self, "Copied", "New License Key copied to clipboard!")


# ---------------------------------------------------------------------------
# Main Key Generator & License Manager Window
# ---------------------------------------------------------------------------
class KeyGenerator(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("R1 BIOS TOOL - License Key Generator & Manager")
        self.setMinimumSize(560, 620)
        self.resize(580, 680)

        self.cfg = load_config()
        self.generated_secret_key = ""
        self.generated_github_line = ""
        self.all_licenses = []
        self.is_github_connected = False

        self.sync_worker = None
        self.status_worker = None
        self.fetch_worker = None
        self.remove_worker = None

        self.apply_styles()
        self.init_ui()

        # Auto-check connection on launch
        QTimer.singleShot(250, self.check_connection)

    def apply_styles(self):
        self.setStyleSheet("""
            QWidget { 
                background-color: #151518; 
                color: #f0f0f5; 
                font-family: 'Segoe UI', sans-serif; 
            }
            QTabWidget::pane {
                border: 1px solid #2d2d38;
                background-color: #1a1a20;
                border-radius: 6px;
            }
            QTabBar::tab {
                background-color: #202028;
                color: #9e9eb0;
                font-weight: bold;
                font-size: 12px;
                padding: 10px 20px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background-color: #1a1a20;
                color: #00ff41;
                border-bottom: 2px solid #00ff41;
            }
            QTabBar::tab:hover:!selected {
                background-color: #2a2a35;
                color: #ffffff;
            }
            QGroupBox {
                background-color: #1e1e24;
                border: 1px solid #2d2d38;
                border-radius: 6px;
                margin-top: 12px;
                font-weight: bold;
                font-size: 12px;
                color: #00ff41;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 2px 8px;
                background-color: #1e1e24;
            }
            QLabel { 
                font-weight: 600; 
                font-size: 12px; 
                color: #d8d8e0;
            }
            QLineEdit, QTextEdit, QDateEdit, QTimeEdit {
                background-color: #272732; 
                border: 1px solid #3d3d4e; 
                border-radius: 4px; 
                padding: 6px; 
                color: #ffffff;
                font-size: 12px;
            }
            QLineEdit:focus, QTextEdit:focus, QDateEdit:focus, QTimeEdit:focus {
                border: 1px solid #00ff41;
            }
            QPushButton {
                background-color: #2d2d3a; 
                color: #ffffff; 
                font-weight: bold; 
                padding: 8px 12px; 
                border-radius: 4px; 
                border: 1px solid #3d3d4e;
            }
            QPushButton:hover { 
                background-color: #3b3b4d; 
                border-color: #55556d;
            }
            QPushButton#btn_primary {
                background-color: #00ff41; 
                color: #000000; 
                font-weight: bold; 
                font-size: 13px;
                padding: 10px; 
                border: none;
            }
            QPushButton#btn_primary:hover { 
                background-color: #00cc33; 
            }
            QPushButton#btn_github {
                background-color: #238636; 
                color: #ffffff; 
                font-weight: bold; 
                border: none;
                padding: 8px 14px;
            }
            QPushButton#btn_github:hover { 
                background-color: #2ea043; 
            }
            QPushButton#btn_danger {
                background-color: #c62828; 
                color: #ffffff; 
                font-weight: bold; 
                border: none;
                padding: 8px 14px;
            }
            QPushButton#btn_danger:hover { 
                background-color: #e53935; 
            }
            QTableWidget {
                background-color: #1b1b22;
                gridline-color: #2c2c38;
                border: 1px solid #2d2d38;
                border-radius: 4px;
                color: #ffffff;
                selection-background-color: #2a3d5e;
                selection-color: #ffffff;
            }
            QHeaderView::section {
                background-color: #24242e;
                color: #00ff41;
                font-weight: bold;
                font-size: 11px;
                padding: 6px;
                border: 1px solid #2c2c38;
            }
            QCheckBox {
                color: #b0b0be;
                font-size: 12px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
        """)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(10)

        # Header Title
        header_layout = QHBoxLayout()
        header_vbox = QVBoxLayout()
        title_lbl = QLabel("R1 BIOS TOOL - License Key Generator & Manager")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        subtitle_lbl = QLabel("Manage company licenses, live GitHub verification & one-click revocation")
        subtitle_lbl.setStyleSheet("font-size: 11px; color: #8a8a9e; font-weight: normal;")
        header_vbox.addWidget(title_lbl)
        header_vbox.addWidget(subtitle_lbl)
        header_layout.addLayout(header_vbox)

        header_layout.addStretch()

        btn_settings = QPushButton("GitHub Settings")
        btn_settings.clicked.connect(self.open_settings)
        header_layout.addWidget(btn_settings)
        main_layout.addLayout(header_layout)

        # Live GitHub Connection Indicator Badge Bar
        status_bar_layout = QHBoxLayout()
        status_bar_layout.setContentsMargins(0, 0, 0, 0)
        
        self.badge_indicator = QLabel("● Checking GitHub Status...")
        self.badge_indicator.setStyleSheet("""
            background-color: #282414; 
            color: #ffd600; 
            font-weight: bold; 
            font-size: 11px; 
            padding: 5px 10px; 
            border-radius: 12px; 
            border: 1px solid #554818;
        """)
        status_bar_layout.addWidget(self.badge_indicator)

        status_bar_layout.addStretch()

        self.btn_refresh_conn = QPushButton("Check Connection")
        self.btn_refresh_conn.setStyleSheet("padding: 4px 10px; font-size: 11px;")
        self.btn_refresh_conn.clicked.connect(self.check_connection)
        status_bar_layout.addWidget(self.btn_refresh_conn)

        main_layout.addLayout(status_bar_layout)

        # Separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #2b2b36;")
        main_layout.addWidget(sep)

        # Main Tab Widget
        self.tabs = QTabWidget()
        self.tab_generator = QWidget()
        self.tab_manager = QWidget()

        self.init_generator_tab()
        self.init_manager_tab()

        self.tabs.addTab(self.tab_generator, "Generate & Push Key")
        self.tabs.addTab(self.tab_manager, "GitHub License Manager")
        self.tabs.currentChanged.connect(self.on_tab_changed)

        main_layout.addWidget(self.tabs)

        # Bottom Status Notification Bar
        self.lbl_main_status = QLabel("Ready")
        self.lbl_main_status.setStyleSheet("""
            background-color: #1e1e24; 
            border: 1px solid #2d2d38; 
            border-radius: 4px; 
            padding: 6px 10px; 
            font-size: 12px; 
            color: #9e9eb0;
        """)
        main_layout.addWidget(self.lbl_main_status)

    # -----------------------------------------------------------------------
    # TAB 1: Key Generator & Single Push
    # -----------------------------------------------------------------------
    def init_generator_tab(self):
        # Outer layout for the tab: just holds the scroll area
        outer_layout = QVBoxLayout(self.tab_generator)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # Scroll Area wrapping all content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")
        outer_layout.addWidget(scroll_area)

        # Inner container widget inside the scroll area
        inner_widget = QWidget()
        inner_widget.setStyleSheet("background-color: transparent;")
        scroll_area.setWidget(inner_widget)

        tab_layout = QVBoxLayout(inner_widget)
        tab_layout.setContentsMargins(12, 12, 12, 12)
        tab_layout.setSpacing(10)

        # 1. License Details Section
        details_group = QGroupBox("License Parameters")
        details_layout = QVBoxLayout(details_group)
        details_layout.setSpacing(8)

        details_layout.addWidget(QLabel("Company / User Name:"))
        self.txt_company = QLineEdit()
        self.txt_company.setPlaceholderText("e.g. Star Tech & Engineering")
        self.txt_company.setMinimumHeight(32)
        details_layout.addWidget(self.txt_company)

        # Quick Duration Presets
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Quick Presets:"))
        
        presets = [
            ("1 Month", lambda: self.set_duration_months(1)),
            ("3 Months", lambda: self.set_duration_months(3)),
            ("6 Months", lambda: self.set_duration_months(6)),
            ("1 Year", lambda: self.set_duration_years(1)),
            ("Lifetime", lambda: self.set_duration_years(10)),
        ]
        for name, callback in presets:
            btn_p = QPushButton(name)
            btn_p.setStyleSheet("padding: 4px 8px; font-size: 11px;")
            btn_p.clicked.connect(callback)
            preset_layout.addWidget(btn_p)
        preset_layout.addStretch()
        details_layout.addLayout(preset_layout)

        # Date and Time
        dt_layout = QHBoxLayout()
        
        date_vbox = QVBoxLayout()
        date_vbox.addWidget(QLabel("Expiry Date:"))
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate().addMonths(1))
        self.date_edit.setMinimumHeight(32)
        date_vbox.addWidget(self.date_edit)
        dt_layout.addLayout(date_vbox)

        time_vbox = QVBoxLayout()
        time_vbox.addWidget(QLabel("Expiry Time:"))
        self.time_edit = QTimeEdit()
        self.time_edit.setTime(QTime(23, 59, 59))
        self.time_edit.setMinimumHeight(32)
        time_vbox.addWidget(self.time_edit)
        dt_layout.addLayout(time_vbox)

        details_layout.addLayout(dt_layout)

        details_layout.addWidget(QLabel("Note (optional):"))
        self.txt_note = QLineEdit()
        self.txt_note.setPlaceholderText("e.g. 1 Month License for Customer A")
        self.txt_note.setMinimumHeight(32)
        details_layout.addWidget(self.txt_note)

        tab_layout.addWidget(details_group)

        # 1.5 Device Limiter (Auto-Locks on Customer's First Activation)
        hwid_group = QGroupBox("Device Limit (Auto-Locks on Customer's First Activation)")
        hwid_vbox = QVBoxLayout(hwid_group)
        hwid_vbox.setSpacing(8)

        limit_layout = QHBoxLayout()
        self.radio_1_device = QRadioButton("1 Device (Recommended - Single PC)")
        self.radio_2_devices = QRadioButton("2 Devices (Allows 2 PCs)")
        self.radio_any_device = QRadioButton("Unlimited (Any PC)")
        self.radio_1_device.setChecked(True)
        limit_layout.addWidget(self.radio_1_device)
        limit_layout.addWidget(self.radio_2_devices)
        limit_layout.addWidget(self.radio_any_device)
        limit_layout.addStretch()
        hwid_vbox.addLayout(limit_layout)

        info_lbl = QLabel("✨ Zero hassle: No need to ask for customer's HWID! The key will automatically lock to their PC on first activation.")
        info_lbl.setStyleSheet("color: #a0a0b8; font-size: 11px; font-weight: normal;")
        hwid_vbox.addWidget(info_lbl)

        tab_layout.addWidget(hwid_group)

        # -------------------------------------------------------------------
        # BIG PROMINENT GENERATE BUTTON
        # -------------------------------------------------------------------
        self.btn_gen = QPushButton("GENERATE LICENSE KEY")
        self.btn_gen.setObjectName("btn_primary")
        self.btn_gen.setFixedHeight(48)
        self.btn_gen.setStyleSheet("""
            QPushButton {
                background-color: #00ff41; 
                color: #000000; 
                font-weight: 900; 
                font-size: 14px; 
                border-radius: 5px; 
                border: none;
            }
            QPushButton:hover { 
                background-color: #00cc33; 
            }
        """)
        self.btn_gen.clicked.connect(self.generate_key)
        tab_layout.addWidget(self.btn_gen)

        # 2. Key Output Section
        output_group = QGroupBox("Generated Keys")
        output_layout = QVBoxLayout(output_group)
        output_layout.setSpacing(8)

        # Output 1: Software License Key
        output_layout.addWidget(QLabel("Software License Key (Give this to the user):"))
        self.txt_key_output = QTextEdit()
        self.txt_key_output.setReadOnly(True)
        self.txt_key_output.setFixedHeight(56)
        self.txt_key_output.setStyleSheet("font-family: 'Consolas', 'Courier New', monospace; font-size: 15px; font-weight: bold; color: #00ff41; padding: 6px;")
        output_layout.addWidget(self.txt_key_output)

        self.btn_copy_key = QPushButton("Copy Key")
        self.btn_copy_key.setMinimumHeight(34)
        self.btn_copy_key.clicked.connect(self.copy_key_only)
        output_layout.addWidget(self.btn_copy_key)

        output_layout.addSpacing(6)

        # Output 2: GitHub Line Format
        output_layout.addWidget(QLabel("GitHub Line Format (Paste in license_keys.txt):"))
        self.txt_github_output = QTextEdit()
        self.txt_github_output.setReadOnly(True)
        self.txt_github_output.setFixedHeight(56)
        self.txt_github_output.setStyleSheet("font-family: 'Consolas', 'Courier New', monospace; font-size: 11px; color: #a0d8ef; padding: 6px;")
        output_layout.addWidget(self.txt_github_output)

        self.btn_github_action = QPushButton("Copy GitHub Line")
        self.btn_github_action.setFixedHeight(40)
        self.btn_github_action.clicked.connect(self.handle_github_action)
        output_layout.addWidget(self.btn_github_action)

        tab_layout.addWidget(output_group)

        # Push spacer to keep content anchored at top
        tab_layout.addStretch()

    # -----------------------------------------------------------------------
    # TAB 2: GitHub License Manager (View, Search, Revoke)
    # -----------------------------------------------------------------------
    def init_manager_tab(self):
        tab_layout = QVBoxLayout(self.tab_manager)
        tab_layout.setContentsMargins(8, 8, 8, 8)
        tab_layout.setSpacing(8)

        # Top Control Bar
        top_bar = QHBoxLayout()
        
        self.lbl_license_summary = QLabel("Total: 0 | Active: 0 | Expired: 0")
        self.lbl_license_summary.setStyleSheet("font-weight: bold; color: #00ff41; font-size: 12px;")
        top_bar.addWidget(self.lbl_license_summary)

        top_bar.addStretch()

        self.btn_refresh_list = QPushButton("Refresh from GitHub")
        self.btn_refresh_list.setStyleSheet("background-color: #238636; color: white; padding: 6px 12px; font-weight: bold;")
        self.btn_refresh_list.clicked.connect(self.fetch_licenses_from_github)
        top_bar.addWidget(self.btn_refresh_list)

        tab_layout.addLayout(top_bar)

        # Filter Search Bar
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Filter:"))
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Type company name or note to filter...")
        self.txt_search.textChanged.connect(self.filter_table)
        search_layout.addWidget(self.txt_search)
        tab_layout.addLayout(search_layout)

        # Table Widget
        self.table_licenses = QTableWidget()
        self.table_licenses.setColumnCount(7)
        self.table_licenses.setHorizontalHeaderLabels([
            "Company / User Name", "Status", "Issued Date", "Expiry Date", "Device Lock (HWID)", "Note", "License Key"
        ])
        self.table_licenses.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_licenses.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_licenses.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_licenses.setAlternatingRowColors(True)
        self.table_licenses.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
        self.table_licenses.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_licenses.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_licenses.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table_licenses.horizontalHeader().setSectionResizeMode(4, QHeaderView.Interactive)
        self.table_licenses.horizontalHeader().setSectionResizeMode(5, QHeaderView.Interactive)
        self.table_licenses.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)
        self.table_licenses.setColumnWidth(0, 150)
        self.table_licenses.setColumnWidth(4, 150)
        self.table_licenses.setColumnWidth(5, 110)
        
        # Enable Right-Click Menu, Double-Click Copy, and Ctrl+C Shortcut
        self.table_licenses.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_licenses.customContextMenuRequested.connect(self._show_table_context_menu)
        self.table_licenses.cellDoubleClicked.connect(self._on_table_cell_double_clicked)
        
        self.table_copy_shortcut = QShortcut(QKeySequence.Copy, self.table_licenses)
        self.table_copy_shortcut.activated.connect(self.copy_selected_key)
        
        tab_layout.addWidget(self.table_licenses)

        # Action Buttons below table
        action_bar = QHBoxLayout()
        action_bar.setSpacing(8)
        
        self.btn_copy_selected = QPushButton("📋 Copy Key")
        self.btn_copy_selected.setStyleSheet("background-color: #238636; color: white; font-weight: bold; border: none; padding: 8px 14px; border-radius: 4px;")
        self.btn_copy_selected.setToolTip("Copy the selected activation key to clipboard (Ctrl+C or Double-Click)")
        self.btn_copy_selected.clicked.connect(self.copy_selected_key)
        action_bar.addWidget(self.btn_copy_selected)

        self.btn_renew = QPushButton("🔄 Renew")
        self.btn_renew.setObjectName("btn_renew")
        self.btn_renew.setStyleSheet("background-color: #0288d1; color: white; font-weight: bold; border: none; padding: 8px 14px; border-radius: 4px;")
        self.btn_renew.clicked.connect(self.renew_selected_license)
        action_bar.addWidget(self.btn_renew)

        self.btn_reset_device = QPushButton("🔓 Reset Lock")
        self.btn_reset_device.setStyleSheet("background-color: #d97706; color: white; font-weight: bold; border: none; padding: 8px 14px; border-radius: 4px;")
        self.btn_reset_device.clicked.connect(self.reset_selected_device_lock)
        action_bar.addWidget(self.btn_reset_device)

        self.btn_revoke = QPushButton("🗑 Remove")
        self.btn_revoke.setObjectName("btn_danger")
        self.btn_revoke.setStyleSheet("background-color: #b91c1c; color: white; font-weight: bold; border: none; padding: 8px 14px; border-radius: 4px;")
        self.btn_revoke.clicked.connect(self.remove_selected_license)
        action_bar.addWidget(self.btn_revoke)

        action_bar.addStretch()

        tab_layout.addLayout(action_bar)

    def on_tab_changed(self, index):
        # When switching to Manager tab, auto-load if empty
        if index == 1 and not self.all_licenses:
            self.fetch_licenses_from_github()

    # -----------------------------------------------------------------------
    # License Manager Logic: Fetch, Filter, Revoke
    # -----------------------------------------------------------------------
    def fetch_licenses_from_github(self):
        self.cfg = load_config()
        token = self.cfg.get("github_token", "").strip()
        if not token:
            self.set_status("Please configure your GitHub Token in Settings to load licenses.", color="#ff5252")
            return

        self.btn_refresh_list.setEnabled(False)
        self.btn_refresh_list.setText("Fetching...")
        self.set_status("Fetching active licenses from GitHub repository...", color="#ffd600")

        self.fetch_worker = GitHubSyncWorker("fetch_list", self.cfg)
        self.fetch_worker.finished.connect(self.on_fetch_finished)
        self.fetch_worker.start()

    def on_fetch_finished(self, success, message, details):
        self.btn_refresh_list.setEnabled(True)
        self.btn_refresh_list.setText("Refresh from GitHub")

        if not success:
            self.set_status(message, color="#ff5252")
            QMessageBox.critical(self, "Fetch Error", message)
            return

        self.all_licenses = details.get("licenses", [])
        self.populate_table(self.all_licenses)
        self.set_status(f"Loaded {len(self.all_licenses)} licenses from GitHub.", color="#00ff41")

    def populate_table(self, licenses):
        self.table_licenses.setRowCount(0)
        active_count = 0
        expired_count = 0

        for row_idx, lic in enumerate(licenses):
            self.table_licenses.insertRow(row_idx)

            company_item = QTableWidgetItem(lic.get("company", ""))
            company_item.setFont(QFont("Segoe UI", 9, QFont.Bold))

            status_str = lic.get("status", "ACTIVE")
            status_item = QTableWidgetItem(f" {status_str} ")
            status_item.setTextAlignment(Qt.AlignCenter)
            if status_str == "ACTIVE":
                status_item.setForeground(QColor("#00ff41"))
                active_count += 1
            else:
                status_item.setForeground(QColor("#ff5252"))
                expired_count += 1

            issued_item = QTableWidgetItem(lic.get("issued", ""))
            expiry_item = QTableWidgetItem(lic.get("expiry", ""))

            hwid_val = lic.get("hwids", "UNBOUND")
            max_dev = lic.get("max_devices", 1)

            if hwid_val in ("UNBOUND", "NONE", ""):
                hwid_display = f"⏳ Pending Activation (0/{max_dev})"
                hwid_color = "#ffd600"
            elif hwid_val == "ANY":
                hwid_display = "🌐 Unlimited (Any PC)"
                hwid_color = "#00d2ff"
            else:
                hwid_display = f"🔒 {hwid_val}"
                hwid_color = "#00ff41"

            hwid_item = QTableWidgetItem(hwid_display)
            hwid_item.setFont(QFont("Consolas", 8, QFont.Bold))
            hwid_item.setForeground(QColor(hwid_color))

            note_item = QTableWidgetItem(lic.get("note", ""))

            key_full = lic.get("key", "")
            key_item = QTableWidgetItem(key_full)
            key_item.setFont(QFont("Consolas", 9, QFont.Bold))
            key_item.setData(Qt.UserRole, key_full)  # Store full key

            self.table_licenses.setItem(row_idx, 0, company_item)
            self.table_licenses.setItem(row_idx, 1, status_item)
            self.table_licenses.setItem(row_idx, 2, issued_item)
            self.table_licenses.setItem(row_idx, 3, expiry_item)
            self.table_licenses.setItem(row_idx, 4, hwid_item)
            self.table_licenses.setItem(row_idx, 5, note_item)
            self.table_licenses.setItem(row_idx, 6, key_item)

        self.lbl_license_summary.setText(f"Total: {len(licenses)} | Active: {active_count} | Expired: {expired_count}")

    def filter_table(self, text):
        query = text.strip().lower()
        for row in range(self.table_licenses.rowCount()):
            company = self.table_licenses.item(row, 0).text().lower()
            hwid = self.table_licenses.item(row, 4).text().lower()
            note = self.table_licenses.item(row, 5).text().lower()
            match = (query in company) or (query in note) or (query in hwid)
            self.table_licenses.setRowHidden(row, not match)

    def remove_selected_license(self):
        selected_row = self.table_licenses.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Select License", "Please select a license from the table to remove.")
            return

        company = self.table_licenses.item(selected_row, 0).text()
        key_item = self.table_licenses.item(selected_row, 6)
        full_key = key_item.data(Qt.UserRole) or key_item.text()

        reply = QMessageBox.question(
            self,
            "Confirm Revocation",
            f"Are you sure you want to revoke and remove the license for:\n\n"
            f"Company: {company}\n\n"
            f"This will delete it directly from GitHub and deactivate the customer's software.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        self.btn_revoke.setEnabled(False)
        self.btn_revoke.setText("Removing from GitHub...")
        self.set_status(f"Revoking license for '{company}' from GitHub...", color="#ffd600")

        payload = {
            "key": full_key,
            "company": company
        }

        self.remove_worker = GitHubSyncWorker("remove_key", self.cfg, payload)
        self.remove_worker.finished.connect(self.on_remove_finished)
        self.remove_worker.start()

    def on_remove_finished(self, success, message, details):
        self.btn_revoke.setEnabled(True)
        self.btn_revoke.setText("Remove from GitHub")

        if success:
            self.set_status(message, color="#00ff41")
            QMessageBox.information(self, "Revocation Successful", message)
            # Refresh list
            self.fetch_licenses_from_github()
        else:
            self.set_status(message, color="#ff5252")
            QMessageBox.critical(self, "Revocation Error", message)

    def reset_selected_device_lock(self):
        selected_row = self.table_licenses.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Select License", "Please select a license from the table to reset device lock.")
            return

        company = self.table_licenses.item(selected_row, 0).text()
        key_item = self.table_licenses.item(selected_row, 6)
        full_key = key_item.data(Qt.UserRole) or key_item.text()

        reply = QMessageBox.question(
            self,
            "Reset Device Lock",
            f"Are you sure you want to reset the device lock for:\n\n"
            f"Company: {company}\n\n"
            f"This will clear the registered computer and set it back to UNBOUND on GitHub.\n"
            f"The customer will be able to activate the key on a new computer.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        self.btn_reset_device.setEnabled(False)
        self.btn_reset_device.setText("Resetting...")
        self.set_status(f"Resetting device lock for '{company}' on GitHub...", color="#ffd600")

        payload = {
            "key": full_key,
            "company": company
        }

        self.reset_worker = GitHubSyncWorker("reset_device", self.cfg, payload)
        self.reset_worker.finished.connect(self.on_reset_device_finished)
        self.reset_worker.start()

    def on_reset_device_finished(self, success, message, details):
        self.btn_reset_device.setEnabled(True)
        self.btn_reset_device.setText("Reset Device Lock")

        if success:
            self.set_status(message, color="#00ff41")
            QMessageBox.information(self, "Reset Successful", message)
            self.fetch_licenses_from_github()
        else:
            self.set_status(message, color="#ff5252")
            QMessageBox.critical(self, "Reset Error", message)

    def copy_selected_key(self):
        selected_row = self.table_licenses.currentRow()
        if selected_row < 0:
            # If only 1 license exists, default to row 0 automatically
            if self.table_licenses.rowCount() == 1:
                selected_row = 0
                self.table_licenses.selectRow(0)
            else:
                QMessageBox.warning(self, "Select License", "Please click on a license row in the table first.")
                return

        key_item = self.table_licenses.item(selected_row, 6)
        if not key_item:
            return
        full_key = key_item.data(Qt.UserRole) or key_item.text()
        company_item = self.table_licenses.item(selected_row, 0)
        company = company_item.text() if company_item else "Customer"

        QApplication.clipboard().setText(full_key)
        self.set_status(f"Copied Key: {full_key}", color="#00ff41")

        # Animate button text
        orig_text = self.btn_copy_selected.text()
        self.btn_copy_selected.setText("✓ Copied!")
        QTimer.singleShot(1500, lambda: self.btn_copy_selected.setText(orig_text))

        QMessageBox.information(
            self,
            "Key Copied",
            f"✅ Activation Key copied to clipboard!\n\nKey: {full_key}\nCompany: {company}"
        )

    def _on_table_cell_double_clicked(self, row, col):
        if row < 0:
            return
        self.table_licenses.selectRow(row)
        self.copy_selected_key()

    def _show_table_context_menu(self, pos):
        item = self.table_licenses.itemAt(pos)
        if not item:
            return
        row = item.row()
        self.table_licenses.selectRow(row)

        key_item = self.table_licenses.item(row, 6)
        full_key = (key_item.data(Qt.UserRole) or key_item.text()) if key_item else ""
        company = self.table_licenses.item(row, 0).text() if self.table_licenses.item(row, 0) else ""

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1a1a24;
                color: #f0f0f5;
                border: 1px solid #38bdf8;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 24px;
                font-size: 13px;
                font-weight: 500;
            }
            QMenu::item:selected {
                background-color: #0284c7;
                color: #ffffff;
                border-radius: 4px;
            }
        """)

        act_copy_key = menu.addAction(f"📋  Copy Activation Key ({full_key[:11]}...)")
        act_copy_comp = menu.addAction(f"🏢  Copy Company ({company})")
        menu.addSeparator()
        act_renew = menu.addAction("🔄  Renew License")
        act_reset = menu.addAction("🔓  Reset Device Lock")
        act_remove = menu.addAction("❌  Remove from GitHub")

        action = menu.exec(self.table_licenses.viewport().mapToGlobal(pos))
        if action == act_copy_key:
            self.copy_selected_key()
        elif action == act_copy_comp:
            QApplication.clipboard().setText(company)
            self.set_status(f"Copied Company: {company}", color="#00ff41")
            QMessageBox.information(self, "Copied", f"Company name copied:\n\n{company}")
        elif action == act_renew:
            self.renew_selected_license()
        elif action == act_reset:
            self.reset_selected_device_lock()
        elif action == act_remove:
            self.remove_selected_license()

    def renew_selected_license(self):
        selected_row = self.table_licenses.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Select License", "Please select a license from the table to renew.")
            return

        company = self.table_licenses.item(selected_row, 0).text()
        expiry_str = self.table_licenses.item(selected_row, 3).text()
        hwid_str = self.table_licenses.item(selected_row, 4).text()
        note_str = self.table_licenses.item(selected_row, 5).text()
        key_item = self.table_licenses.item(selected_row, 6)
        full_key = key_item.data(Qt.UserRole) or key_item.text()

        lic_data = {
            "company": company,
            "key": full_key,
            "expiry": expiry_str,
            "hwids": hwid_str,
            "note": note_str
        }

        dlg = LicenseRenewalDialog(self, lic_data, self.cfg)
        if dlg.exec():
            self.fetch_licenses_from_github()

    # -----------------------------------------------------------------------
    # Connection Check & Live Indicator
    # -----------------------------------------------------------------------
    def check_connection(self):
        if self.status_worker and self.status_worker.isRunning():
            return

        self.cfg = load_config()
        token = self.cfg.get("github_token", "").strip()
        repo = self.cfg.get("repo", "").strip()

        if not token:
            self.set_indicator("DISCONNECTED", "● DISCONNECTED: No GitHub Token configured (Open Settings)")
            return

        self.set_indicator("CHECKING", "● Checking GitHub Connection...")
        self.btn_refresh_conn.setEnabled(False)

        self.status_worker = GitHubSyncWorker("test", self.cfg)
        self.status_worker.finished.connect(self.on_connection_checked)
        self.status_worker.start()

    def on_connection_checked(self, success, message, details):
        self.btn_refresh_conn.setEnabled(True)
        repo = self.cfg.get("repo", "rscomputer204-netizen/license_keys.txt")
        self.is_github_connected = success
        self.update_github_action_button()
        if success:
            self.set_indicator("CONNECTED", f"● CONNECTED: {repo} (Write Access OK)")
            self.set_status("GitHub connection verified successfully.", color="#00ff41")
        else:
            self.set_indicator("DISCONNECTED", f"● DISCONNECTED: {message}")
            self.set_status(f"GitHub Error: {message}", color="#ff5252")

    def update_github_action_button(self):
        if hasattr(self, 'btn_github_action'):
            if self.is_github_connected:
                self.btn_github_action.setText("Push to GitHub")
                self.btn_github_action.setStyleSheet("background-color: #238636; color: #ffffff; font-weight: bold; border: none; padding: 10px; border-radius: 4px; font-size: 13px;")
            else:
                self.btn_github_action.setText("Copy GitHub Line")
                self.btn_github_action.setStyleSheet("background-color: #2d2d3a; color: #ffffff; font-weight: bold; padding: 10px; border: 1px solid #3d3d4e; border-radius: 4px; font-size: 13px;")

    def set_indicator(self, state, text):
        if state == "CONNECTED":
            self.badge_indicator.setStyleSheet("""
                background-color: #12301c; 
                color: #00ff41; 
                font-weight: bold; 
                font-size: 11px; 
                padding: 5px 12px; 
                border-radius: 12px; 
                border: 1px solid #1e6633;
            """)
        elif state == "CHECKING":
            self.badge_indicator.setStyleSheet("""
                background-color: #332b12; 
                color: #ffd600; 
                font-weight: bold; 
                font-size: 11px; 
                padding: 5px 12px; 
                border-radius: 12px; 
                border: 1px solid #66521a;
            """)
        else:  # DISCONNECTED
            self.badge_indicator.setStyleSheet("""
                background-color: #331518; 
                color: #ff5252; 
                font-weight: bold; 
                font-size: 11px; 
                padding: 5px 12px; 
                border-radius: 12px; 
                border: 1px solid #662028;
            """)
        self.badge_indicator.setText(text)

    # -----------------------------------------------------------------------
    # Preset Handlers
    # -----------------------------------------------------------------------
    def set_duration_months(self, months):
        self.date_edit.setDate(QDate.currentDate().addMonths(months))
        self.set_status(f"Expiry set to {months} month(s) from today.")

    def set_duration_years(self, years):
        self.date_edit.setDate(QDate.currentDate().addYears(years))
        self.set_status(f"Expiry set to {years} year(s) from today.")

    def on_autopush_changed(self, state):
        self.cfg["auto_push"] = (state == Qt.Checked.value if hasattr(Qt, 'Checked') else bool(state))
        save_config(self.cfg)

    def set_status(self, text, color="#00ff41"):
        self.lbl_main_status.setText(text)
        self.lbl_main_status.setStyleSheet(f"""
            background-color: #1e1e24; 
            border: 1px solid #2d2d38; 
            border-radius: 4px; 
            padding: 6px 10px; 
            font-size: 12px; 
            color: {color};
        """)

    # -----------------------------------------------------------------------
    # Key Generation Logic
    # -----------------------------------------------------------------------
    def generate_key(self):
        company = self.txt_company.text().strip()
        if not company:
            QMessageBox.warning(self, "Validation Error", "Company / User Name is required!")
            return False

        # Determine Device Limit (Auto-locks on customer activation)
        if self.radio_1_device.isChecked():
            max_devices = 1
            hwid_record_str = "UNBOUND"
            dev_desc = "1 Device (Auto-locks on activation)"
        elif self.radio_2_devices.isChecked():
            max_devices = 2
            hwid_record_str = "UNBOUND"
            dev_desc = "2 Devices (Allows 2 PCs)"
        else:
            max_devices = 999
            hwid_record_str = "ANY"
            dev_desc = "Unlimited (Any PC)"

        dt = self.date_edit.date()
        tm = self.time_edit.time()

        # Local time to UTC timestamp
        expiry_dt = datetime(dt.year(), dt.month(), dt.day(), tm.hour(), tm.minute(), tm.second())
        expiry_ts = expiry_dt.replace(tzinfo=datetime.now().astimezone().tzinfo).astimezone(timezone.utc).timestamp()
        issued_ts = datetime.now(timezone.utc).timestamp()

        payload = {
            "company": company,
            "expiry_ts": expiry_ts,
            "issued_ts": issued_ts,
            "uuid": str(uuid.uuid4())
        }

        secret_key = encrypt_payload(payload)

        expiry_str = expiry_dt.strftime("%Y-%m-%d %H:%M:%S")
        issued_str = datetime.now().strftime("%Y-%m-%d")
        note = self.txt_note.text().strip() or "No_Note"
        note = note.replace("|", "_").replace(" ", "_")
        company_clean = company.replace("|", "_").replace(" ", "_")

        self.generated_secret_key = secret_key
        self.generated_github_line = f"{secret_key}|{issued_str}|{expiry_str}|{company_clean}|{note}|{max_devices}|{hwid_record_str}"

        self.txt_key_output.setText(self.generated_secret_key)
        self.txt_github_output.setText(self.generated_github_line)
        self.set_status(f"License Key generated! [{dev_desc}]", color="#00ff41")
        return True

    def handle_github_action(self):
        if self.is_github_connected:
            self.push_to_github()
        else:
            self.copy_github_only()

    # -----------------------------------------------------------------------
    # Clipboard Helpers
    # -----------------------------------------------------------------------
    def copy_key_only(self):
        if self.generated_secret_key:
            QApplication.clipboard().setText(self.generated_secret_key)
            self.set_status("Software License Key copied to clipboard!", color="#00ff41")
            QMessageBox.information(
                self,
                "Key Copied",
                f"✅ Activation Key copied to clipboard!\n\n{self.generated_secret_key}"
            )
        else:
            QMessageBox.warning(self, "Notice", "Please generate a key first.")

    def copy_github_only(self):
        if self.generated_github_line:
            QApplication.clipboard().setText(self.generated_github_line)
            self.set_status("GitHub Line Format copied to clipboard!", color="#00ff41")
            QMessageBox.information(
                self,
                "Line Copied",
                f"✅ GitHub Line Format copied to clipboard!\n\n{self.generated_github_line}"
            )
        else:
            QMessageBox.warning(self, "Notice", "Please generate a key first.")

    # -----------------------------------------------------------------------
    # GitHub Synchronization
    # -----------------------------------------------------------------------
    def push_to_github(self):
        if not self.generated_github_line:
            QMessageBox.warning(self, "Notice", "Please generate a license key first.")
            return

        self.cfg = load_config()
        token = self.cfg.get("github_token", "").strip()
        if not token:
            reply = QMessageBox.question(
                self,
                "GitHub Token Required",
                "No GitHub Personal Access Token is configured.\n\nWould you like to open Settings to configure it now?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.open_settings()
            return

        self.btn_github_action.setEnabled(False)
        self.btn_github_action.setText("Pushing to GitHub...")
        self.set_status("Syncing with GitHub repository...", color="#ffd600")

        company = self.txt_company.text().strip()
        payload = {
            "github_line": self.generated_github_line,
            "company": company,
            "secret_key": self.generated_secret_key
        }

        self.sync_worker = GitHubSyncWorker("push", self.cfg, payload)
        self.sync_worker.finished.connect(self.on_push_finished)
        self.sync_worker.start()

    def on_push_finished(self, success, message, details):
        self.btn_github_action.setEnabled(True)
        self.update_github_action_button()

        if success:
            self.set_status(message, color="#00ff41")
            self.set_indicator("CONNECTED", f"● CONNECTED: {self.cfg.get('repo')} (Last Push OK)")
            QMessageBox.information(self, "GitHub Sync", message)
            if self.tabs.currentIndex() == 1 or self.all_licenses:
                self.fetch_licenses_from_github()
        else:
            self.set_status(message, color="#ff5252")
            self.set_indicator("DISCONNECTED", f"● DISCONNECTED: {message}")
            QMessageBox.critical(self, "GitHub Sync Error", message)

    def open_settings(self):
        dlg = GitHubSettingsDialog(self)
        if dlg.exec():
            self.cfg = load_config()
            self.check_connection()


# ---------------------------------------------------------------------------
# Application Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = KeyGenerator()
    window.show()
    sys.exit(app.exec())
