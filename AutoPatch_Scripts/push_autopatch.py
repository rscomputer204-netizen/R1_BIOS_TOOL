"""
R1 AUTOPATCH ❖ SCRIPT & CLOUD REPOSITORY MANAGER
================================================
Dedicated visual deployment and patch management suite for R1_AutoPatch_Database.
Features:
- Dedicated Settings Dialog (Manage/Test Token, Repo Owner, Branch anytime)
- Live GitHub API connection health monitor
- Full-width spacious script inventory table with live search and brand dropdown filter
- Highly visible cyan insertion cursor on all text inputs and entries
- Right-click context menu on any patch to Edit Metadata, Open Code, or Delete
- Modal popup dialog for editing Title, Description, Symptom, Model, Brand, etc.
- Smart DELETE button that highlights ONLY when a row is selected
- "NEW UPDATE DETECT" scans for newly added, modified, or deleted scripts
- Unlocks "PUSH TO GITHUB" only after change detection
- Real-time streaming GitHub deployment terminal
"""

import os
import sys
import re
import ast
import json
import time
import shutil
import threading
import subprocess
import urllib.request
import urllib.error
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

# ─── PATHS & CONFIG ──────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
PATCHES_DIR = os.path.join(SCRIPT_DIR, "patches")
MANIFEST_FILE = os.path.join(SCRIPT_DIR, "manifest.json")
CONFIG_FILE = os.path.join(ROOT_DIR, "config", "github_token.json")


def load_config():
    default_cfg = {
        "repo_owner": "rscomputer204-netizen",
        "repo_name": "R1_AutoPatch_Database",
        "branch": "main",
        "github_token": ""
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("github_token"):
                    default_cfg["github_token"] = data["github_token"].strip()
                if data.get("repo_owner"):
                    default_cfg["repo_owner"] = data["repo_owner"].strip()
                if data.get("autopatch_repo_name"):
                    default_cfg["repo_name"] = data["autopatch_repo_name"].strip()
                elif data.get("repo_name") and data.get("repo_name") != "R1_BIOS_TOOL":
                    default_cfg["repo_name"] = data["repo_name"].strip()
                if data.get("autopatch_branch"):
                    default_cfg["branch"] = data["autopatch_branch"].strip()
        except Exception:
            pass
    return default_cfg


def save_config(cfg):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    existing = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            pass
    existing["github_token"] = cfg.get("github_token", "").strip()
    existing["repo_owner"] = cfg.get("repo_owner", "rscomputer204-netizen").strip()
    existing["autopatch_repo_name"] = cfg.get("repo_name", "R1_AutoPatch_Database").strip()
    existing["autopatch_branch"] = cfg.get("branch", "main").strip()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=4)


def check_github_api(token, timeout=5):
    """Directly query the GitHub API to verify token status."""
    token = (token or "").strip()
    if not token:
        return ("EMPTY", None, "No Token Configured")

    url = "https://api.github.com/user"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"token {token}")
    req.add_header("User-Agent", "R1-AUTOPATCH-MANAGER")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            login = data.get("login", "Unknown")
            return ("OK", login, f"Connected as @{login}")
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return ("EXPIRED", None, "Token Expired / Invalid (401)")
        elif e.code == 403:
            return ("EXPIRED", None, "Rate Limited / Access Denied (403)")
        return ("ERROR", None, f"HTTP Error {e.code}")
    except Exception:
        return ("NO_INTERNET", None, "No Internet / Network Error")


def scan_patches():
    """Scans all .py files in patches/ and extracts PATCH_INFO dicts."""
    manifest = []
    if not os.path.exists(PATCHES_DIR):
        os.makedirs(PATCHES_DIR, exist_ok=True)
        return manifest

    for root, _, files in os.walk(PATCHES_DIR):
        for f in files:
            if f.endswith(".py"):
                py_path = os.path.join(root, f)
                rel_path = os.path.relpath(py_path, SCRIPT_DIR).replace("\\", "/")
                try:
                    with open(py_path, "r", encoding="utf-8") as fp:
                        code = fp.read()

                    tree = ast.parse(code)
                    info = {}
                    for node in tree.body:
                        if isinstance(node, ast.Assign):
                            for target in node.targets:
                                if isinstance(target, ast.Name) and target.id == "PATCH_INFO":
                                    if isinstance(node.value, ast.Dict):
                                        keys = [k.value if isinstance(k, ast.Constant) else k.s for k in node.value.keys]
                                        values = []
                                        for v in node.value.values:
                                            if isinstance(v, ast.Constant):
                                                values.append(v.value)
                                            elif isinstance(v, ast.List):
                                                values.append([el.value for el in v.elts if isinstance(el, ast.Constant)])
                                            else:
                                                values.append(str(v))
                                        info = dict(zip(keys, values))
                                        break
                    if info:
                        info["script_file"] = rel_path
                        info.setdefault("brand", "UNIVERSAL")
                        info.setdefault("model", "Universal")
                        info.setdefault("board_code", "N/A")
                        info.setdefault("title", os.path.basename(py_path))
                        info.setdefault("category", "General")
                        info.setdefault("symptom", "N/A")
                        info.setdefault("description", "")
                        info.setdefault("version", "1.0.0")
                        info.setdefault("author", "R1 LAB")
                        info["last_modified"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(py_path)))
                        manifest.append(info)
                except Exception as e:
                    print(f"Error parsing {py_path}: {e}")

    manifest.sort(key=lambda x: (x.get("brand", ""), x.get("title", "")))
    return manifest


def update_manifest():
    data = scan_patches()
    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return data


def update_script_patch_info(py_path, new_info: dict):
    """Safely updates the PATCH_INFO assignment inside a .py script."""
    if not os.path.exists(py_path):
        return False, "Script file not found!"

    with open(py_path, "r", encoding="utf-8") as f:
        content = f.read()

    dict_lines = ["PATCH_INFO = {"]
    for k, v in new_info.items():
        if k in ("script_file", "last_modified"):
            continue
        if isinstance(v, str):
            safe_v = v.replace("\\", "\\\\").replace('"', '\\"')
            dict_lines.append(f'    "{k}": "{safe_v}",')
        elif isinstance(v, list):
            dict_lines.append(f'    "{k}": {v},')
        else:
            dict_lines.append(f'    "{k}": {repr(v)},')
    dict_lines.append("}")
    new_block = "\n".join(dict_lines)

    pattern = r"PATCH_INFO\s*=\s*\{.*?\n\}"
    if re.search(pattern, content, flags=re.DOTALL):
        new_content = re.sub(pattern, new_block, content, count=1, flags=re.DOTALL)
    else:
        new_content = new_block + "\n\n" + content

    with open(py_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    return True, "Saved successfully!"


# ─── SETTINGS DIALOG (TOKEN & REPO CONFIGURATION) ────────────────────────────
class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, cfg, on_save_cb):
        super().__init__(parent)
        self.title("AutoPatch GitHub Deployment Settings")
        self.geometry("520x460")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.cfg = dict(cfg)
        self.on_save_cb = on_save_cb

        clr_bg = "#0b1017"
        clr_card = "#111927"
        clr_border = "#1e293b"
        clr_cyan = "#00adb5"
        clr_cyan_bright = "#00f3ff"
        clr_text = "#e2e8f0"
        clr_dim = "#94a3b8"

        self.configure(bg=clr_bg)

        # Header
        hdr = tk.Frame(self, bg="#0e1520", padx=16, pady=12, highlightthickness=1, highlightbackground=clr_border)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="⚙️  GITHUB CONNECTION SETTINGS", fg=clr_cyan_bright, bg="#0e1520", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tk.Label(hdr, text="Configure your personal access token and AutoPatch target repository", fg=clr_dim, bg="#0e1520", font=("Segoe UI", 8)).pack(anchor="w")

        # Body
        body = tk.Frame(self, bg=clr_bg, padx=18, pady=14)
        body.pack(fill=tk.BOTH, expand=True)

        # Token Field
        tk.Label(body, text="PERSONAL ACCESS TOKEN (REPO SCOPE):", fg=clr_dim, bg=clr_bg, font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 2))
        tok_frame = tk.Frame(body, bg=clr_card, highlightthickness=1, highlightbackground=clr_border)
        tok_frame.pack(fill=tk.X, pady=(0, 8))

        self.var_token = tk.StringVar(value=self.cfg.get("github_token", ""))
        self.show_tok = False
        self.ent_token = tk.Entry(
            tok_frame, textvariable=self.var_token, bg=clr_card, fg=clr_text,
            insertbackground=clr_cyan_bright, insertwidth=2, relief="flat", font=("Consolas", 9), show="•"
        )
        self.ent_token.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8, pady=6)

        self.btn_eye = tk.Button(tok_frame, text="👁", bg=clr_card, fg=clr_dim, relief="flat", cursor="hand2", command=self.toggle_eye)
        self.btn_eye.pack(side=tk.RIGHT, padx=6)

        # Live Test Button & Result
        test_frame = tk.Frame(body, bg=clr_bg)
        test_frame.pack(fill=tk.X, pady=(0, 12))
        self.btn_test = tk.Button(test_frame, text="⚡ Test Token Connection", bg="#1e293b", fg=clr_cyan_bright,
                                  font=("Segoe UI", 8, "bold"), relief="flat", padx=10, pady=4, cursor="hand2",
                                  command=self.run_test)
        self.btn_test.pack(side=tk.LEFT)

        self.lbl_test_res = tk.Label(test_frame, text="Click to test token validity", fg=clr_dim, bg=clr_bg, font=("Segoe UI", 8))
        self.lbl_test_res.pack(side=tk.LEFT, padx=(10, 0))

        # Repo Owner
        tk.Label(body, text="REPOSITORY OWNER (USERNAME / ORG):", fg=clr_dim, bg=clr_bg, font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 2))
        self.var_owner = tk.StringVar(value=self.cfg.get("repo_owner", "rscomputer204-netizen"))
        ent_owner = tk.Entry(
            body, textvariable=self.var_owner, bg=clr_card, fg=clr_text,
            insertbackground=clr_cyan_bright, insertwidth=2, relief="flat", font=("Segoe UI", 9),
            highlightthickness=1, highlightbackground=clr_border
        )
        ent_owner.pack(fill=tk.X, pady=(0, 10), ipady=4, padx=1)

        # Repo Name
        tk.Label(body, text="REPOSITORY NAME:", fg=clr_dim, bg=clr_bg, font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 2))
        self.var_repo = tk.StringVar(value=self.cfg.get("repo_name", "R1_AutoPatch_Database"))
        ent_repo = tk.Entry(
            body, textvariable=self.var_repo, bg=clr_card, fg=clr_text,
            insertbackground=clr_cyan_bright, insertwidth=2, relief="flat", font=("Segoe UI", 9),
            highlightthickness=1, highlightbackground=clr_border
        )
        ent_repo.pack(fill=tk.X, pady=(0, 10), ipady=4, padx=1)

        # Branch Name
        tk.Label(body, text="TARGET BRANCH:", fg=clr_dim, bg=clr_bg, font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 2))
        self.var_branch = tk.StringVar(value=self.cfg.get("branch", "main"))
        ent_branch = tk.Entry(
            body, textvariable=self.var_branch, bg=clr_card, fg=clr_text,
            insertbackground=clr_cyan_bright, insertwidth=2, relief="flat", font=("Segoe UI", 9),
            highlightthickness=1, highlightbackground=clr_border
        )
        ent_branch.pack(fill=tk.X, pady=(0, 14), ipady=4, padx=1)

        # Footer Buttons
        ftr = tk.Frame(self, bg="#0e1520", padx=16, pady=10, highlightthickness=1, highlightbackground=clr_border)
        ftr.pack(fill=tk.X, side=tk.BOTTOM)

        btn_cancel = tk.Button(ftr, text="Cancel", bg="#1e293b", fg=clr_dim, relief="flat", padx=16, pady=6, cursor="hand2", command=self.destroy)
        btn_cancel.pack(side=tk.RIGHT, padx=(8, 0))

        btn_save = tk.Button(ftr, text="💾 Save Settings", bg=clr_cyan, fg="#0b1017",
                             font=("Segoe UI", 9, "bold"), relief="flat", padx=20, pady=6, cursor="hand2",
                             activebackground=clr_cyan_bright, command=self.save)
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
                self.after(0, lambda: self.lbl_test_res.config(text=f"✔ Authenticated as @{login}", fg="#22c55e"))
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
        new_repo = self.var_repo.get().strip() or "R1_AutoPatch_Database"
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


# ─── MAIN APPLICATION ────────────────────────────────────────────────────────
class AutoPatchManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("R1 AutoPatch ❖ Script & Cloud Repository Manager")
        self.root.geometry("1100x720")
        self.root.minsize(980, 600)

        # Colors matching Cyber Blue theme
        self.clr_bg = "#0b1017"
        self.clr_card = "#111927"
        self.clr_header = "#0e1520"
        self.clr_border = "#1e293b"
        self.clr_cyan = "#00adb5"
        self.clr_cyan_bright = "#00f3ff"
        self.clr_green = "#22c55e"
        self.clr_text = "#e2e8f0"
        self.clr_dim = "#94a3b8"

        self.root.configure(bg=self.clr_bg)
        self.cfg = load_config()
        self.patches_list = []
        self.current_selected_patch = None

        self.setup_ui()
        self.refresh_inventory()

        # Start live connection monitor in background
        self.check_connection_async()

    def setup_ui(self):
        # ── 1. Top Header ──────────────────────────────────────────────────
        header = tk.Frame(self.root, bg=self.clr_header, padx=18, pady=12, highlightthickness=1, highlightbackground=self.clr_border)
        header.pack(fill=tk.X)

        title_box = tk.Frame(header, bg=self.clr_header)
        title_box.pack(side=tk.LEFT)

        tk.Label(title_box, text="R1 AUTOPATCH ❖ SCRIPT & CLOUD MANAGER", fg=self.clr_cyan_bright, bg=self.clr_header,
                 font=("Segoe UI", 13, "bold")).pack(anchor="w")
        tk.Label(title_box, text="DYNAMIC BIOS PATCH INVENTORY, RIGHT-CLICK METADATA EDITOR & CLOUD DEPLOYER", fg=self.clr_dim, bg=self.clr_header,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")

        # Right Header: Settings Button & Live Connection Badge
        header_right = tk.Frame(header, bg=self.clr_header)
        header_right.pack(side=tk.RIGHT)

        # Settings Button
        btn_settings = tk.Button(
            header_right, text="⚙️ Settings", bg="#1e293b", fg=self.clr_cyan_bright,
            font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=5, cursor="hand2",
            activebackground="#334155", activeforeground="#ffffff",
            command=self.open_settings
        )
        btn_settings.pack(side=tk.RIGHT, padx=(10, 0))

        # Live Health Status Box
        health_box = tk.Frame(header_right, bg=self.clr_card, padx=12, pady=5, highlightthickness=1, highlightbackground=self.clr_border)
        health_box.pack(side=tk.RIGHT)

        self.lbl_repo_badge = tk.Label(
            health_box, text=f"REPO: {self.cfg['repo_owner']}/{self.cfg['repo_name']} [{self.cfg['branch']}]",
            fg=self.clr_cyan, bg=self.clr_card, font=("Segoe UI", 8, "bold")
        )
        self.lbl_repo_badge.pack(anchor="e")
        self.lbl_health = tk.Label(health_box, text="⏳ Checking GitHub Link...", fg=self.clr_dim, bg=self.clr_card, font=("Segoe UI", 8, "bold"))
        self.lbl_health.pack(anchor="e")

        # ── 2. Top Action Banner ───────────────────────────────────────────
        action_bar = tk.Frame(self.root, bg=self.clr_card, padx=14, pady=10, highlightthickness=1, highlightbackground=self.clr_border)
        action_bar.pack(fill=tk.X, padx=16, pady=(12, 10))

        # Button 1: NEW UPDATE DETECT (Primary action)
        self.btn_detect = tk.Button(
            action_bar, text="🔍  NEW UPDATE DETECT", bg=self.clr_cyan, fg="#0b1017",
            font=("Segoe UI", 10, "bold"), relief="flat", padx=20, pady=7, cursor="hand2",
            activebackground=self.clr_cyan_bright, activeforeground="#0b1017",
            command=self.on_detect_updates
        )
        self.btn_detect.pack(side=tk.LEFT, padx=(0, 10))

        # Button 2: Delete Script (DISABLED BY DEFAULT, highlights ONLY when a row is selected!)
        self.btn_del = tk.Button(
            action_bar, text="🗑 DELETE SCRIPT", bg="#1e293b", fg="#64748b",
            font=("Segoe UI", 9, "bold"), relief="flat", padx=16, pady=7, cursor="arrow",
            state=tk.DISABLED,
            command=self.delete_selected_script
        )
        self.btn_del.pack(side=tk.LEFT, padx=(0, 14))

        # Button 3: PUSH TO GITHUB (Disabled until updates detected)
        self.btn_push = tk.Button(
            action_bar, text="🚀  PUSH TO GITHUB", bg="#1e293b", fg="#64748b",
            font=("Segoe UI", 10, "bold"), relief="flat", padx=24, pady=7, cursor="arrow",
            state=tk.DISABLED,
            command=self.deploy_to_github
        )
        self.btn_push.pack(side=tk.LEFT)

        # Status Badge on right
        self.lbl_inv_status = tk.Label(
            action_bar, text="Click 'NEW UPDATE DETECT' to begin", fg=self.clr_dim, bg=self.clr_card, font=("Segoe UI", 9, "bold")
        )
        self.lbl_inv_status.pack(side=tk.RIGHT, padx=5)

        # ── 3. Full-Width Script Inventory Table ───────────────────────────
        content_frame = tk.Frame(self.root, bg=self.clr_bg)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 10))

        table_card = tk.Frame(content_frame, bg=self.clr_card, padx=14, pady=12, highlightthickness=1, highlightbackground=self.clr_border)
        table_card.pack(fill=tk.BOTH, expand=True)

        # Search Bar & Brand Filter Row
        search_row = tk.Frame(table_card, bg=self.clr_card)
        search_row.pack(fill=tk.X, pady=(0, 10))

        tk.Label(search_row, text="SEARCH CATALOG:", fg=self.clr_cyan, bg=self.clr_card, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 8))
        self.var_search = tk.StringVar()
        self.var_search.trace_add("write", lambda *args: self.filter_tree())
        
        # High visibility cyan cursor
        ent_search = tk.Entry(
            search_row, textvariable=self.var_search, bg="#080c12", fg=self.clr_cyan_bright,
            font=("Segoe UI", 10), relief="solid", bd=1,
            insertbackground=self.clr_cyan_bright, insertwidth=2
        )
        ent_search.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Brand Filter Dropdown right beside search
        tk.Label(search_row, text="FILTER BRAND:", fg=self.clr_cyan, bg=self.clr_card, font=("Segoe UI", 8, "bold")).pack(side=tk.LEFT, padx=(14, 6))
        self.var_brand_filter = tk.StringVar(value="ALL BRANDS")
        self.cmb_brand_filter = ttk.Combobox(
            search_row, textvariable=self.var_brand_filter,
            values=["ALL BRANDS", "DELL", "LENOVO", "HP", "ASUS", "ACER", "APPLE", "UNIVERSAL"],
            state="readonly", width=14, font=("Segoe UI", 9, "bold")
        )
        self.cmb_brand_filter.pack(side=tk.LEFT, padx=(0, 10))
        self.cmb_brand_filter.bind("<<ComboboxSelected>>", lambda e: self.filter_tree())

        btn_refresh = tk.Button(search_row, text="↻ Refresh", bg="#1e293b", fg=self.clr_text, font=("Segoe UI", 8, "bold"), relief="flat", padx=10, pady=3, command=self.refresh_inventory)
        btn_refresh.pack(side=tk.RIGHT, padx=(6, 0))

        tk.Label(search_row, text="💡 Tip: Right-click row to Edit", fg="#64748b", bg=self.clr_card, font=("Segoe UI", 8, "italic")).pack(side=tk.RIGHT, padx=(10, 0))

        # Spacious Treeview
        tree_style = ttk.Style()
        tree_style.theme_use("clam")
        tree_style.configure("Treeview", background="#080c12", foreground="#e2e8f0", fieldbackground="#080c12", rowheight=28, font=("Segoe UI", 9))
        tree_style.configure("Treeview.Heading", background="#1a2536", foreground="#00f3ff", font=("Segoe UI", 9, "bold"))
        # Selected row: vivid blue highlight background with black text
        tree_style.map("Treeview", background=[("selected", "#00b4ff")], foreground=[("selected", "#000000")])

        columns = ("brand", "model", "title", "category", "symptom")
        self.tree = ttk.Treeview(table_card, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("brand", text="Brand")
        self.tree.heading("model", text="Target Model / Board")
        self.tree.heading("title", text="Patch Title")
        self.tree.heading("category", text="Category")
        self.tree.heading("symptom", text="Observed Problem / Symptom")

        self.tree.column("brand", width=90, anchor="center")
        self.tree.column("model", width=220)
        self.tree.column("title", width=240)
        self.tree.column("category", width=110, anchor="center")
        self.tree.column("symptom", width=360)

        tree_scroll_y = ttk.Scrollbar(table_card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll_y.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        # Bindings
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<Double-1>", lambda e: self.open_edit_popup())
        self.tree.bind("<Button-3>", self.show_context_menu)

        # ── 4. Right-Click Context Menu ────────────────────────────────────
        self.context_menu = tk.Menu(self.root, tearoff=0, bg="#111927", fg="#e2e8f0", activebackground="#00adb5", activeforeground="#0b1017", font=("Segoe UI", 9))
        self.context_menu.add_command(label="✎  Edit Metadata (Popup)...", command=self.open_edit_popup)
        self.context_menu.add_command(label="⚡  Open Code in Editor", command=self.open_selected_code)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🗑  Delete Script", command=self.delete_selected_script)

        # ── 5. Bottom Real-time Deployment Terminal ────────────────────────
        term_frame = tk.Frame(self.root, bg=self.clr_card, padx=12, pady=8, highlightthickness=1, highlightbackground=self.clr_border)
        term_frame.pack(fill=tk.X, padx=16, pady=(0, 12))

        tk.Label(term_frame, text="DEPLOYMENT TERMINAL LOG:", fg=self.clr_cyan, bg=self.clr_card, font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 4))
        self.txt_log = scrolledtext.ScrolledText(term_frame, bg="#080c12", fg="#38bdf8", font=("Consolas", 9), height=5, relief="solid", bd=1)
        self.txt_log.pack(fill=tk.X)

    def log(self, text: str, tag: str = None):
        self.txt_log.insert(tk.END, f"{text}\n")
        self.txt_log.see(tk.END)

    def open_settings(self):
        SettingsDialog(self.root, self.cfg, self.on_settings_saved)

    def on_settings_saved(self, new_cfg):
        self.cfg = new_cfg
        repo_name = f"{self.cfg['repo_owner']}/{self.cfg['repo_name']}"
        self.lbl_repo_badge.configure(text=f"REPO: {repo_name} [{self.cfg['branch']}]")
        self.log(f"Settings updated for {repo_name}.")
        self.check_connection_async()

    def check_connection_async(self):
        def _check():
            tok = self.cfg.get("github_token", "")
            status, user, msg = check_github_api(tok)
            if status == "OK":
                self.lbl_health.configure(text=f"🟢 {msg}", fg=self.clr_green)
            else:
                self.lbl_health.configure(text=f"🔴 {msg}", fg="#f87171")
        threading.Thread(target=_check, daemon=True).start()

    def refresh_inventory(self):
        self.patches_list = update_manifest()
        self.filter_tree()
        self.log(f"Inventory refreshed: {len(self.patches_list)} patch script(s) loaded.")

    def filter_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        q = self.var_search.get().strip().lower()
        selected_brand = self.var_brand_filter.get().strip().upper()
        self.tree_item_map = {}

        for p in self.patches_list:
            p_brand = p.get('brand', 'UNIVERSAL').upper()

            # Brand filter logic
            if selected_brand not in ("ALL BRANDS", "ALL", ""):
                if p_brand != selected_brand:
                    continue

            # Text query search
            haystack = f"{p.get('brand','')} {p.get('model','')} {p.get('title','')} {p.get('category','')} {p.get('symptom','')}".lower()
            if q and q not in haystack:
                continue

            item_id = self.tree.insert("", tk.END, values=(
                p.get("brand", "ALL"),
                f"{p.get('model', '')} ({p.get('board_code', 'N/A')})",
                p.get("title", ""),
                p.get("category", ""),
                p.get("symptom", "N/A")
            ))
            self.tree_item_map[item_id] = p

        self.current_selected_patch = None
        self.update_delete_button_state()

    def on_tree_select(self, event):
        sel = self.tree.selection()
        if not sel:
            self.current_selected_patch = None
            self.update_delete_button_state()
            return
        p = self.tree_item_map.get(sel[0])
        if p:
            self.current_selected_patch = p
            self.update_delete_button_state()

    def update_delete_button_state(self):
        if self.current_selected_patch:
            self.btn_del.configure(
                state=tk.NORMAL,
                bg="#3d1818",
                fg="#f87171",
                cursor="hand2"
            )
        else:
            self.btn_del.configure(
                state=tk.DISABLED,
                bg="#1e293b",
                fg="#64748b",
                cursor="arrow"
            )

    def show_context_menu(self, event):
        row_id = self.tree.identify_row(event.y)
        if row_id:
            self.tree.selection_set(row_id)
            self.on_tree_select(None)
            self.context_menu.tk_popup(event.x_root, event.y_root)

    def open_edit_popup(self):
        if not self.current_selected_patch:
            messagebox.showwarning("Notice", "Please select a script from the table first.")
            return

        p = self.current_selected_patch
        script_rel = p.get("script_file")
        full_py_path = os.path.join(SCRIPT_DIR, script_rel.replace("/", os.sep))

        dlg = tk.Toplevel(self.root)
        dlg.title(f"Edit Patch — {p.get('title')}")
        dlg.geometry("560x580")
        dlg.configure(bg=self.clr_bg)
        dlg.transient(self.root)
        dlg.grab_set()

        frame = tk.Frame(dlg, bg=self.clr_bg, padx=20, pady=16)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="EDIT SCRIPT METADATA", fg=self.clr_cyan_bright, bg=self.clr_bg, font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 10))

        # Title (with prominent cyan cursor)
        tk.Label(frame, text="Patch Title:", fg=self.clr_dim, bg=self.clr_bg, font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(4, 1))
        var_title = tk.StringVar(value=p.get("title", ""))
        ent_title = tk.Entry(
            frame, textvariable=var_title, bg="#080c12", fg=self.clr_text, font=("Segoe UI", 9), relief="solid", bd=1,
            insertbackground=self.clr_cyan_bright, insertwidth=2
        )
        ent_title.pack(fill=tk.X)

        # Brand & Category row
        row_bc = tk.Frame(frame, bg=self.clr_bg)
        row_bc.pack(fill=tk.X, pady=(6, 0))

        col_b = tk.Frame(row_bc, bg=self.clr_bg)
        col_b.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        tk.Label(col_b, text="Brand:", fg=self.clr_dim, bg=self.clr_bg, font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 1))
        var_brand = tk.StringVar(value=p.get("brand", "UNIVERSAL"))
        cmb_brand = ttk.Combobox(col_b, textvariable=var_brand, values=["DELL", "LENOVO", "HP", "ASUS", "ACER", "APPLE", "UNIVERSAL"], state="readonly")
        cmb_brand.pack(fill=tk.X)

        col_c = tk.Frame(row_bc, bg=self.clr_bg)
        col_c.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        tk.Label(col_c, text="Category:", fg=self.clr_dim, bg=self.clr_bg, font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 1))
        var_cat = tk.StringVar(value=p.get("category", "General"))
        cmb_cat = ttk.Combobox(col_c, textvariable=var_cat, values=["RAM Disable", "Delay Fix", "Error Fix", "TPM Clear", "Power-On Lock", "General"])
        cmb_cat.pack(fill=tk.X)

        # Model & Board Code row
        row_mb = tk.Frame(frame, bg=self.clr_bg)
        row_mb.pack(fill=tk.X, pady=(6, 0))

        col_m = tk.Frame(row_mb, bg=self.clr_bg)
        col_m.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        tk.Label(col_m, text="Model Name:", fg=self.clr_dim, bg=self.clr_bg, font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 1))
        var_model = tk.StringVar(value=p.get("model", ""))
        ent_model = tk.Entry(
            col_m, textvariable=var_model, bg="#080c12", fg=self.clr_text, font=("Segoe UI", 9), relief="solid", bd=1,
            insertbackground=self.clr_cyan_bright, insertwidth=2
        )
        ent_model.pack(fill=tk.X)

        col_bd = tk.Frame(row_mb, bg=self.clr_bg)
        col_bd.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        tk.Label(col_bd, text="Board Part Number:", fg=self.clr_dim, bg=self.clr_bg, font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 1))
        var_board = tk.StringVar(value=p.get("board_code", "N/A"))
        ent_board = tk.Entry(
            col_bd, textvariable=var_board, bg="#080c12", fg=self.clr_text, font=("Segoe UI", 9), relief="solid", bd=1,
            insertbackground=self.clr_cyan_bright, insertwidth=2
        )
        ent_board.pack(fill=tk.X)

        # Symptom
        tk.Label(frame, text="Symptom / Observed Issue:", fg="#eab308", bg=self.clr_bg, font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(6, 1))
        txt_symp = tk.Text(
            frame, bg="#080c12", fg="#fef08a", font=("Segoe UI", 9), height=3, relief="solid", bd=1,
            insertbackground=self.clr_cyan_bright, insertwidth=2
        )
        txt_symp.insert("1.0", p.get("symptom", "N/A"))
        txt_symp.pack(fill=tk.X)

        # Description
        tk.Label(frame, text="Description / Action:", fg=self.clr_dim, bg=self.clr_bg, font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(6, 1))
        txt_desc = tk.Text(
            frame, bg="#080c12", fg=self.clr_text, font=("Segoe UI", 9), height=5, relief="solid", bd=1,
            insertbackground=self.clr_cyan_bright, insertwidth=2
        )
        txt_desc.insert("1.0", p.get("description", ""))
        txt_desc.pack(fill=tk.X, pady=(0, 14))

        def _save():
            new_title = var_title.get().strip()
            if not new_title:
                messagebox.showerror("Validation", "Patch title cannot be empty!")
                return

            updated_info = dict(p)
            updated_info["title"] = new_title
            updated_info["brand"] = var_brand.get().strip().upper()
            updated_info["category"] = var_cat.get().strip()
            updated_info["model"] = var_model.get().strip()
            updated_info["board_code"] = var_board.get().strip()
            updated_info["symptom"] = txt_symp.get("1.0", tk.END).strip()
            updated_info["description"] = txt_desc.get("1.0", tk.END).strip()

            ok, msg = update_script_patch_info(full_py_path, updated_info)
            if ok:
                update_manifest()
                self.refresh_inventory()
                self.log(f"Updated metadata for: {new_title}")
                dlg.destroy()
                messagebox.showinfo("Success", f"Metadata saved successfully!\nScript updated: {os.path.basename(full_py_path)}")
            else:
                messagebox.showerror("Error", f"Failed to save:\n{msg}")

        btn_row = tk.Frame(frame, bg=self.clr_bg)
        btn_row.pack(fill=tk.X)

        tk.Button(
            btn_row, text="💾 SAVE CHANGES", bg=self.clr_cyan, fg="#0b1017",
            font=("Segoe UI", 10, "bold"), relief="flat", padx=16, pady=8, cursor="hand2",
            activebackground=self.clr_cyan_bright, activeforeground="#0b1017",
            command=_save
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        tk.Button(
            btn_row, text="Cancel", bg="#1e293b", fg=self.clr_dim,
            font=("Segoe UI", 10), relief="flat", padx=16, pady=8, cursor="hand2",
            command=dlg.destroy
        ).pack(side=tk.RIGHT)

    def on_detect_updates(self):
        self.log("\n=======================================================", "info")
        self.log("[SCAN] Detecting scripts & changes in patches/...", "info")

        prev_map = {}
        if os.path.exists(MANIFEST_FILE):
            try:
                with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
                    for item in json.load(f):
                        prev_map[item.get("script_file")] = item
            except Exception:
                pass

        current_manifest = scan_patches()
        current_map = {item.get("script_file"): item for item in current_manifest}

        new_scripts = []
        modified_scripts = []
        deleted_scripts = []

        for rel_path, info in current_map.items():
            if rel_path not in prev_map:
                new_scripts.append(f"{info.get('brand')} - {info.get('title')} ({rel_path})")
            else:
                prev_info = prev_map[rel_path]
                if (info.get("title") != prev_info.get("title") or 
                    info.get("description") != prev_info.get("description") or 
                    info.get("symptom") != prev_info.get("symptom") or 
                    info.get("model") != prev_info.get("model") or
                    info.get("last_modified") != prev_info.get("last_modified")):
                    modified_scripts.append(f"{info.get('title')} ({rel_path})")

        for rel_path, info in prev_map.items():
            if rel_path not in current_map:
                deleted_scripts.append(f"{info.get('title')} ({rel_path})")

        if new_scripts:
            self.log(f"  [+] Found {len(new_scripts)} NEW script(s):", "ok")
            for ns in new_scripts:
                self.log(f"      • {ns}", "ok")

        if modified_scripts:
            self.log(f"  [*] Found {len(modified_scripts)} MODIFIED script(s):", "info")
            for ms in modified_scripts:
                self.log(f"      • {ms}", "info")

        if deleted_scripts:
            self.log(f"  [-] Found {len(deleted_scripts)} DELETED script(s):", "warn")
            for ds in deleted_scripts:
                self.log(f"      • {ds}", "warn")

        if not new_scripts and not modified_scripts and not deleted_scripts:
            self.log(f"  [=] All {len(current_manifest)} scripts verified. Catalog is synchronized.", "info")

        with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
            json.dump(current_manifest, f, indent=2, ensure_ascii=False)

        self.patches_list = current_manifest
        self.filter_tree()

        # Unlock the PUSH TO GITHUB button
        self.btn_push.configure(
            state=tk.NORMAL,
            bg=self.clr_cyan,
            fg="#0b1017",
            cursor="hand2"
        )
        self.lbl_inv_status.configure(
            text=f"Updates detected ({len(current_manifest)} scripts). Ready to push!",
            fg=self.clr_cyan_bright
        )
        self.log(f"[READY] manifest.json updated. 'PUSH TO GITHUB' button is now UNLOCKED!", "ok")
        self.log("=======================================================\n", "info")

    def open_selected_code(self):
        if not self.current_selected_patch:
            return
        script_rel = self.current_selected_patch.get("script_file")
        full_py_path = os.path.join(SCRIPT_DIR, script_rel.replace("/", os.sep))
        if os.path.exists(full_py_path):
            os.startfile(full_py_path)
            self.log(f"Opened code in editor: {os.path.basename(full_py_path)}")
        else:
            messagebox.showerror("Error", f"File does not exist:\n{full_py_path}")

    def delete_selected_script(self):
        if not self.current_selected_patch:
            messagebox.showwarning("Notice", "Please select a script from the table first.")
            return

        title = self.current_selected_patch.get("title")
        script_rel = self.current_selected_patch.get("script_file")
        full_py_path = os.path.join(SCRIPT_DIR, script_rel.replace("/", os.sep))

        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete this patch?\n\n'{title}'\nFile: {script_rel}\n\nThis will remove the file and update manifest.json."
        )
        if not confirm:
            return

        try:
            if os.path.exists(full_py_path):
                os.remove(full_py_path)
            self.refresh_inventory()
            self.log(f"Deleted script: {script_rel}")
            messagebox.showinfo("Deleted", f"Patch '{title}' deleted successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Could not delete file:\n{e}")

    def deploy_to_github(self):
        tok = self.cfg.get("github_token", "").strip()
        repo_owner = self.cfg.get("repo_owner", "rscomputer204-netizen").strip()
        repo_name = self.cfg.get("repo_name", "R1_AutoPatch_Database").strip()
        branch = self.cfg.get("branch", "main").strip()

        if not tok:
            messagebox.showerror("Configuration Error", "No GitHub token configured!\nPlease click '⚙️ Settings' in the top header and enter your token.")
            return

        manifest = update_manifest()
        self.btn_push.configure(state=tk.DISABLED, text="🚀 DEPLOYING...")
        self.log(f"Preparing to push {len(manifest)} scripts to {repo_owner}/{repo_name} [{branch}]...")

        def _worker():
            import tempfile
            temp_dir = tempfile.mkdtemp(prefix="autopatch_push_")
            try:
                for item in os.listdir(SCRIPT_DIR):
                    if item.startswith(".") or item == "__pycache__":
                        continue
                    s = os.path.join(SCRIPT_DIR, item)
                    d = os.path.join(temp_dir, item)
                    if os.path.isdir(s):
                        shutil.copytree(s, d, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
                    else:
                        shutil.copy2(s, d)

                readme = os.path.join(temp_dir, "README.md")
                if not os.path.exists(readme):
                    with open(readme, "w", encoding="utf-8") as f:
                        f.write(f"# R1 AutoPatch Database 🚀\nCloud repository of BIOS fix and patch scripts for **R1 BIOS TOOL**.\n\nTotal Patches: {len(manifest)}\n")

                self.log("Initializing git bundle...")
                subprocess.run(["git", "init"], cwd=temp_dir, check=True, capture_output=True)
                subprocess.run(["git", "config", "user.name", "R1 LAB"], cwd=temp_dir, check=True, capture_output=True)
                subprocess.run(["git", "config", "user.email", "r1lab@bios-tool.local"], cwd=temp_dir, check=True, capture_output=True)
                subprocess.run(["git", "checkout", "-b", branch], cwd=temp_dir, check=True, capture_output=True)
                subprocess.run(["git", "add", "."], cwd=temp_dir, check=True, capture_output=True)

                commit_msg = f"AutoPatch Cloud Sync: {len(manifest)} scripts updated ({time.strftime('%Y-%m-%d %H:%M')})"
                subprocess.run(["git", "commit", "-m", commit_msg], cwd=temp_dir, check=True, capture_output=True)

                self.log(f"Streaming push to https://github.com/{repo_owner}/{repo_name}.git...")
                auth_url = f"https://x-access-token:{tok}@github.com/{repo_owner}/{repo_name}.git"
                
                proc = subprocess.Popen(
                    f'git -c credential.helper= push -u "{auth_url}" {branch} --force',
                    shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=temp_dir
                )

                for line in proc.stdout:
                    l = line.strip()
                    if l:
                        self.log(f"  {l}")

                proc.wait()

                if proc.returncode == 0:
                    self.log(f"SUCCESS: AutoPatch repository is 100% updated on GitHub!")
                    messagebox.showinfo(
                        "Deployment Complete",
                        f"All {len(manifest)} scripts and manifest successfully deployed to:\nhttps://github.com/{repo_owner}/{repo_name}\n\nClient machines can now instantly access these patches!"
                    )
                else:
                    self.log(f"ERROR: Git push exited with code {proc.returncode}")
                    messagebox.showerror("Error", f"Failed to push to GitHub. Code: {proc.returncode}")

            except Exception as e:
                self.log(f"Exception during deployment: {e}")
                messagebox.showerror("Exception", f"Deployment error:\n{e}")
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)
                self.btn_push.configure(state=tk.NORMAL, text="🚀 PUSH TO GITHUB")

        threading.Thread(target=_worker, daemon=True).start()


if __name__ == "__main__":
    root = tk.Tk()
    app = AutoPatchManagerApp(root)
    root.mainloop()
