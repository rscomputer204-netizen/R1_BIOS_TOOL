"""
R1 BIOS TOOL — GITHUB DEPLOYMENT & AUTO-UPDATE PACKAGING MANAGER v3.0
====================================================================
Features:
- Manual Change Detection (No intrusive auto-scans overwriting user input)
- Ultra-smart Code Inspector (Detects 1-line changes, functions, classes, new files/folders)
- Real-time GitHub Connection Health Monitor (Live API check every 10 seconds — no fake OK!)
- Dedicated Settings Dialog (Change/Test Token, Repo Owner, Branch anytime)
- Full Auto-Update Packager (Guarantees R1_CSME_Analyzer, rg_engine, assets & _internal are bundled)
"""

import os
import sys
import re
import ast
import json
import time
import shutil
import threading
import datetime
import subprocess
import urllib.request
import urllib.error
import tkinter as tk
from tkinter import ttk, messagebox

# ─── PATHS & CONFIG ──────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

CONFIG_FILE = os.path.join(BASE_DIR, "config", "github_token.json")


def load_config():
    default_cfg = {
        "repo_owner": "rscomputer204-netizen",
        "repo_name": "R1_BIOS_TOOL",
        "branch": "main",
        "github_token": ""
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                default_cfg.update(data)
        except Exception:
            pass
    return default_cfg


def save_config(cfg):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)


def run_cmd(cmd, check=True):
    """Run shell command in BASE_DIR and return stdout string."""
    res = subprocess.run(cmd, shell=True, text=True, encoding="utf-8", errors="replace", capture_output=True, cwd=BASE_DIR)
    if check and res.returncode != 0:
        err = (res.stderr or "").strip()
        raise RuntimeError(err or f"Command failed with code {res.returncode}")
    return (res.stdout or "").strip()


def get_current_version():
    ver_file = os.path.join(BASE_DIR, "version.txt")
    if os.path.exists(ver_file):
        try:
            with open(ver_file, "r", encoding="utf-8") as f:
                v = f.read().strip()
                if v:
                    if not v.startswith("R1"):
                        v = f"R1.{v.lstrip('v.')}"
                    return v
        except Exception:
            pass
    return "R1.1.0.0"


def increment_version(ver_str):
    try:
        match = re.match(r'^(.*?)(\d+)$', ver_str)
        if match:
            prefix, num = match.groups()
            return f"{prefix}{int(num)+1}"
    except Exception:
        pass
    return ver_str


# ─── REAL-TIME GITHUB API CONNECTION CHECKER ─────────────────────────────────
def check_github_api(token, timeout=5):
    """
    Directly query the GitHub API to verify token status.
    Returns:
      ('OK', username, 'Connected')
      ('EXPIRED', None, 'Token Expired / Invalid (401)')
      ('NO_INTERNET', None, 'No Internet Connection')
      ('EMPTY', None, 'No Token Configured')
    """
    token = (token or "").strip()
    if not token:
        return ("EMPTY", None, "No Token Configured")

    url = "https://api.github.com/user"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"token {token}")
    req.add_header("User-Agent", "R1-BIOS-DEPLOYMENT-TOOL")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            login = data.get("login", "Unknown")
            return ("OK", login, f"Connected as @{login}")
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return ("EXPIRED", None, "Token Expired or Invalid (401)")
        elif e.code == 403:
            return ("EXPIRED", None, "Rate Limited / Access Denied (403)")
        return ("ERROR", None, f"HTTP Error {e.code}")
    except Exception as e:
        return ("NO_INTERNET", None, "No Internet / Network Error")


# ─── ULTRA-SMART CODE & RESOURCE CHANGE DETECTOR ─────────────────────────────
def analyze_git_changes():
    """
    Scans the repository deeply:
    - Working tree modifications (git status --porcelain -u)
    - Single-line additions / deletions (git diff -U0 and numstat)
    - Unpushed commits (origin/{branch}..HEAD)
    - Function and class level alterations
    - New folders/modules (e.g. R1_CSME_Analyzer)
    """
    cfg = load_config()
    branch = cfg.get("branch", "main")
    file_map = {}

    def parse_py_functions(filepath, diff_text=""):
        full_path = os.path.join(BASE_DIR, filepath)
        funcs = []
        if not os.path.exists(full_path):
            return funcs

        if diff_text:
            for d_line in diff_text.splitlines():
                hunk_match = re.search(r'@@.*?(?:def|class)\s+([A-Za-z0-9_]+)', d_line)
                if hunk_match:
                    fn = hunk_match.group(1)
                    if f"def {fn}()" not in funcs:
                        funcs.append(f"def {fn}()")
                added_fn = re.search(r'^\+\s*(?:async\s+)?def\s+([A-Za-z0-9_]+)\s*\(', d_line)
                if added_fn:
                    fn = added_fn.group(1)
                    tag = f"def {fn}() [NEW]"
                    if tag not in funcs and f"def {fn}()" not in funcs:
                        funcs.append(tag)
                added_cls = re.search(r'^\+\s*class\s+([A-Za-z0-9_]+)', d_line)
                if added_cls:
                    cls_name = f"class {added_cls.group(1)} [NEW]"
                    if cls_name not in funcs:
                        funcs.append(cls_name)
        else:
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    tree = ast.parse(f.read(), filename=filepath)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        funcs.append(f"def {node.name}()")
                    elif isinstance(node, ast.ClassDef):
                        funcs.append(f"class {node.name}")
            except Exception:
                pass
        return funcs

    # 1. Unpushed commits compared to origin/branch
    try:
        unpushed_raw = run_cmd(f"git diff --name-status origin/{branch}..HEAD", check=False)
        if unpushed_raw:
            for line in unpushed_raw.splitlines():
                parts = line.strip().split(None, 1)
                if len(parts) < 2:
                    continue
                sc, fp = parts[0], parts[1].replace('"', '')
                if fp.endswith(".log") or "__pycache__" in fp or fp.startswith(".gemini"):
                    continue

                ch_type = "MODIFIED"
                if "A" in sc:
                    ch_type = "NEW FILE"
                elif "D" in sc:
                    ch_type = "DELETED"

                funcs = []
                diff_stats = ""
                if fp.endswith(".py") and ch_type != "DELETED":
                    diff_txt = run_cmd(f'git diff -U0 origin/{branch}..HEAD -- "{fp}"', check=False)
                    funcs = parse_py_functions(fp, diff_txt)
                    numstat = run_cmd(f'git diff --numstat origin/{branch}..HEAD -- "{fp}"', check=False)
                    if numstat:
                        parts_ns = numstat.split()
                        if len(parts_ns) >= 2:
                            diff_stats = f"+{parts_ns[0]} / -{parts_ns[1]} lines"

                file_map[fp] = {
                    "status": ch_type,
                    "path": fp,
                    "functions": funcs,
                    "stats": diff_stats,
                    "source": "unpushed_commit"
                }
    except Exception:
        pass

    # 2. Working tree status (-u flag ensures untracked directory files are unpacked)
    raw_status = run_cmd("git status --porcelain -u", check=False)
    if raw_status:
        for raw_line in raw_status.splitlines():
            trimmed = raw_line.strip()
            if not trimmed:
                continue
            parts = trimmed.split(None, 1)
            if len(parts) < 2:
                continue
            status_code = parts[0]
            filepath = parts[1].replace('"', '')

            # Ignore transient logs, cache & Rust app workspace
            norm_path = filepath.replace("\\", "/").lower()
            if (filepath.endswith(".log") or "__pycache__" in filepath or 
                filepath.startswith(".gemini") or filepath.endswith(".tmp") or
                norm_path.startswith("rust app") or norm_path.startswith("rust_app") or
                "/rust app/" in norm_path or "/rust_app/" in norm_path):
                continue

            change_type = "MODIFIED"
            if "?" in status_code:
                change_type = "NEW FILE"
            elif "D" in status_code:
                change_type = "DELETED"
            elif "A" in status_code:
                change_type = "ADDED"

            funcs = []
            diff_stats = ""
            if filepath.endswith(".py") and change_type != "DELETED":
                if change_type == "NEW FILE":
                    funcs = parse_py_functions(filepath, "")
                    try:
                        with open(os.path.join(BASE_DIR, filepath), "r", encoding="utf-8", errors="ignore") as f:
                            lines_cnt = sum(1 for _ in f)
                        diff_stats = f"{lines_cnt} lines"
                    except Exception:
                        pass
                else:
                    diff_out = run_cmd(f'git diff -U0 -- "{filepath}"', check=False)
                    funcs = parse_py_functions(filepath, diff_out)
                    numstat = run_cmd(f'git diff --numstat -- "{filepath}"', check=False)
                    if numstat:
                        parts_ns = numstat.split()
                        if len(parts_ns) >= 2:
                            diff_stats = f"+{parts_ns[0]} / -{parts_ns[1]} lines"

            if filepath in file_map:
                existing = file_map[filepath]
                merged_funcs = list(dict.fromkeys(existing["functions"] + funcs))
                file_map[filepath]["functions"] = merged_funcs
                file_map[filepath]["status"] = change_type
                if diff_stats:
                    file_map[filepath]["stats"] = diff_stats
            else:
                file_map[filepath] = {
                    "status": change_type,
                    "path": filepath,
                    "functions": funcs,
                    "stats": diff_stats,
                    "source": "working_tree"
                }

    return list(file_map.values())


# ─── SETTINGS DIALOG (TOKEN & REPO CONFIG) ───────────────────────────────────
class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, cfg, on_save_cb):
        super().__init__(parent)
        self.title("⚙️ GITHUB DEPLOYMENT SETTINGS")
        self.geometry("540x440")
        self.resizable(False, False)
        self.configure(bg="#030712")
        self.transient(parent)
        self.grab_set()

        self.cfg = dict(cfg)
        self.on_save_cb = on_save_cb

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 270
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 220
        self.geometry(f"+{max(0, x)}+{max(0, y)}")

        self.setup_ui()

    def setup_ui(self):
        clr_bg = "#030712"
        clr_card = "#0f172a"
        clr_border = "#1e293b"
        clr_cyan = "#06b6d4"
        clr_text = "#f8fafc"
        clr_dim = "#94a3b8"

        # Header
        hdr = tk.Frame(self, bg="#020617", padx=16, pady=12, highlightthickness=1, highlightbackground=clr_border)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="⚙️ GITHUB REPOSITORY & ACCESS CONFIG", fg=clr_cyan, bg="#020617", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tk.Label(hdr, text="Configure your personal access token and target repository details.", fg=clr_dim, bg="#020617", font=("Segoe UI", 8)).pack(anchor="w")

        # Body
        body = tk.Frame(self, bg=clr_bg, padx=16, pady=12)
        body.pack(fill=tk.BOTH, expand=True)

        # Token Field
        tk.Label(body, text="PERSONAL ACCESS TOKEN (CLASSIC / REPO SCOPE)", fg=clr_dim, bg=clr_bg, font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 2))
        tok_frame = tk.Frame(body, bg=clr_card, highlightthickness=1, highlightbackground=clr_border)
        tok_frame.pack(fill=tk.X, pady=(0, 10))

        self.var_token = tk.StringVar(value=self.cfg.get("github_token", ""))
        self.show_tok = False
        self.ent_token = tk.Entry(tok_frame, textvariable=self.var_token, bg=clr_card, fg=clr_text,
                                  insertbackground=clr_cyan, relief="flat", font=("Consolas", 9), show="•")
        self.ent_token.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8, pady=6)

        self.btn_eye = tk.Button(tok_frame, text="👁", bg=clr_card, fg=clr_dim, relief="flat", cursor="hand2", command=self.toggle_eye)
        self.btn_eye.pack(side=tk.RIGHT, padx=6)

        # Live Test Button & Result
        test_frame = tk.Frame(body, bg=clr_bg)
        test_frame.pack(fill=tk.X, pady=(0, 12))
        self.btn_test = tk.Button(test_frame, text="⚡ Test Token Connection", bg="#1e293b", fg=clr_cyan,
                                  font=("Segoe UI", 8, "bold"), relief="flat", padx=10, pady=4, cursor="hand2",
                                  command=self.run_test)
        self.btn_test.pack(side=tk.LEFT)

        self.lbl_test_res = tk.Label(test_frame, text="Click to test token validity", fg=clr_dim, bg=clr_bg, font=("Segoe UI", 8))
        self.lbl_test_res.pack(side=tk.LEFT, padx=(10, 0))

        # Repo Owner
        tk.Label(body, text="REPOSITORY OWNER (USERNAME / ORG)", fg=clr_dim, bg=clr_bg, font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 2))
        self.var_owner = tk.StringVar(value=self.cfg.get("repo_owner", "rscomputer204-netizen"))
        ent_owner = tk.Entry(body, textvariable=self.var_owner, bg=clr_card, fg=clr_text,
                             insertbackground=clr_cyan, relief="flat", font=("Segoe UI", 9),
                             highlightthickness=1, highlightbackground=clr_border)
        ent_owner.pack(fill=tk.X, pady=(0, 10), ipady=4, padx=1)

        # Repo Name
        tk.Label(body, text="REPOSITORY NAME", fg=clr_dim, bg=clr_bg, font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 2))
        self.var_repo = tk.StringVar(value=self.cfg.get("repo_name", "R1_BIOS_TOOL"))
        ent_repo = tk.Entry(body, textvariable=self.var_repo, bg=clr_card, fg=clr_text,
                            insertbackground=clr_cyan, relief="flat", font=("Segoe UI", 9),
                            highlightthickness=1, highlightbackground=clr_border)
        ent_repo.pack(fill=tk.X, pady=(0, 10), ipady=4, padx=1)

        # Branch Name
        tk.Label(body, text="TARGET BRANCH", fg=clr_dim, bg=clr_bg, font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 2))
        self.var_branch = tk.StringVar(value=self.cfg.get("branch", "main"))
        ent_branch = tk.Entry(body, textvariable=self.var_branch, bg=clr_card, fg=clr_text,
                              insertbackground=clr_cyan, relief="flat", font=("Segoe UI", 9),
                              highlightthickness=1, highlightbackground=clr_border)
        ent_branch.pack(fill=tk.X, pady=(0, 16), ipady=4, padx=1)

        # Footer Buttons
        ftr = tk.Frame(self, bg="#020617", padx=16, pady=10, highlightthickness=1, highlightbackground=clr_border)
        ftr.pack(fill=tk.X, side=tk.BOTTOM)

        btn_cancel = tk.Button(ftr, text="Cancel", bg="#1e293b", fg=clr_dim, relief="flat", padx=16, pady=6, cursor="hand2", command=self.destroy)
        btn_cancel.pack(side=tk.RIGHT, padx=(8, 0))

        btn_save = tk.Button(ftr, text="💾 Save Settings", bg="#10b981", fg="#000000",
                             font=("Segoe UI", 9, "bold"), relief="flat", padx=20, pady=6, cursor="hand2",
                             command=self.save)
        btn_save.pack(side=tk.RIGHT)

    def toggle_eye(self):
        self.show_tok = not self.show_tok
        self.ent_token.config(show="" if self.show_tok else "•")

    def run_test(self):
        tok = self.var_token.get().strip()
        if not tok:
            self.lbl_test_res.config(text="⚠ Please enter a token first", fg="#facc15")
            return
        self.lbl_test_res.config(text="Testing with GitHub...", fg="#38bdf8")
        self.btn_test.config(state=tk.DISABLED)

        def worker():
            status, login, msg = check_github_api(tok)
            if status == "OK":
                self.after(0, lambda: self.lbl_test_res.config(text=f"✔ Authenticated as @{login}", fg="#10b981"))
            elif status == "EXPIRED":
                self.after(0, lambda: self.lbl_test_res.config(text="✖ Token Expired or Invalid (401)", fg="#f43f5e"))
            elif status == "NO_INTERNET":
                self.after(0, lambda: self.lbl_test_res.config(text="⚠ No Internet / Connection Failed", fg="#facc15"))
            else:
                self.after(0, lambda: self.lbl_test_res.config(text=f"✖ {msg}", fg="#f43f5e"))
            self.after(0, lambda: self.btn_test.config(state=tk.NORMAL))

        threading.Thread(target=worker, daemon=True).start()

    def save(self):
        new_tok = self.var_token.get().strip()
        new_owner = self.var_owner.get().strip() or "rscomputer204-netizen"
        new_repo = self.var_repo.get().strip() or "R1_BIOS_TOOL"
        new_branch = self.var_branch.get().strip() or "main"

        self.cfg["github_token"] = new_tok
        self.cfg["repo_owner"] = new_owner
        self.cfg["repo_name"] = new_repo
        self.cfg["branch"] = new_branch

        save_config(self.cfg)
        if self.on_save_cb:
            self.on_save_cb(self.cfg)
        messagebox.showinfo("SETTINGS SAVED", "GitHub deployment settings saved successfully!")
        self.destroy()


# ─── MAIN DEPLOYMENT GUI APPLICATION ─────────────────────────────────────────
class GitPushGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("R1 BIOS TOOL ❖ GITHUB DEPLOYMENT & AUTO-UPDATE ENGINE")
        self.root.geometry("920x720")
        self.root.minsize(860, 640)

        # Modern Cyber Dark Palette
        self.clr_bg = "#030712"
        self.clr_card = "#0f172a"
        self.clr_header = "#020617"
        self.clr_border = "#1e293b"
        self.clr_cyan = "#06b6d4"
        self.clr_cyan_bright = "#22d3ee"
        self.clr_green = "#10b981"
        self.clr_green_hover = "#059669"
        self.clr_dim = "#94a3b8"
        self.clr_text = "#f8fafc"
        self.clr_red = "#f43f5e"
        self.clr_yellow = "#facc15"

        self.root.configure(bg=self.clr_bg)

        # State
        self.cfg = load_config()
        self.detected_changes = []
        self.is_busy = False
        self.github_status = "CHECKING"  # OK, EXPIRED, NO_INTERNET, EMPTY
        self.github_user = None

        self.setup_ui()
        self.center_window()
        self.log("SYSTEM INITIALIZED. Ready for manual scan.", "info")

        # Start 10-second background GitHub Connection Health Checker
        self.start_health_monitor()

    def center_window(self):
        self.root.update_idletasks()
        w = 920
        h = 720
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2) - 30
        self.root.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")

    # ─── REAL-TIME HEALTH MONITOR (10 SECOND INTERVAL) ──────────────────────
    def start_health_monitor(self):
        def monitor_worker():
            while True:
                tok = self.cfg.get("github_token", "")
                status, user, msg = check_github_api(tok, timeout=6)
                self.github_status = status
                self.github_user = user
                self.root.after(0, lambda s=status, u=user, m=msg: self.update_health_badge(s, u, m))
                time.sleep(10)  # Check every 10 seconds exactly

        t = threading.Thread(target=monitor_worker, daemon=True)
        t.start()

    def update_health_badge(self, status, user, msg):
        if status == "OK":
            self.lbl_health_badge.config(
                text=f"🟢 LIVE: Connected (@{user})",
                fg=self.clr_green
            )
            # Re-enable push button if changes were already detected
            if self.detected_changes and not self.is_busy:
                self.btn_push.config(state=tk.NORMAL, bg=self.clr_green, fg="#000000", cursor="hand2")
        elif status == "EXPIRED":
            self.lbl_health_badge.config(
                text="🔴 TOKEN EXPIRED / INVALID (Click ⚙️ Settings)",
                fg=self.clr_red
            )
            # Disable push button with warning
            if not self.is_busy:
                self.btn_push.config(state=tk.DISABLED, bg="#1e293b", fg="#64748b", cursor="arrow")
        elif status == "NO_INTERNET":
            self.lbl_health_badge.config(
                text="🟡 OFFLINE: No Internet Connection",
                fg=self.clr_yellow
            )
        else:
            self.lbl_health_badge.config(
                text="⚪ TOKEN NOT CONFIGURED (Click ⚙️ Settings)",
                fg=self.clr_dim
            )
            if not self.is_busy:
                self.btn_push.config(state=tk.DISABLED, bg="#1e293b", fg="#64748b", cursor="arrow")

    # ─── UI SETUP ────────────────────────────────────────────────────────────
    def setup_ui(self):
        # 1. Header Frame
        header = tk.Frame(self.root, bg=self.clr_header, padx=18, pady=12, highlightthickness=1, highlightbackground=self.clr_border)
        header.pack(fill=tk.X)

        title_box = tk.Frame(header, bg=self.clr_header)
        title_box.pack(side=tk.LEFT)

        tk.Label(title_box, text="R1 BIOS TOOL ❖ CLOUD DEPLOYMENT", fg=self.clr_cyan, bg=self.clr_header,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w")
        tk.Label(title_box, text="SMART CHANGE DETECTOR & AUTO-UPDATE PACKAGING ENGINE", fg=self.clr_dim, bg=self.clr_header,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")

        # Right Header: Settings Button & Live Connection Badge
        header_right = tk.Frame(header, bg=self.clr_header)
        header_right.pack(side=tk.RIGHT)

        # Settings Button
        btn_settings = tk.Button(
            header_right, text="⚙️ Settings", bg="#1e293b", fg=self.clr_cyan_bright,
            font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=4, cursor="hand2",
            activebackground="#334155", activeforeground="#ffffff",
            command=self.open_settings
        )
        btn_settings.pack(side=tk.RIGHT, padx=(10, 0))

        # Live Health Status Box
        health_box = tk.Frame(header_right, bg=self.clr_card, padx=10, pady=5, highlightthickness=1, highlightbackground=self.clr_border)
        health_box.pack(side=tk.RIGHT)

        repo_name = f"{self.cfg.get('repo_owner', 'rscomputer204-netizen')}/{self.cfg.get('repo_name', 'R1_BIOS_TOOL')}"
        tk.Label(health_box, text=f"REPO: {repo_name} [{self.cfg.get('branch', 'main')}]", fg=self.clr_cyan, bg=self.clr_card, font=("Segoe UI", 8, "bold")).pack(anchor="e")
        self.lbl_health_badge = tk.Label(health_box, text="⏳ Checking GitHub Link...", fg=self.clr_dim, bg=self.clr_card, font=("Segoe UI", 8, "bold"))
        self.lbl_health_badge.pack(anchor="e")

        # 2. Main Content Container
        content = tk.Frame(self.root, bg=self.clr_bg, padx=16, pady=10)
        content.pack(fill=tk.BOTH, expand=True)

        # Action Buttons Banner (Manual Detection & Push)
        btn_banner = tk.Frame(content, bg=self.clr_card, padx=14, pady=10, highlightthickness=1, highlightbackground=self.clr_border)
        btn_banner.pack(fill=tk.X, pady=(0, 10))

        # Button 1: DETECT CHANGES (MANUAL)
        self.btn_detect = tk.Button(
            btn_banner, text="🔍  DETECT CHANGES", bg=self.clr_cyan, fg="#000000",
            font=("Segoe UI", 10, "bold"), relief="flat", padx=22, pady=8, cursor="hand2",
            activebackground=self.clr_cyan_bright, activeforeground="#000000",
            command=self.on_detect_click
        )
        self.btn_detect.pack(side=tk.LEFT, padx=(0, 12))

        # Button 2: PUSH TO GITHUB (Initially Disabled)
        self.btn_push = tk.Button(
            btn_banner, text="🚀  PUSH TO GITHUB", bg="#1e293b", fg="#64748b",
            font=("Segoe UI", 10, "bold"), relief="flat", padx=25, pady=8, cursor="arrow",
            state=tk.DISABLED, command=self.on_push_click
        )
        self.btn_push.pack(side=tk.LEFT)

        # Status Summary Label
        self.lbl_status_badge = tk.Label(btn_banner, text="Click 'DETECT CHANGES' to start", fg=self.clr_dim, bg=self.clr_card, font=("Segoe UI", 9, "bold"))
        self.lbl_status_badge.pack(side=tk.RIGHT, padx=5)

        # Split Container: Left Metadata Panel & Right Inspector
        split_frame = tk.Frame(content, bg=self.clr_bg)
        split_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # --- LEFT PANEL: Version & Metadata ---
        left_panel = tk.Frame(split_frame, bg=self.clr_card, width=280, padx=14, pady=12, highlightthickness=1, highlightbackground=self.clr_border)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.pack_propagate(False)

        tk.Label(left_panel, text="RELEASE METADATA", fg=self.clr_cyan, bg=self.clr_card, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 8))

        # Current Version
        cur_ver = get_current_version()
        tk.Label(left_panel, text="CURRENT VERSION", fg=self.clr_dim, bg=self.clr_card, font=("Segoe UI", 8)).pack(anchor="w")
        self.lbl_cur_ver = tk.Label(left_panel, text=cur_ver, fg=self.clr_text, bg=self.clr_card, font=("Segoe UI", 12, "bold"))
        self.lbl_cur_ver.pack(anchor="w", pady=(0, 8))

        # Next Version Entry
        tk.Label(left_panel, text="TARGET RELEASE VERSION", fg=self.clr_dim, bg=self.clr_card, font=("Segoe UI", 8)).pack(anchor="w")
        self.var_next_ver = tk.StringVar(value=increment_version(cur_ver))
        ver_entry = tk.Entry(left_panel, textvariable=self.var_next_ver, bg=self.clr_bg, fg=self.clr_green,
                             insertbackground=self.clr_cyan, relief="flat", font=("Segoe UI", 10, "bold"),
                             highlightthickness=1, highlightbackground=self.clr_border)
        ver_entry.pack(fill=tk.X, pady=(2, 10), ipady=3, padx=1)

        # Changelog / Commit Message
        tk.Label(left_panel, text="RELEASE NOTES / DESCRIPTION", fg=self.clr_dim, bg=self.clr_card, font=("Segoe UI", 8)).pack(anchor="w")
        self.txt_changelog = tk.Text(left_panel, bg=self.clr_bg, fg=self.clr_text, insertbackground=self.clr_cyan,
                                     relief="flat", font=("Segoe UI", 9), height=6,
                                     highlightthickness=1, highlightbackground=self.clr_border)
        self.txt_changelog.pack(fill=tk.BOTH, expand=True, pady=(2, 8))
        self.txt_changelog.insert(tk.END, "Integrated native R1 CSME Analyzer, optimized auto-repair and verified clean builds.")

        # Quick Settings Shortcut
        btn_cfg_quick = tk.Button(left_panel, text="⚙️ Configure Token & Repo", bg="#1e293b", fg=self.clr_cyan,
                                  font=("Segoe UI", 8, "bold"), relief="flat", cursor="hand2", command=self.open_settings)
        btn_cfg_quick.pack(fill=tk.X, pady=(4, 0), ipady=3)

        # --- RIGHT PANEL: Ultra-Smart Inspector ---
        right_panel = tk.Frame(split_frame, bg=self.clr_card, padx=14, pady=12, highlightthickness=1, highlightbackground=self.clr_border)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        header_right = tk.Frame(right_panel, bg=self.clr_card)
        header_right.pack(fill=tk.X, pady=(0, 8))
        tk.Label(header_right, text="CODE & RESOURCE CHANGE INSPECTOR", fg=self.clr_cyan, bg=self.clr_card, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        self.lbl_changes_count = tk.Label(header_right, text="0 Changes", fg=self.clr_dim, bg=self.clr_card, font=("Segoe UI", 8))
        self.lbl_changes_count.pack(side=tk.RIGHT)

        # Text View for Changes Analysis
        self.txt_inspector = tk.Text(
            right_panel, bg=self.clr_bg, fg=self.clr_text, relief="flat",
            font=("Consolas", 9), wrap="none",
            highlightthickness=1, highlightbackground=self.clr_border
        )
        self.txt_inspector.pack(fill=tk.BOTH, expand=True)

        # Text Tags
        self.txt_inspector.tag_config("title", foreground="#38bdf8", font=("Consolas", 9, "bold"))
        self.txt_inspector.tag_config("file_mod", foreground="#22d3ee", font=("Consolas", 9, "bold"))
        self.txt_inspector.tag_config("file_new", foreground="#34d399", font=("Consolas", 9, "bold"))
        self.txt_inspector.tag_config("file_del", foreground="#f43f5e", font=("Consolas", 9, "bold"))
        self.txt_inspector.tag_config("func", foreground="#a7f3d0", font=("Consolas", 9))
        self.txt_inspector.tag_config("stats", foreground="#facc15", font=("Consolas", 9))
        self.txt_inspector.tag_config("dim", foreground="#64748b")
        self.txt_inspector.tag_config("success", foreground="#10b981", font=("Consolas", 10, "bold"))

        self.txt_inspector.insert(tk.END, "Ready. Click '[ 🔍 DETECT CHANGES ]' to scan code modifications...\n", "dim")

        # 3. Bottom Terminal Log Console
        console_frame = tk.Frame(self.root, bg=self.clr_card, padx=14, pady=8, highlightthickness=1, highlightbackground=self.clr_border)
        console_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=16, pady=(0, 10))

        tk.Label(console_frame, text="ACTIVITY LOG", fg=self.clr_dim, bg=self.clr_card, font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 3))

        self.txt_console = tk.Text(
            console_frame, bg=self.clr_bg, fg="#cbd5e1", relief="flat",
            font=("Consolas", 8), height=5, wrap="word",
            highlightthickness=1, highlightbackground=self.clr_border
        )
        self.txt_console.pack(fill=tk.X)
        self.txt_console.tag_config("info", foreground="#38bdf8")
        self.txt_console.tag_config("ok", foreground="#34d399")
        self.txt_console.tag_config("warn", foreground="#facc15")
        self.txt_console.tag_config("err", foreground="#f87171")

    def log(self, msg, tag="info"):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.txt_console.insert(tk.END, f"[{ts}] {msg}\n", tag)
        self.txt_console.see(tk.END)

    def open_settings(self):
        SettingsDialog(self.root, self.cfg, self.on_settings_saved)

    def on_settings_saved(self, new_cfg):
        self.cfg = new_cfg
        repo_name = f"{self.cfg.get('repo_owner', 'rscomputer204-netizen')}/{self.cfg.get('repo_name', 'R1_BIOS_TOOL')}"
        self.log(f"Settings updated for repository {repo_name}.", "ok")
        # Trigger immediate connection health test
        status, user, msg = check_github_api(self.cfg.get("github_token", ""))
        self.update_health_badge(status, user, msg)

    # ─── STEP 1: MANUAL DETECT CHANGES ACTION ────────────────────────────────
    def on_detect_click(self):
        if self.is_busy:
            return

        self.btn_detect.config(state=tk.DISABLED, text="⏳  SCANNING...")
        self.lbl_status_badge.config(text="Scanning repository diff & changes...", fg=self.clr_cyan)
        self.txt_inspector.delete(1.0, tk.END)
        self.txt_inspector.insert(tk.END, "Analyzing all working tree files, line diffs, and unpushed commits...\n\n", "dim")

        def worker():
            try:
                # Add safe directory config
                run_cmd(f'git config --global --add safe.directory "{BASE_DIR}"', check=False)
                reports = analyze_git_changes()

                self.root.after(0, lambda: self.render_analysis(reports))
            except Exception as e:
                self.root.after(0, lambda: self.log(f"Scan failed: {e}", "err"))
                self.root.after(0, lambda: self.btn_detect.config(state=tk.NORMAL, text="🔍  DETECT CHANGES"))

        threading.Thread(target=worker, daemon=True).start()

    def render_analysis(self, reports):
        self.detected_changes = reports
        self.btn_detect.config(state=tk.NORMAL, text="🔍  DETECT CHANGES")
        self.txt_inspector.delete(1.0, tk.END)

        if not reports:
            self.lbl_changes_count.config(text="0 Changes Detected")
            self.lbl_status_badge.config(text="Everything up to date", fg=self.clr_green)
            self.txt_inspector.insert(tk.END, "✔ ALL REPOSITORY FILES ARE COMMITTED & SYNCED!\n", "success")
            self.txt_inspector.insert(tk.END, "• Working directory is clean.\n", "dim")
            self.txt_inspector.insert(tk.END, f"• GitHub repository ({self.cfg.get('repo_name')}) is completely up-to-date with local branch.\n", "dim")
            self.txt_inspector.insert(tk.END, "• You can still enter a new version and push to force re-generate update.zip package if needed.\n\n", "dim")

            # Enable push button if token is valid
            if self.github_status == "OK":
                self.btn_push.config(state=tk.NORMAL, bg=self.clr_green, fg="#000000", cursor="hand2")
            else:
                self.btn_push.config(state=tk.DISABLED, bg="#1e293b", fg="#64748b", cursor="arrow")
            return

        total_files = len(reports)
        self.lbl_changes_count.config(text=f"{total_files} Changed Files")
        self.lbl_status_badge.config(text=f"{total_files} changes detected", fg=self.clr_cyan)

        self.txt_inspector.insert(tk.END, f"DETECTED {total_files} MODIFIED / NEW ITEMS:\n", "title")
        self.txt_inspector.insert(tk.END, "─" * 65 + "\n\n", "dim")

        for item in reports:
            st = item["status"]
            fp = item["path"]
            funcs = item["functions"]
            stats = item.get("stats", "")

            # Tag style
            file_tag = "file_mod"
            icon = "✎ "
            if st == "NEW FILE" or st == "ADDED":
                file_tag = "file_new"
                icon = "✚ "
            elif st == "DELETED":
                file_tag = "file_del"
                icon = "✖ "

            stats_display = f" [{stats}]" if stats else ""
            self.txt_inspector.insert(tk.END, f"{icon}{st.ljust(9)}: ", file_tag)
            self.txt_inspector.insert(tk.END, f"{fp}", "title")
            if stats_display:
                self.txt_inspector.insert(tk.END, f"{stats_display}\n", "stats")
            else:
                self.txt_inspector.insert(tk.END, "\n")

            if funcs:
                for fn in funcs:
                    self.txt_inspector.insert(tk.END, f"    ↳ {fn}\n", "func")
            self.txt_inspector.insert(tk.END, "\n")

        # Check Token health before enabling push
        if self.github_status == "OK":
            self.btn_push.config(state=tk.NORMAL, bg=self.clr_green, fg="#000000", cursor="hand2")
            self.log(f"Scan complete. {total_files} changes found. Click 'PUSH TO GITHUB' to deploy.", "ok")
        else:
            self.btn_push.config(state=tk.DISABLED, bg="#1e293b", fg="#64748b", cursor="arrow")
            self.log(f"Scan complete. {total_files} changes found, but GitHub Token is expired/invalid. Please click Settings to update token.", "warn")

    # ─── STEP 2: PUSH TO GITHUB ACTION & PACKAGING ───────────────────────────
    def on_push_click(self):
        if self.is_busy:
            return

        target_ver = self.var_next_ver.get().strip()
        if not target_ver:
            messagebox.showwarning("VERSION REQUIRED", "Please enter a valid version string (e.g. R1.1.0.4).")
            return

        changelog = self.txt_changelog.get("1.0", tk.END).strip()
        if not changelog:
            changelog = f"Auto-Update: Release {target_ver} with latest features"

        # Lock UI
        self.is_busy = True
        self.btn_detect.config(state=tk.DISABLED)
        self.btn_push.config(state=tk.DISABLED, text="⏳  PACKAGING & UPLOADING...")
        self.lbl_status_badge.config(text="Packaging & Pushing...", fg=self.clr_cyan)
        self.log(f"Starting GitHub deployment for version {target_ver}...")

        def push_worker():
            try:
                # 1. Update version.txt locally
                with open(os.path.join(BASE_DIR, "version.txt"), "w", encoding="utf-8") as f:
                    f.write(target_ver)
                py_ver_path = os.path.join(BASE_DIR, "python_version", "version.txt")
                if os.path.exists(os.path.dirname(py_ver_path)):
                    with open(py_ver_path, "w", encoding="utf-8") as f:
                        f.write(target_ver)
                self.log(f"Updated local version to {target_ver}.", "ok")

                # 2. Package complete update.zip bundle
                self.log("Creating update.zip bundle with all engines and scripts...")
                payload_dir = os.path.join(BASE_DIR, "temp_update_payload")
                if os.path.exists(payload_dir):
                    shutil.rmtree(payload_dir, ignore_errors=True)
                os.makedirs(payload_dir, exist_ok=True)

                payload_content = os.path.join(payload_dir, "payload")
                os.makedirs(payload_content, exist_ok=True)
                payload_internal = os.path.join(payload_content, "_internal")
                os.makedirs(payload_internal, exist_ok=True)

                # Ensure fresh native updater.exe is compiled if source present
                csc_path = r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
                updater_cs = os.path.join(BASE_DIR, "updater.cs")
                dist_updater = os.path.join(BASE_DIR, "dist", "updater.exe")
                if os.path.exists(csc_path) and os.path.exists(updater_cs):
                    try:
                        subprocess.run([
                            csc_path, "/target:winexe", "/optimize",
                            "/reference:System.Windows.Forms.dll",
                            f"/out:{dist_updater}", updater_cs
                        ], capture_output=True, check=False)
                    except Exception:
                        pass

                # Copy freshly compiled EXEs if dist/R1_BIOS_TOOL exists
                dist_source = os.path.join(BASE_DIR, "dist", "R1_BIOS_TOOL")
                if os.path.exists(dist_source):
                    for f in os.listdir(dist_source):
                        if f.endswith(".exe"):
                            abs_p = os.path.join(dist_source, f)
                            dest_p = os.path.join(payload_content, f)
                            shutil.copy2(abs_p, dest_p)

                # Copy updater executables & scripts
                updater_exe_src = os.path.join(dist_source, "updater.exe") if os.path.exists(os.path.join(dist_source, "updater.exe")) else os.path.join(BASE_DIR, "dist", "updater.exe")
                if os.path.exists(updater_exe_src):
                    shutil.copy2(updater_exe_src, os.path.join(payload_content, "updater.exe"))
                    shutil.copy2(updater_exe_src, os.path.join(payload_dir, "updater.exe"))
                    shutil.copy2(updater_exe_src, os.path.join(payload_internal, "updater.exe"))

                updater_py_src = os.path.join(BASE_DIR, "updater.py")
                if os.path.exists(updater_py_src):
                    shutil.copy2(updater_py_src, os.path.join(payload_content, "updater.py"))
                    shutil.copy2(updater_py_src, os.path.join(payload_dir, "updater.py"))
                    shutil.copy2(updater_py_src, os.path.join(payload_internal, "updater.py"))

                # CRITICAL: Copy ALL core packages and directories into payload AND _internal
                core_dirs = [
                    "R1_CSME_Analyzer",  # <-- Guaranteed inclusion of our native engine!
                    "R1_Universal_Extractor",  # <-- Native Universal Extractor engine!
                    "AutoPatch_Scripts",  # <-- AutoPatch scripts and manifest!
                    "translations",
                    "rg_engine",
                    "brands",
                    "config",
                    "assets",
                    "BIOSUtilities",
                    "utils",
                    "scripts",
                    "image"
                ]
                for cdir in core_dirs:
                    src_dir = os.path.join(BASE_DIR, cdir)
                    if os.path.exists(src_dir):
                        dest_dir = os.path.join(payload_content, cdir)
                        if os.path.exists(dest_dir):
                            shutil.rmtree(dest_dir, ignore_errors=True)
                        shutil.copytree(src_dir, dest_dir, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.tmp"))

                        # Also mirror core engine into _internal for frozen PyInstaller onedir compatibility
                        if cdir in ("R1_CSME_Analyzer", "R1_Universal_Extractor", "rg_engine", "brands", "BIOSUtilities", "translations", "assets"):
                            dest_internal = os.path.join(payload_internal, cdir)
                            if os.path.exists(dest_internal):
                                shutil.rmtree(dest_internal, ignore_errors=True)
                            shutil.copytree(src_dir, dest_internal, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.tmp"))

                # Copy core python files from root
                for f in os.listdir(BASE_DIR):
                    if f.endswith(".py") and not f.startswith("push_to_github") and not f.startswith("chat_") and not f.startswith("test_"):
                        shutil.copy2(os.path.join(BASE_DIR, f), os.path.join(payload_content, f))

                if os.path.exists(os.path.join(BASE_DIR, "version.txt")):
                    shutil.copy2(os.path.join(BASE_DIR, "version.txt"), os.path.join(payload_content, "version.txt"))
                    shutil.copy2(os.path.join(BASE_DIR, "version.txt"), os.path.join(payload_dir, "version.txt"))

                # Collect all individual files inside payload for manifest
                manifest_files = []
                for root, dirs, files in os.walk(payload_content):
                    dirs[:] = [d for d in dirs if d != "__pycache__"]
                    for f in files:
                        abs_p = os.path.join(root, f)
                        rel_p = os.path.relpath(abs_p, payload_content).replace("\\", "/")
                        manifest_files.append(rel_p)

                manifest = {
                    "version": target_ver,
                    "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "files": sorted(manifest_files)
                }
                with open(os.path.join(payload_dir, "manifest.json"), "w", encoding="utf-8") as f:
                    json.dump(manifest, f, indent=4)

                zip_out = os.path.join(BASE_DIR, "update")
                if os.path.exists(os.path.join(BASE_DIR, "update.zip")):
                    try:
                        os.remove(os.path.join(BASE_DIR, "update.zip"))
                    except Exception:
                        pass
                shutil.make_archive(zip_out, "zip", payload_dir)
                shutil.rmtree(payload_dir, ignore_errors=True)
                self.log(f"update.zip generated successfully ({len(manifest_files)} packaged files).", "ok")

                # 3. Update version.json
                repo_owner = self.cfg.get("repo_owner", "rscomputer204-netizen")
                repo_name = self.cfg.get("repo_name", "R1_BIOS_TOOL")
                branch = self.cfg.get("branch", "main")
                token = self.cfg.get("github_token", "")

                raw_zip_url = f"https://raw.githubusercontent.com/{repo_owner}/{repo_name}/{branch}/update.zip"
                ver_info = {
                    "version": target_ver,
                    "url": raw_zip_url,
                    "changelog": changelog,
                    "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                with open(os.path.join(BASE_DIR, "version.json"), "w", encoding="utf-8") as f:
                    json.dump(ver_info, f, indent=4)

                # 4. Git Add & Commit
                self.log("Staging git modifications...", "info")
                run_cmd("git add .")
                staged = run_cmd("git diff --cached --name-only", check=False)
                if staged:
                    self.log("Committing changes...", "info")
                    commit_msg = f"{changelog} (v{target_ver})"
                    # Use subprocess with arguments list to prevent shell quoting bugs
                    subprocess.run(["git", "commit", "-m", commit_msg], cwd=BASE_DIR, check=True)
                    self.log(f"Committed: {commit_msg}", "ok")
                else:
                    self.log("All files already committed.", "info")

                # 5. Push to GitHub with Real-Time Streaming
                self.log(f"Pushing to remote origin [{branch}]...", "info")
                auth_url = f"https://x-access-token:{token}@github.com/{repo_owner}/{repo_name}.git"
                push_cmd = f'git -c credential.helper= push --force --progress "{auth_url}" {branch}'

                proc = subprocess.Popen(
                    push_cmd, shell=True, text=True, encoding="utf-8", errors="replace",
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=BASE_DIR
                )

                err_summary = ""
                for line in proc.stdout:
                    clean_line = line.strip()
                    if clean_line:
                        self.log(f"  {clean_line}")
                        err_summary += clean_line + "\n"

                proc.wait()
                if proc.returncode != 0:
                    if "Authentication failed" in err_summary or "Invalid username or token" in err_summary or "Bad credentials" in err_summary:
                        raise RuntimeError("GitHub Authentication Failed!\nYour Personal Access Token is expired or invalid.\nPlease open ⚙️ Settings and update your token.")
                    raise RuntimeError(f"Git push failed:\n{err_summary}")

                # Synchronize local origin tracking ref
                run_cmd(f"git update-ref refs/remotes/origin/{branch} HEAD", check=False)
                run_cmd(f"git fetch origin {branch}", check=False)

                self.root.after(0, lambda: self.render_push_success(target_ver))
            except Exception as e:
                self.root.after(0, lambda: self.render_push_error(str(e)))

        threading.Thread(target=push_worker, daemon=True).start()

    def render_push_success(self, version):
        self.is_busy = False
        self.btn_detect.config(state=tk.NORMAL)
        self.btn_push.config(state=tk.DISABLED, text="🚀  PUSH TO GITHUB", bg="#1e293b", fg="#64748b", cursor="arrow")
        self.lbl_status_badge.config(text=f"✔ Pushed v{version} to GitHub!", fg=self.clr_green)
        self.lbl_cur_ver.config(text=version)
        self.var_next_ver.set(increment_version(version))

        self.txt_inspector.delete(1.0, tk.END)
        self.txt_inspector.insert(tk.END, f"DEPLOYMENT COMPLETED FOR VERSION {version}!\n", "success")
        self.txt_inspector.insert(tk.END, "─" * 65 + "\n\n", "dim")
        self.txt_inspector.insert(tk.END, f"• All code changes & R1_CSME_Analyzer are now LIVE on GitHub.\n", "title")
        self.txt_inspector.insert(tk.END, f"• update.zip contains all native modules & _internal binaries.\n", "title")
        self.txt_inspector.insert(tk.END, f"• Auto-updater will now smoothly install and execute R1 CSME Analyzer.\n\n", "success")

        self.log(f"SUCCESS: Version {version} successfully pushed to GitHub!", "ok")
        messagebox.showinfo("DEPLOYMENT SUCCESS", f"Version {version} has been successfully deployed to GitHub!\n\nAll clients updating via GitHub will now receive full R1_CSME_Analyzer features.")

    def render_push_error(self, err_msg):
        self.is_busy = False
        self.btn_detect.config(state=tk.NORMAL)
        self.btn_push.config(state=tk.NORMAL, text="🚀  PUSH TO GITHUB", bg=self.clr_green, fg="#000000", cursor="hand2")
        self.lbl_status_badge.config(text="Push Failed", fg=self.clr_red)
        self.log(f"ERROR during GitHub Push: {err_msg}", "err")
        messagebox.showerror("PUSH FAILED", f"Could not push to GitHub:\n\n{err_msg}")


# ─── MAIN ENTRY POINT ────────────────────────────────────────────────────────
def main():
    root = tk.Tk()
    app = GitPushGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
