"""
R1 AUTOPATCH ❖ SCRIPT & CLOUD REPOSITORY MANAGER
================================================
Dedicated visual deployment and patch management suite for R1_AutoPatch_Database.
Features:
- Live GitHub API connection health monitor
- "NEW UPDATE DETECT" scans for newly added, modified, or deleted scripts
- In-place metadata editor (Edit Title, Description, Symptom, Model, etc.)
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

REPO_OWNER = "rscomputer204-netizen"
REPO_NAME = "R1_AutoPatch_Database"
DEFAULT_BRANCH = "main"


def load_github_token():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("github_token", "").strip()
        except Exception:
            pass
    return ""


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


class AutoPatchManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("R1 AutoPatch ❖ Script & Cloud Repository Manager")
        self.root.geometry("1100x750")
        self.root.minsize(980, 640)

        # Colors matching push_to_github.py Cyber Blue theme
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
        tk.Label(title_box, text="DYNAMIC BIOS PATCH INVENTORY, IN-PLACE METADATA EDITOR & REPO DEPLOYER", fg=self.clr_dim, bg=self.clr_header,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")

        # Right Header: Connection Health Badge
        health_box = tk.Frame(header, bg=self.clr_card, padx=12, pady=6, highlightthickness=1, highlightbackground=self.clr_border)
        health_box.pack(side=tk.RIGHT)

        tk.Label(health_box, text=f"REPO: {REPO_OWNER}/{REPO_NAME} [{DEFAULT_BRANCH}]", fg=self.clr_cyan, bg=self.clr_card, font=("Segoe UI", 8, "bold")).pack(anchor="e")
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

        # Button 2: Delete Script
        btn_del = tk.Button(
            action_bar, text="🗑 DELETE SCRIPT", bg="#2a1515", fg="#f87171",
            font=("Segoe UI", 9, "bold"), relief="flat", padx=14, pady=7, cursor="hand2",
            activebackground="#451a1a", activeforeground="#ffffff",
            command=self.delete_selected_script
        )
        btn_del.pack(side=tk.LEFT, padx=(0, 14))

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

        # ── 3. Main Split Container (Left: Inventory Table, Right: In-Place Editor)
        content_frame = tk.Frame(self.root, bg=self.clr_bg)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 10))

        # --- LEFT PANEL: Script Inventory ---
        left_frame = tk.Frame(content_frame, bg=self.clr_card, width=540, padx=12, pady=10, highlightthickness=1, highlightbackground=self.clr_border)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        # Search bar row
        search_row = tk.Frame(left_frame, bg=self.clr_card)
        search_row.pack(fill=tk.X, pady=(0, 8))

        tk.Label(search_row, text="SEARCH:", fg=self.clr_dim, bg=self.clr_card, font=("Segoe UI", 8, "bold")).pack(side=tk.LEFT, padx=(0, 6))
        self.var_search = tk.StringVar()
        self.var_search.trace_add("write", lambda *args: self.filter_tree())
        ent_search = tk.Entry(search_row, textvariable=self.var_search, bg="#080c12", fg=self.clr_cyan_bright, font=("Segoe UI", 9), relief="solid", bd=1)
        ent_search.pack(side=tk.LEFT, fill=tk.X, expand=True)

        btn_refresh = tk.Button(search_row, text="↻ Refresh", bg="#1e293b", fg=self.clr_text, font=("Segoe UI", 8), relief="flat", padx=8, command=self.refresh_inventory)
        btn_refresh.pack(side=tk.RIGHT, padx=(8, 0))

        # Treeview
        tree_style = ttk.Style()
        tree_style.theme_use("clam")
        tree_style.configure("Treeview", background="#080c12", foreground="#e2e8f0", fieldbackground="#080c12", rowheight=26, font=("Segoe UI", 9))
        tree_style.configure("Treeview.Heading", background="#1a2536", foreground="#00f3ff", font=("Segoe UI", 9, "bold"))
        tree_style.map("Treeview", background=[("selected", "#1b314f")], foreground=[("selected", "#ffffff")])

        columns = ("brand", "model", "title", "category")
        self.tree = ttk.Treeview(left_frame, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("brand", text="Brand")
        self.tree.heading("model", text="Model")
        self.tree.heading("title", text="Title")
        self.tree.heading("category", text="Category")

        self.tree.column("brand", width=75, anchor="center")
        self.tree.column("model", width=140)
        self.tree.column("title", width=190)
        self.tree.column("category", width=95, anchor="center")

        tree_scroll = ttk.Scrollbar(left_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<Double-1>", lambda e: self.open_selected_code())

        # --- RIGHT PANEL: In-Place Metadata Editor ---
        right_frame = tk.Frame(content_frame, bg=self.clr_card, width=460, padx=14, pady=12, highlightthickness=1, highlightbackground=self.clr_border)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH)
        right_frame.pack_propagate(False)

        tk.Label(right_frame, text="EDIT SCRIPT METADATA", fg=self.clr_cyan_bright, bg=self.clr_card, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 6))

        # Form Entries
        self.edit_vars = {
            "title": tk.StringVar(),
            "brand": tk.StringVar(),
            "model": tk.StringVar(),
            "board_code": tk.StringVar(),
            "category": tk.StringVar(),
            "version": tk.StringVar(),
        }

        form_grid = tk.Frame(right_frame, bg=self.clr_card)
        form_grid.pack(fill=tk.X, pady=(0, 6))

        # Title
        tk.Label(form_grid, text="Patch Title:", fg=self.clr_dim, bg=self.clr_card, font=("Segoe UI", 8, "bold")).grid(row=0, column=0, sticky="w", pady=2)
        tk.Entry(form_grid, textvariable=self.edit_vars["title"], bg="#080c12", fg=self.clr_text, font=("Segoe UI", 9), relief="solid", bd=1).grid(row=0, column=1, sticky="ew", pady=2, padx=(6, 0))

        # Brand & Category row
        tk.Label(form_grid, text="Brand / Cat:", fg=self.clr_dim, bg=self.clr_card, font=("Segoe UI", 8, "bold")).grid(row=1, column=0, sticky="w", pady=2)
        row1_box = tk.Frame(form_grid, bg=self.clr_card)
        row1_box.grid(row=1, column=1, sticky="ew", pady=2, padx=(6, 0))

        cmb_brand = ttk.Combobox(row1_box, textvariable=self.edit_vars["brand"], values=["DELL", "LENOVO", "HP", "ASUS", "ACER", "APPLE", "UNIVERSAL"], width=10, state="readonly")
        cmb_brand.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        cmb_cat = ttk.Combobox(row1_box, textvariable=self.edit_vars["category"], values=["RAM Disable", "Delay Fix", "Error Fix", "TPM Clear", "Power-On Lock", "General"], width=12)
        cmb_cat.pack(side=tk.RIGHT, fill=tk.X, expand=True)

        # Model & Board Code
        tk.Label(form_grid, text="Model / Board:", fg=self.clr_dim, bg=self.clr_card, font=("Segoe UI", 8, "bold")).grid(row=2, column=0, sticky="w", pady=2)
        row2_box = tk.Frame(form_grid, bg=self.clr_card)
        row2_box.grid(row=2, column=1, sticky="ew", pady=2, padx=(6, 0))
        tk.Entry(row2_box, textvariable=self.edit_vars["model"], bg="#080c12", fg=self.clr_text, font=("Segoe UI", 9), relief="solid", bd=1).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        tk.Entry(row2_box, textvariable=self.edit_vars["board_code"], bg="#080c12", fg=self.clr_text, font=("Segoe UI", 9), relief="solid", bd=1, width=12).pack(side=tk.RIGHT)

        form_grid.columnconfigure(1, weight=1)

        # Symptom
        tk.Label(right_frame, text="Symptom / Observed Issue:", fg="#eab308", bg=self.clr_card, font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(4, 2))
        self.txt_symptom = tk.Text(right_frame, bg="#080c12", fg="#fef08a", font=("Segoe UI", 9), height=2, relief="solid", bd=1)
        self.txt_symptom.pack(fill=tk.X, pady=(0, 4))

        # Description
        tk.Label(right_frame, text="Description / Action:", fg=self.clr_dim, bg=self.clr_card, font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(2, 2))
        self.txt_desc = tk.Text(right_frame, bg="#080c12", fg=self.clr_text, font=("Segoe UI", 9), height=4, relief="solid", bd=1)
        self.txt_desc.pack(fill=tk.X, pady=(0, 8))

        # Save Button
        btn_save = tk.Button(
            right_frame, text="💾 SAVE SCRIPT METADATA", bg=self.clr_cyan, fg="#0b1017",
            font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=7, cursor="hand2",
            activebackground=self.clr_cyan_bright, activeforeground="#0b1017",
            command=self.save_metadata_changes
        )
        btn_save.pack(fill=tk.X, pady=(0, 6))

        # Helper note
        tk.Label(
            right_frame,
            text="Tip: Double-click any script in the table to open its code in your editor.",
            fg="#64748b", bg=self.clr_card, font=("Segoe UI", 8, "italic")
        ).pack(anchor="w")

        # ── 4. Bottom Real-time Deployment Terminal ────────────────────────
        term_frame = tk.Frame(self.root, bg=self.clr_card, padx=12, pady=8, highlightthickness=1, highlightbackground=self.clr_border)
        term_frame.pack(fill=tk.X, padx=16, pady=(0, 12))

        tk.Label(term_frame, text="DEPLOYMENT TERMINAL LOG:", fg=self.clr_cyan, bg=self.clr_card, font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 4))
        self.txt_log = scrolledtext.ScrolledText(term_frame, bg="#080c12", fg="#38bdf8", font=("Consolas", 9), height=5, relief="solid", bd=1)
        self.txt_log.pack(fill=tk.X)

    def log(self, text: str, tag: str = None):
        self.txt_log.insert(tk.END, f"{text}\n")
        self.txt_log.see(tk.END)

    def check_connection_async(self):
        def _check():
            tok = load_github_token()
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
        self.tree_item_map = {}

        for p in self.patches_list:
            haystack = f"{p.get('brand','')} {p.get('model','')} {p.get('title','')} {p.get('category','')}".lower()
            if q and q not in haystack:
                continue

            item_id = self.tree.insert("", tk.END, values=(
                p.get("brand", "ALL"),
                p.get("model", ""),
                p.get("title", ""),
                p.get("category", "")
            ))
            self.tree_item_map[item_id] = p

        # Auto select first
        children = self.tree.get_children()
        if children:
            self.tree.selection_set(children[0])
            self.on_tree_select(None)

    def on_tree_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        p = self.tree_item_map.get(sel[0])
        if not p:
            return

        self.current_selected_patch = p
        self.edit_vars["title"].set(p.get("title", ""))
        self.edit_vars["brand"].set(p.get("brand", "UNIVERSAL"))
        self.edit_vars["model"].set(p.get("model", ""))
        self.edit_vars["board_code"].set(p.get("board_code", "N/A"))
        self.edit_vars["category"].set(p.get("category", "General"))
        self.edit_vars["version"].set(p.get("version", "1.0.0"))

        self.txt_symptom.delete("1.0", tk.END)
        self.txt_symptom.insert("1.0", p.get("symptom", "N/A"))

        self.txt_desc.delete("1.0", tk.END)
        self.txt_desc.insert("1.0", p.get("description", ""))

    def on_detect_updates(self):
        """
        Scans patches/ folder deeply, detects added, modified or deleted scripts,
        updates manifest.json, and enables the 'PUSH TO GITHUB' button.
        """
        self.log("\n=======================================================", "info")
        self.log("[SCAN] Detecting scripts & changes in patches/...", "info")

        # Read existing manifest to compare
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

        # Log findings
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

        # Synchronize manifest.json
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

    def save_metadata_changes(self):
        if not self.current_selected_patch:
            messagebox.showwarning("Notice", "Please select a script from the table first.")
            return

        script_rel = self.current_selected_patch.get("script_file")
        full_py_path = os.path.join(SCRIPT_DIR, script_rel.replace("/", os.sep))

        updated_info = dict(self.current_selected_patch)
        updated_info["title"] = self.edit_vars["title"].get().strip()
        updated_info["brand"] = self.edit_vars["brand"].get().strip().upper()
        updated_info["model"] = self.edit_vars["model"].get().strip()
        updated_info["board_code"] = self.edit_vars["board_code"].get().strip()
        updated_info["category"] = self.edit_vars["category"].get().strip()
        updated_info["symptom"] = self.txt_symptom.get("1.0", tk.END).strip()
        updated_info["description"] = self.txt_desc.get("1.0", tk.END).strip()

        ok, msg = update_script_patch_info(full_py_path, updated_info)
        if ok:
            update_manifest()
            self.refresh_inventory()
            self.log(f"Updated metadata for: {updated_info['title']}")
            messagebox.showinfo("Success", f"Metadata saved and script updated:\n{os.path.basename(full_py_path)}")
        else:
            messagebox.showerror("Error", f"Failed to update script:\n{msg}")

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
        tok = load_github_token()
        if not tok:
            messagebox.showerror("Error", "No GitHub token found in config/github_token.json!")
            return

        manifest = update_manifest()
        self.btn_push.configure(state=tk.DISABLED, text="🚀 DEPLOYING...")
        self.log(f"Preparing to push {len(manifest)} scripts to {REPO_OWNER}/{REPO_NAME}...")

        def _worker():
            import tempfile
            temp_dir = tempfile.mkdtemp(prefix="autopatch_push_")
            try:
                # Copy everything from SCRIPT_DIR
                for item in os.listdir(SCRIPT_DIR):
                    if item.startswith(".") or item == "__pycache__":
                        continue
                    s = os.path.join(SCRIPT_DIR, item)
                    d = os.path.join(temp_dir, item)
                    if os.path.isdir(s):
                        shutil.copytree(s, d, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
                    else:
                        shutil.copy2(s, d)

                # Ensure README exists
                readme = os.path.join(temp_dir, "README.md")
                if not os.path.exists(readme):
                    with open(readme, "w", encoding="utf-8") as f:
                        f.write(f"# R1 AutoPatch Database 🚀\nCloud repository of BIOS fix and patch scripts for **R1 BIOS TOOL**.\n\nTotal Patches: {len(manifest)}\n")

                # Git commit & push
                self.log("Initializing git bundle...")
                subprocess.run(["git", "init"], cwd=temp_dir, check=True, capture_output=True)
                subprocess.run(["git", "config", "user.name", "R1 LAB"], cwd=temp_dir, check=True, capture_output=True)
                subprocess.run(["git", "config", "user.email", "r1lab@bios-tool.local"], cwd=temp_dir, check=True, capture_output=True)
                subprocess.run(["git", "checkout", "-b", DEFAULT_BRANCH], cwd=temp_dir, check=True, capture_output=True)
                subprocess.run(["git", "add", "."], cwd=temp_dir, check=True, capture_output=True)

                commit_msg = f"AutoPatch Cloud Sync: {len(manifest)} scripts updated ({time.strftime('%Y-%m-%d %H:%M')})"
                subprocess.run(["git", "commit", "-m", commit_msg], cwd=temp_dir, check=True, capture_output=True)

                self.log(f"Streaming push to https://github.com/{REPO_OWNER}/{REPO_NAME}.git...")
                auth_url = f"https://x-access-token:{tok}@github.com/{REPO_OWNER}/{REPO_NAME}.git"
                
                proc = subprocess.Popen(
                    f'git -c credential.helper= push -u "{auth_url}" {DEFAULT_BRANCH} --force',
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
                        f"All {len(manifest)} scripts and manifest successfully deployed to:\nhttps://github.com/{REPO_OWNER}/{REPO_NAME}\n\nClient machines can now instantly access these patches!"
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
