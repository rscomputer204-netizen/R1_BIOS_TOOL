"""
Error Management System
Provides centralized, structured JSON logging and interactive Crash Diagnostics.
"""
import os
import json
import zipfile
from shutil import copy2
from pathlib import Path
from datetime import datetime
from PySide6.QtCore import QObject, Signal, Qt, QMetaObject, Q_ARG, Q_RETURN_ARG
from path_utils import get_app_root

class BiosError(Exception):
    """Custom exception for controlled BIOS manipulation failures."""
    def __init__(self, message, error_code="GENERIC", fatal=False):
        super().__init__(message)
        self.error_code = error_code
        self.fatal = fatal

class ErrorManager(QObject):
    def __init__(self, main_ui=None):
        super().__init__()
        self.main_ui = main_ui
        self.root_dir = Path(get_app_root())
        self.logs_dir = self.root_dir / "TESTING_AREA"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.json_log_path = self.logs_dir / "fit_errors_solutions.json"
        
        # We will keep max 20 crash reports
        self.crash_reports_dir = self.root_dir / "CRASH_REPORTS"
        self.crash_reports_dir.mkdir(exist_ok=True)

    def log_json_error(self, module: str, action: str, details: str, is_fatal: bool):
        """Append error to JSON database."""
        record = {
            "timestamp": datetime.now().isoformat(),
            "module": module,
            "action": action,
            "fatal": is_fatal,
            "details": details
        }
        
        db = []
        if self.json_log_path.exists():
            try:
                with open(self.json_log_path, "r", encoding="utf-8") as f:
                    db = json.load(f)
            except Exception:
                pass
        
        db.append(record)
        with open(self.json_log_path, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=4, ensure_ascii=False)

    def trigger_ui_prompt(self, title: str, message: str, allow_custom_fit: bool = False) -> str:
        """
        Signals the UI to open a blocking error prompt.
        If UI is not available, falls back to terminal print.
        """
        if not self.main_ui:
            return "abort"
        
        # Use simple invokeMethod with Blocking connection to pause thread and wait for UI.
        # We can't easily return strings via Q_RETURN_ARG in python, so we invoke a method 
        # that returns a simple string.
        res = ""
        try:
            # Workaround for getting return value from UI across threads:
            self.main_ui.last_error_choice = "abort"
            QMetaObject.invokeMethod(self.main_ui, "show_error_prompt_sync",
                Qt.BlockingQueuedConnection,
                Q_ARG(str, title),
                Q_ARG(str, message),
                Q_ARG(bool, allow_custom_fit)
            )
            return getattr(self.main_ui, "last_error_choice", "abort")
        except Exception as e:
            print(f"Error invoking UI prompt: {e}")
            return "abort"

    def manage_error(self, module: str, action: str, error_msg: str, is_fatal: bool, bios_path: str = None) -> str:
        """
        Central handler for errors. Logs them, decides on auto-recovery or UI prompt, 
        and generates crash reports if fatal.
        Returns user choice: "retry", "ignore", "abort"
        """
        # 1. Log the error structurally
        self.log_json_error(module, action, error_msg, is_fatal)
        
        allow_custom_fit = is_fatal and ("FIT" in module.upper() or "DECOMPILE" in action.upper() or "BUILD" in action.upper() or "FIT" in error_msg.upper())
        
        if is_fatal:
            # Generate Crash ZIP
            crash_zip = self.generate_crash_report(error_msg, bios_path)
            diag_msg = (
                f"<h3 style='color: #ff3131; margin-bottom: 5px;'>[Module]: {module}</h3>"
                f"<div style='background-color: #000; padding: 10px; border: 1px solid #ff3131; font-family: monospace; white-space: pre-wrap; font-size: 14px;'>"
                f"{error_msg}"
                f"</div><br>"
                f"<b>Crash diagnostics saved to:</b><br><span style='color: #00f3ff;'>{Path(crash_zip).name}</span>"
            )
            return self.trigger_ui_prompt("CRITICAL PIPELINE ERROR", diag_msg, allow_custom_fit=allow_custom_fit)
        else:
            # Standard error that might be ignored or retried
            msg = (
                f"<h3 style='color: #ffaa00; margin-bottom: 5px;'>[Module]: {module}</h3>"
                f"<div style='background-color: #000; padding: 10px; border: 1px solid #ffaa00; font-family: monospace; white-space: pre-wrap; font-size: 14px;'>"
                f"{error_msg}"
                f"</div><br>"
                f"<b>Do you want to retry, ignore and continue, or abort?</b>"
            )
            return self.trigger_ui_prompt(f"Error ({module})", msg)

    def generate_crash_report(self, main_error: str, bios_path: str) -> str:
        """Create a zip file containing the corrupt bios, FIT logs, and metadata."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_name = self.crash_reports_dir / f"CRASH_{timestamp}.zip"
        
        # Prune old crash reports to save space
        self._prune_crash_reports(max_count=20)
        
        workspace = self.root_dir / "FIT_WORKSPACE"
        fit_log = workspace / "fit.log"
        xml_file = workspace / "config.xml"
        
        try:
            with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Add main error description
                zf.writestr("CRASH_INFO.txt", f"Time: {timestamp}\nError: {main_error}\nBios Path: {bios_path}")
                
                if fit_log.exists():
                    zf.write(fit_log, "fit.log")
                if xml_file.exists():
                    zf.write(xml_file, "config.xml")
                
                # Copy the BIOS itself if valid path
                if bios_path and Path(bios_path).exists():
                    zf.write(bios_path, f"Subject_BIOS_{Path(bios_path).name}")
                    
                # Copy the JSON error DB for context
                if self.json_log_path.exists():
                    zf.write(self.json_log_path, self.json_log_path.name)
            
            return str(zip_name)
        except Exception as e:
            print(f"Error creating crash report: {e}")
            return "N/A"

    def _prune_crash_reports(self, max_count: int):
        """Delete oldest crash reports if we exceed the max count."""
        reports = list(self.crash_reports_dir.glob("*.zip"))
        if len(reports) >= max_count:
            # Sort by modification time, oldest first
            reports.sort(key=lambda p: p.stat().st_mtime)
            # Delete the oldest ones
            to_delete = len(reports) - max_count + 1
            for p in reports[:to_delete]:
                try:
                    p.unlink()
                except Exception:
                    pass

