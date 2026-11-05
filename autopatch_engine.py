"""
R1 BIOS TOOL — AUTOPATCH ENGINE
==============================
Handles loading patch catalogs, filtering by detected brand/model, verifying compatibility,
and safely applying binary patches.
"""

import os
import sys
import json
import importlib.util
import urllib.request
import urllib.error
import shutil
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_SCRIPTS_DIR = os.path.join(BASE_DIR, "AutoPatch_Scripts")
LOCAL_MANIFEST = os.path.join(LOCAL_SCRIPTS_DIR, "manifest.json")
CACHE_DIR = os.path.join(BASE_DIR, "data", "autopatch")
REMOTE_MANIFEST_URL = "https://raw.githubusercontent.com/rscomputer204-netizen/R1_AutoPatch_Database/main/manifest.json"
REMOTE_RAW_BASE = "https://raw.githubusercontent.com/rscomputer204-netizen/R1_AutoPatch_Database/main/"


class AutoPatchEngine:
    def __init__(self):
        os.makedirs(CACHE_DIR, exist_ok=True)
        self.patches = []
        self.load_manifest()

    def load_manifest(self) -> list:
        """Loads manifest from local AutoPatch_Scripts or cached copy."""
        # 1. Prefer workspace AutoPatch_Scripts if present
        if os.path.exists(LOCAL_MANIFEST):
            try:
                with open(LOCAL_MANIFEST, "r", encoding="utf-8") as f:
                    self.patches = json.load(f)
                    return self.patches
            except Exception as e:
                print(f"[AutoPatch] Error reading local manifest: {e}")

        # 2. Check local cache
        cached_file = os.path.join(CACHE_DIR, "manifest.json")
        if os.path.exists(cached_file):
            try:
                with open(cached_file, "r", encoding="utf-8") as f:
                    self.patches = json.load(f)
                    return self.patches
            except Exception as e:
                print(f"[AutoPatch] Error reading cached manifest: {e}")

        self.patches = []
        return self.patches

    def sync_from_github(self) -> tuple[bool, str]:
        """Fetches latest manifest.json from GitHub repository."""
        try:
            req = urllib.request.Request(
                REMOTE_MANIFEST_URL,
                headers={"User-Agent": "R1-BIOS-TOOL-AutoPatch"}
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                if response.status == 200:
                    data = response.read().decode("utf-8")
                    new_manifest = json.loads(data)
                    
                    # Save to cache
                    cached_file = os.path.join(CACHE_DIR, "manifest.json")
                    with open(cached_file, "w", encoding="utf-8") as f:
                        f.write(data)

                    # Also update local scripts manifest if working in dev tree
                    if os.path.exists(LOCAL_SCRIPTS_DIR):
                        with open(LOCAL_MANIFEST, "w", encoding="utf-8") as f:
                            f.write(data)

                    self.patches = new_manifest
                    return True, f"Successfully synchronized {len(new_manifest)} patches from GitHub!"
        except Exception as e:
            return False, f"Could not sync with GitHub: {e}"

        return False, "Failed to download manifest."

    def detect_brand(self, file_path_or_bytes, dmi_hint: dict = None) -> tuple[str, str]:
        """
        Detects manufacturer brand and model.
        Returns (brand, model).
        """
        # 1. Check DMI hint if provided
        if dmi_hint and isinstance(dmi_hint, dict):
            brand = dmi_hint.get("Brand") or dmi_hint.get("brand")
            model = dmi_hint.get("Model") or dmi_hint.get("model") or ""
            if brand and brand.upper() not in ("UNKNOWN", "N/A", ""):
                return brand.upper(), model

        # 2. Inspect raw bytes for signatures
        try:
            if isinstance(file_path_or_bytes, str):
                if not os.path.exists(file_path_or_bytes):
                    return "UNKNOWN", ""
                with open(file_path_or_bytes, "rb") as f:
                    # Read sample chunks (first 2MB, last 2MB)
                    header = f.read(2 * 1024 * 1024)
                    f.seek(max(0, os.path.getsize(file_path_or_bytes) - 2 * 1024 * 1024))
                    footer = f.read()
                    data = header + footer
            else:
                data = bytes(file_path_or_bytes)

            data_str = data.decode("latin-1", errors="ignore")

            # Check known signatures
            if "DELL" in data_str or "Dell Inc." in data_str or "Alienware" in data_str:
                return "DELL", ""
            if "LENOVO" in data_str or "ThinkPad" in data_str or "IdeaPad" in data_str:
                return "LENOVO", ""
            if "Hewlett-Packard" in data_str or "HP Inc." in data_str or "ProBook" in data_str or "EliteBook" in data_str:
                return "HP", ""
            if "ASUSTeK" in data_str or "ASUS" in data_str or "ROG STRIX" in data_str:
                return "ASUS", ""
            if "Acer" in data_str or "Aspire" in data_str or "Predator" in data_str:
                return "ACER", ""
            if "Apple Inc." in data_str or "MacBook" in data_str:
                return "APPLE", ""

        except Exception as e:
            print(f"[AutoPatch] Brand detection error: {e}")

        return "UNKNOWN", ""

    def get_patch_dest_path(self, patch_info: dict) -> str:
        """Returns the local client cache path for the given patch script."""
        script_rel = patch_info.get("script_file", "")
        return os.path.join(CACHE_DIR, script_rel.replace("/", os.sep))

    def is_patch_downloaded(self, patch_info: dict) -> bool:
        """Returns True if the patch script is already downloaded locally."""
        dest = self.get_patch_dest_path(patch_info)
        return os.path.exists(dest) and os.path.getsize(dest) > 0

    def get_patch_download_url(self, patch_info: dict) -> str:
        """Returns the public raw GitHub download URL for the patch script."""
        script_rel = patch_info.get("script_file", "").lstrip("/")
        return REMOTE_RAW_BASE + script_rel

    def get_downloaded_count(self) -> int:
        """Returns the total number of downloaded patches in local cache."""
        return sum(1 for p in self.patches if self.is_patch_downloaded(p))

    def get_filtered_patches(self, brand: str = None, search_query: str = None, filter_mode: str = "ALL") -> list:
        """
        Returns patches filtered by brand, search query, and download status.
        filter_mode can be 'ALL', 'DOWNLOADED_ONLY', or 'CLOUD_ONLY'.
        """
        results = []
        brand = (brand or "").strip().upper()
        query = (search_query or "").strip().lower()

        for p in self.patches:
            # Check download status filter
            is_dl = self.is_patch_downloaded(p)
            if filter_mode == "DOWNLOADED_ONLY" and not is_dl:
                continue
            elif filter_mode == "CLOUD_ONLY" and is_dl:
                continue

            p_brand = p.get("brand", "").upper()
            
            # Brand filter: include exact match or UNIVERSAL
            if brand and brand not in ("ALL", "UNKNOWN", ""):
                if p_brand != brand and p_brand != "UNIVERSAL":
                    continue

            # Query filter (matches title, model, board_code, symptom, description)
            if query:
                haystack = f"{p.get('title', '')} {p.get('model', '')} {p.get('board_code', '')} {p.get('symptom', '')} {p.get('description', '')}".lower()
                if query not in haystack:
                    continue

            results.append(p)

        return results

    def _load_script_module(self, patch_info: dict):
        """Dynamically imports the patch script module, downloading if needed."""
        script_rel = patch_info.get("script_file")
        if not script_rel:
            raise FileNotFoundError("Patch metadata does not specify script_file.")

        # 1. Check local cache (downloaded patches)
        script_path = self.get_patch_dest_path(patch_info)

        # 2. If not in cache, download from GitHub or fallback to dev workspace
        if not (os.path.exists(script_path) and os.path.getsize(script_path) > 0):
            os.makedirs(os.path.dirname(script_path), exist_ok=True)
            url = self.get_patch_download_url(patch_info)
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "R1-BIOS-TOOL"})
                with urllib.request.urlopen(req, timeout=10) as resp, open(script_path, "wb") as f:
                    f.write(resp.read())
            except Exception as e:
                dev_path = os.path.join(LOCAL_SCRIPTS_DIR, script_rel.replace("/", os.sep))
                if os.path.exists(dev_path):
                    script_path = dev_path
                else:
                    raise FileNotFoundError(f"Failed to fetch script from cloud: {e}")

        module_name = f"autopatch_{patch_info.get('id', 'module')}"
        spec = importlib.util.spec_from_file_location(module_name, script_path)
        if not spec or not spec.loader:
            raise ImportError(f"Cannot load spec from {script_path}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def delete_patch(self, patch_info: dict) -> bool:
        """Deletes the downloaded patch file from local cache."""
        dest = self.get_patch_dest_path(patch_info)
        if os.path.exists(dest):
            try:
                os.remove(dest)
                return True
            except Exception:
                return False
        return False

    def verify_patch(self, patch_info: dict, bios_data: bytearray) -> tuple[bool, str]:
        """Executes the script's verify() function ONLY if already downloaded."""
        if not self.is_patch_downloaded(patch_info):
            return False, "NOT_DOWNLOADED"
        try:
            mod = self._load_script_module(patch_info)
            if hasattr(mod, "verify"):
                return mod.verify(bios_data, patch_info)
            return True, "Script does not require pre-verification."
        except Exception as e:
            return False, f"Verification error: {e}"

    def execute_patch(self, patch_info: dict, file_path: str, create_backup: bool = True, output_path: str = None) -> tuple[bool, str, str]:
        """
        Applies patch to bios file.
        Returns (success, output_path, message).
        """
        if not os.path.exists(file_path):
            return False, "", "Input BIOS file not found!"

        try:
            with open(file_path, "rb") as f:
                data = bytearray(f.read())
        except Exception as e:
            return False, "", f"Failed to read file: {e}"

        # 1. Verify
        ok, msg = self.verify_patch(patch_info, data)
        if not ok:
            return False, "", f"Safety Verification Blocked:\n{msg}"

        # 2. Apply patch
        try:
            mod = self._load_script_module(patch_info)
            if not hasattr(mod, "apply_patch"):
                return False, "", "Script is missing apply_patch() function!"

            patch_ok, patched_data, patch_msg = mod.apply_patch(data, patch_info)
            if not patch_ok:
                return False, "", f"Patch execution failed: {patch_msg}"
        except Exception as e:
            return False, "", f"Script runtime exception: {e}"

        # 3. Determine output path
        folder = os.path.dirname(file_path)
        base, ext = os.path.splitext(os.path.basename(file_path))
        patch_tag = patch_info.get("id", "patched")
        
        if not output_path:
            output_path = os.path.join(folder, f"{base}_{patch_tag}_PATCHED{ext}")

        # 4. Optional original backup
        if create_backup:
            bak_path = os.path.join(folder, f"{base}_ORIGINAL_BACKUP{ext}")
            if not os.path.exists(bak_path):
                try:
                    shutil.copy2(file_path, bak_path)
                except Exception:
                    pass

        # 5. Save patched binary
        try:
            with open(output_path, "wb") as f:
                f.write(patched_data)
        except Exception as e:
            return False, "", f"Failed to write patched file: {e}"

        # 6. Reveal in Windows Explorer
        try:
            if os.name == "nt":
                subprocess.Popen(f'explorer /select,"{os.path.abspath(output_path)}"')
        except Exception:
            pass

        return True, output_path, patch_msg

