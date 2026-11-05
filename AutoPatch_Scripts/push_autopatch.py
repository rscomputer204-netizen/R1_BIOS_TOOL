"""
R1 BIOS TOOL — AUTOPATCH CLOUD DEPLOYMENT & SCRIPT MANAGER
=========================================================
Standalone manager for AutoPatch scripts:
1. Auto-scans all patches in patches/ and updates manifest.json
2. Visual Template Generator for new patch scripts (RAM disable, Delay fix, etc.)
3. One-click commit and push to GitHub repository
"""

import os
import sys
import json
import glob
import ast
import time
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
PATCHES_DIR = os.path.join(BASE_DIR, "patches")
MANIFEST_FILE = os.path.join(BASE_DIR, "manifest.json")
CONFIG_FILE = os.path.join(ROOT_DIR, "config", "github_token.json")


def scan_patches():
    """Scans all .py files in patches/ and extracts PATCH_INFO dicts."""
    manifest = []
    if not os.path.exists(PATCHES_DIR):
        os.makedirs(PATCHES_DIR, exist_ok=True)
        return manifest

    py_files = glob.glob(os.path.join(PATCHES_DIR, "**", "*.py"), recursive=True)
    for py_path in py_files:
        rel_path = os.path.relpath(py_path, BASE_DIR).replace("\\", "/")
        try:
            with open(py_path, "r", encoding="utf-8") as f:
                code = f.read()

            # Parse AST to extract PATCH_INFO without running arbitrary code
            tree = ast.parse(code)
            info = {}
            for node in tree.body:
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == "PATCH_INFO":
                            # Safe evaluate dictionary
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
                # Ensure essential fields
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
            print(f"[!] Error parsing {py_path}: {e}")

    # Sort by brand, then title
    manifest.sort(key=lambda x: (x.get("brand", ""), x.get("title", "")))
    return manifest


def update_manifest():
    """Builds and writes manifest.json."""
    data = scan_patches()
    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return data


class AutoPatchManagerGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("R1 AutoPatch — Script Manager & GitHub Deployer")
        self.geometry("960, 680")
        self.configure(bg="#0b1017")
        self.minsize(800, 550)

        self.apply_theme()
        self.build_ui()
        self.refresh_list()

    def apply_theme(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", background="#0b1017", foreground="#e2e8f0", font=("Segoe UI", 10))
        style.configure("TFrame", background="#0b1017")
        style.configure("Card.TFrame", background="#111927", relief="solid", borderwidth=1)
        style.configure("TLabel", background="#0b1017", foreground="#e2e8f0")
        style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"), foreground="#00f3ff")
        style.configure("Sub.TLabel", font=("Segoe UI", 9), foreground="#7e8f9f")
        style.configure("Cyber.TButton", background="#00f3ff", foreground="#0b1017", font=("Segoe UI", 10, "bold"), borderwidth=0)
        style.map("Cyber.TButton", background=[("active", "#00c4cc"), ("disabled", "#334155")])
        style.configure("Action.TButton", background="#1e293b", foreground="#e2e8f0", font=("Segoe UI", 9, "bold"))
        style.map("Action.TButton", background=[("active", "#334155")])

    def build_ui(self):
        # Top Header
        top_bar = ttk.Frame(self, padding=(20, 15))
        top_bar.pack(fill="x")
        
        ttk.Label(top_bar, text="AUTOPATCH SCRIPT MANAGER", style="Header.TLabel").pack(anchor="w")
        ttk.Label(top_bar, text="Manage, create, and deploy BIOS patch scripts directly to GitHub Cloud.", style="Sub.TLabel").pack(anchor="w")

        # Main horizontal split
        main_pane = ttk.PanedWindow(self, orient="horizontal")
        main_pane.pack(fill="both", expand=True, padx=20, pady=5)

        # Left: Script List
        left_frame = ttk.Frame(main_pane, style="Card.TFrame", padding=10)
        main_pane.add(left_frame, weight=3)

        list_header = ttk.Frame(left_frame)
        list_header.pack(fill="x", pady=(0, 8))
        ttk.Label(list_header, text="Available Patches", font=("Segoe UI", 11, "bold"), foreground="#00f3ff").pack(side="left")
        
        btn_refresh = ttk.Button(list_header, text="↻ Refresh", style="Action.TButton", command=self.refresh_list)
        btn_refresh.pack(side="right")

        # Treeview for patches
        columns = ("brand", "model", "category", "title")
        self.tree = ttk.Treeview(left_frame, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("brand", text="Brand")
        self.tree.heading("model", text="Model")
        self.tree.heading("category", text="Category")
        self.tree.heading("title", text="Patch Title")
        self.tree.column("brand", width=80, anchor="center")
        self.tree.column("model", width=140)
        self.tree.column("category", width=100, anchor="center")
        self.tree.column("title", width=180)
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select_patch)

        # Right: Details & Create New
        right_frame = ttk.Frame(main_pane, style="Card.TFrame", padding=15)
        main_pane.add(right_frame, weight=2)

        ttk.Label(right_frame, text="Patch Details & Actions", font=("Segoe UI", 11, "bold"), foreground="#00f3ff").pack(anchor="w", pady=(0, 10))

        self.lbl_details = tk.Text(right_frame, bg="#0e1520", fg="#94a3b8", font=("Consolas", 9), relief="flat", height=12)
        self.lbl_details.pack(fill="x", pady=(0, 10))
        self.lbl_details.insert("1.0", "Select a patch from the list to view metadata...")
        self.lbl_details.configure(state="disabled")

        # Action Buttons
        btn_box = ttk.Frame(right_frame)
        btn_box.pack(fill="x", pady=5)

        btn_new = ttk.Button(btn_box, text="+ Create New Patch", style="Cyber.TButton", command=self.open_new_dialog)
        btn_new.pack(fill="x", pady=4)

        btn_edit = ttk.Button(btn_box, text="✎ Open Script in Editor", style="Action.TButton", command=self.open_selected_script)
        btn_edit.pack(fill="x", pady=4)

        btn_push = ttk.Button(btn_box, text="☁ Push AutoPatch to GitHub", style="Cyber.TButton", command=self.push_to_github)
        btn_push.pack(fill="x", pady=8)

        # Bottom Log / Status
        self.status_var = tk.StringVar(value="Ready.")
        status_bar = ttk.Frame(self, padding=(20, 8))
        status_bar.pack(fill="x")
        ttk.Label(status_bar, textvariable=self.status_var, foreground="#38bdf8", font=("Segoe UI", 9)).pack(side="left")

    def refresh_list(self):
        manifest = update_manifest()
        for item in self.tree.get_children():
            self.tree.delete(item)

        self.patches_map = {}
        for p in manifest:
            item_id = self.tree.insert("", "end", values=(
                p.get("brand", ""),
                p.get("model", ""),
                p.get("category", ""),
                p.get("title", "")
            ))
            self.patches_map[item_id] = p

        self.status_var.set(f"Loaded {len(manifest)} patches. manifest.json synchronized.")

    def on_select_patch(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        p = self.patches_map.get(selected[0])
        if not p:
            return

        detail_text = (
            f"ID:          {p.get('id')}\n"
            f"Brand:       {p.get('brand')}\n"
            f"Model:       {p.get('model')}\n"
            f"Board Code:  {p.get('board_code')}\n"
            f"Title:       {p.get('title')}\n"
            f"Category:    {p.get('category')}\n"
            f"Author:      {p.get('author')}\n"
            f"File:        {p.get('script_file')}\n"
            f"Modified:    {p.get('last_modified')}\n\n"
            f"Symptom:\n  {p.get('symptom')}\n\n"
            f"Description:\n  {p.get('description')}\n"
        )
        self.lbl_details.configure(state="normal")
        self.lbl_details.delete("1.0", "end")
        self.lbl_details.insert("1.0", detail_text)
        self.lbl_details.configure(state="disabled")

    def open_selected_script(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Notice", "Please select a patch first.")
            return
        p = self.patches_map.get(selected[0])
        if p and p.get("script_file"):
            full_path = os.path.join(BASE_DIR, p["script_file"].replace("/", os.sep))
            if os.path.exists(full_path):
                os.startfile(full_path)
            else:
                messagebox.showerror("Error", f"Script file not found:\n{full_path}")

    def open_new_dialog(self):
        """Opens dialog to generate a new patch template."""
        dlg = tk.Toplevel(self)
        dlg.title("New Patch Template Generator")
        dlg.geometry("520, 560")
        dlg.configure(bg="#0b1017")
        dlg.transient(self)
        dlg.grab_set()

        frame = ttk.Frame(dlg, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Generate New AutoPatch Script", style="Header.TLabel").pack(anchor="w", pady=(0, 15))

        entries = {}
        fields = [
            ("Brand:", "brand", ["DELL", "LENOVO", "HP", "ASUS", "ACER", "APPLE", "UNIVERSAL"]),
            ("Model Name:", "model", "e.g. ThinkPad T480 / Latitude 3400"),
            ("Board Part Number:", "board_code", "e.g. NM-B481 / LA-G521P"),
            ("Patch Title:", "title", "e.g. Onboard RAM Disable"),
            ("Category:", "category", ["RAM Disable", "Delay Fix", "Error Fix", "TPM Clear", "Power-On Lock", "General"]),
            ("Symptom:", "symptom", "What problem occurs? (e.g. 3 Beeps, Black screen)"),
            ("Description:", "description", "How does this patch fix the issue?"),
        ]

        for label_text, key, default in fields:
            ttk.Label(frame, text=label_text, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(6, 2))
            if isinstance(default, list):
                cb = ttk.Combobox(frame, values=default, state="readonly")
                cb.set(default[0])
                cb.pack(fill="x")
                entries[key] = cb
            else:
                ent = ttk.Entry(frame)
                ent.insert(0, default if not default.startswith("e.g.") else "")
                ent.pack(fill="x")
                entries[key] = ent

        def create_script():
            brand = entries["brand"].get().strip().upper()
            model = entries["model"].get().strip()
            board = entries["board_code"].get().strip() or "Universal"
            title = entries["title"].get().strip()
            cat = entries["category"].get().strip()
            symptom = entries["symptom"].get().strip() or "N/A"
            desc = entries["description"].get().strip() or "N/A"

            if not model or not title:
                messagebox.showerror("Validation", "Model and Title are required!")
                return

            safe_name = f"{brand.lower()}_{title.lower().replace(' ', '_').replace('/', '_')}.py"
            brand_dir = os.path.join(PATCHES_DIR, brand.lower())
            os.makedirs(brand_dir, exist_ok=True)
            target_path = os.path.join(brand_dir, safe_name)

            if os.path.exists(target_path):
                messagebox.showerror("Error", f"A script named {safe_name} already exists!")
                return

            template_code = f'''"""
AutoPatch Script: {brand} {model} - {title}
Author: R1 LAB
"""

PATCH_INFO = {{
    "id": "{brand.lower()}_{title.lower().replace(' ', '_')}",
    "brand": "{brand}",
    "model": "{model}",
    "board_code": "{board}",
    "title": "{title}",
    "category": "{cat}",
    "symptom": "{symptom}",
    "description": "{desc}",
    "version": "1.0.0",
    "author": "R1 LAB",
    "target_size_mb": [8, 16, 32],
}}

def verify(bios_data: bytearray, metadata: dict = None) -> tuple[bool, str]:
    """
    Check if the BIOS image is compatible before patching.
    Return (True, "Ready") or (False, "Reason for mismatch").
    """
    if len(bios_data) < 4 * 1024 * 1024:
        return False, "File size is too small."
    
    # TODO: Add your signature checks here
    return True, "{brand} {model} signature verified. Ready to patch."

def apply_patch(bios_data: bytearray, metadata: dict = None) -> tuple[bool, bytearray, str]:
    """
    Perform byte modifications and return (success, patched_data, message).
    """
    ok, msg = verify(bios_data, metadata)
    if not ok:
        return False, bios_data, f"Verification failed: {{msg}}"
        
    patched = bytearray(bios_data)
    
    # TODO: Put your hex search & replace or offset modification logic here
    # Example:
    # search_bytes = bytes.fromhex("...")
    # replace_bytes = bytes.fromhex("...")
    # pos = patched.find(search_bytes)
    # if pos != -1:
    #     patched[pos:pos+len(replace_bytes)] = replace_bytes

    return True, patched, "Patch applied successfully!"
'''
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(template_code)

            dlg.destroy()
            self.refresh_list()
            messagebox.showinfo("Success", f"Script generated at:\n{target_path}\nOpening editor...")
            os.startfile(target_path)

        ttk.Button(frame, text="Generate Template & Open Editor", style="Cyber.TButton", command=create_script).pack(fill="x", pady=(20, 0))

    def push_to_github(self):
        """Updates manifest and pushes AutoPatch_Scripts to GitHub."""
        manifest = update_manifest()
        self.status_var.set("Manifest updated. Staging and committing to GitHub...")
        
        try:
            cfg = {}
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)

            token = cfg.get("github_token", "")
            repo_owner = "rscomputer204-netizen"
            repo_name = "R1_AutoPatch_Database"
            branch = "main"

            if not token:
                messagebox.showerror("Error", "No GitHub token found in config/github_token.json!")
                return

            import tempfile
            import shutil

            temp_dir = tempfile.mkdtemp(prefix="autopatch_deploy_")
            try:
                # Copy everything from BASE_DIR except __pycache__ and temp
                for item in os.listdir(BASE_DIR):
                    if item.startswith(".") or item == "__pycache__":
                        continue
                    s = os.path.join(BASE_DIR, item)
                    d = os.path.join(temp_dir, item)
                    if os.path.isdir(s):
                        shutil.copytree(s, d, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
                    else:
                        shutil.copy2(s, d)

                # Ensure README exists
                readme = os.path.join(temp_dir, "README.md")
                if not os.path.exists(readme):
                    with open(readme, "w", encoding="utf-8") as f:
                        f.write("# R1 AutoPatch Database\nCloud repository of BIOS fix and patch scripts for R1 BIOS TOOL.\n")

                # Git commit & push
                subprocess.run(["git", "init"], cwd=temp_dir, check=True, capture_output=True)
                subprocess.run(["git", "config", "user.name", "R1 LAB"], cwd=temp_dir, check=True, capture_output=True)
                subprocess.run(["git", "config", "user.email", "r1lab@bios-tool.local"], cwd=temp_dir, check=True, capture_output=True)
                subprocess.run(["git", "checkout", "-b", branch], cwd=temp_dir, check=True, capture_output=True)
                subprocess.run(["git", "add", "."], cwd=temp_dir, check=True, capture_output=True)
                
                commit_msg = f"AutoPatch Cloud Sync: {len(manifest)} scripts updated"
                subprocess.run(["git", "commit", "-m", commit_msg], cwd=temp_dir, check=True, capture_output=True)

                auth_url = f"https://x-access-token:{token}@github.com/{repo_owner}/{repo_name}.git"
                res = subprocess.run(
                    f'git -c credential.helper= push -u "{auth_url}" {branch} --force',
                    shell=True, capture_output=True, text=True, cwd=temp_dir
                )

                if res.returncode == 0:
                    self.status_var.set(f"Successfully deployed {len(manifest)} patches to GitHub!")
                    messagebox.showinfo(
                        "Cloud Deploy Success",
                        f"AutoPatch scripts and manifest successfully pushed to:\nhttps://github.com/{repo_owner}/{repo_name}\n\nAll client machines can now access these patches instantly!"
                    )
                else:
                    self.status_var.set(f"Push failed with code {res.returncode}")
                    messagebox.showerror("Push Error", f"Git output:\n{res.stdout}\n{res.stderr}")

            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

        except Exception as e:
            self.status_var.set(f"Push error: {e}")
            messagebox.showerror("Error", f"Failed to push to GitHub:\n{e}")


if __name__ == "__main__":
    app = AutoPatchManagerGUI()
    app.mainloop()

