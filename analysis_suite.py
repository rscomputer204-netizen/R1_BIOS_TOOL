import os
import subprocess
import threading
import sys
from pathlib import Path
from path_utils import get_app_root, get_python_cmd, get_subprocess_env

class AnalysisSuite:
    """
    Adapter class to run Platomav's analysis tools (MEA, MCE, MCS, RSD).
    """

    @staticmethod
    def _run_script(script_path: str, file_path: str, terminal_callback, extra_args=None, use_platomav_flags=True):
        """Generic script runner with support for console suppression and Platomav flags."""
        if not os.path.exists(script_path):
            if terminal_callback:
                terminal_callback(f"[ERROR] Tool script not found: {script_path}")
            return False

        # Build command
        python_exe = get_python_cmd()
        cmd = [python_exe, script_path]
        
        if file_path:
            cmd.append(file_path)
            
        if use_platomav_flags:
            cmd.extend(["-exit", "-skip", "-duc", "-dcm"])
            
        if extra_args:
            cmd.extend(extra_args)

        try:
            # Creation flags to hide the console window on Windows
            creationflags = 0
            if os.name == 'nt':
                creationflags = 0x08000000 # CREATE_NO_WINDOW

            # Use stdin=PIPE to allow sending newlines to bypass prompts
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                encoding='utf-8',
                errors='replace',
                creationflags=creationflags,
                env=get_subprocess_env()
            )

            # Send a newline immediately to bypass any "Press Enter to continue" prompts
            if process.stdin:
                try:
                    process.stdin.write('\n')
                    process.stdin.flush()
                except:
                    pass

            # Read output line by line, suppressing update notifications
            suppress_sep = False
            for line in process.stdout:
                line_str = line.rstrip()
                line_l = line_str.lower()
                if any(ign in line_l for ign in ["outdated me analyzer", "outdated database", "download the latest from", "github.com/platomav"]):
                    suppress_sep = True
                    continue
                if suppress_sep and (not line_str.strip() or all(c in "═━-=" for c in line_str.strip())):
                    suppress_sep = False
                    continue
                suppress_sep = False
                if terminal_callback:
                    terminal_callback(line_str)

            process.wait()
            return process.returncode == 0
        except Exception as e:
            if terminal_callback:
                terminal_callback(f"[ERROR] Execution failed: {str(e)}")
            return False

    @staticmethod
    def run_me_analyzer(file_path: str, terminal_callback):
        """Runs ME Analyzer (MEA.py)"""
        script = os.path.join(get_app_root(), "ME Analyzer", "MEA.py")
        if terminal_callback:
            terminal_callback("[INFO] Starting ME Analyzer...")
        return AnalysisSuite._run_script(script, file_path, terminal_callback)

    @staticmethod
    def run_security_descriptor_parser(file_path: str, terminal_callback):
        """Runs ME Analyzer with -dfpt flag to show Intel Security Descriptors"""
        script = os.path.join(get_app_root(), "ME Analyzer", "MEA.py")
        if terminal_callback:
            terminal_callback("\n" + "="*50)
            terminal_callback("--- PHASE 1: INTEL SECURITY DESCRIPTORS ---")
            terminal_callback("="*50)
        return AnalysisSuite._run_script(script, file_path, terminal_callback, extra_args=["-dfpt"])

    @staticmethod
    def run_advanced_microcode_info(file_path: str, terminal_callback):
        """Runs MCExtractor with -info flag for security metadata"""
        script = os.path.join(get_app_root(), "MCExtractor", "MCE.py")
        if terminal_callback:
            terminal_callback("\n" + "="*50)
            terminal_callback("--- PHASE 2: ADVANCED MICROCODE SECURITY ---")
            terminal_callback("="*50)
        return AnalysisSuite._run_script(script, file_path, terminal_callback, extra_args=["-info"])

    @staticmethod
    def run_bios_guard_analysis(file_path: str, terminal_callback):
        """Runs Intel BIOS Guard Script Tool"""
        script = os.path.join(get_app_root(), "BGScriptTool", "big_script_tool.py")
        if terminal_callback:
            terminal_callback("\n" + "="*50)
            terminal_callback("--- PHASE 3: INTEL BIOS GUARD ANALYSIS ---")
            terminal_callback("="*50)
        # Note: big_script_tool.py requires -d and does NOT support Platomav flags
        return AnalysisSuite._run_script(script, "", terminal_callback, extra_args=["-d", file_path], use_platomav_flags=False)

    @staticmethod
    def run_microcode_analyzer(file_path: str, terminal_callback):
        """Runs MCExtractor (MCE.py)"""
        script = os.path.join(get_app_root(), "MCExtractor", "MCE.py")
        if terminal_callback:
            terminal_callback("[INFO] Starting Intel Microcode Extractor...")
        return AnalysisSuite._run_script(script, file_path, terminal_callback)

    @staticmethod
    def run_microcode_sub_parser(file_path: str, terminal_callback):
        """Runs MCS-Parser (MCS.py)"""
        script = os.path.join(get_app_root(), "MCS-Parser", "MCS.py")
        if terminal_callback:
            terminal_callback("[INFO] Starting Microcode Sub-component Parser...")
        return AnalysisSuite._run_script(script, file_path, terminal_callback)
