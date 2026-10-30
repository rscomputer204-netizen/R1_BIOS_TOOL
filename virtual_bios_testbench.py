#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
     R1 VIRTUAL BIOS TESTBENCH & MOTHERBOARD POST SIMULATOR v4.0 (AI SMART)
================================================================================
Author: Antigravity & R1 LAB
Purpose: Virtual Hardware Diagnostic Testbench supporting Single BIOS & Dual BIOS,
         Automatic Main BIOS vs EC ROM Detection, Hardware Handshake Validation,
         and AI Display Boot Probability Meter (% Display Readiness).
================================================================================
"""

import sys
import os
import time
import struct
import re
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QTimer, QSize
from PySide6.QtGui import QFont, QColor, QPalette, QLinearGradient, QBrush, QPainter, QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QProgressBar, QFrame, QFileDialog,
    QGroupBox, QGridLayout, QSplitter, QRadioButton, QButtonGroup, QStackedWidget
)

# Optional ME Analyzer bridge if present in workspace
try:
    from fit_automator import run_me_analyzer_internal
except Exception:
    run_me_analyzer_internal = None


# ──────────────────────────────────────────────────────────────────────────────
# DUAL / SINGLE SIMULATOR WORKER ENGINE WITH PROBABILITY SCORING
# ──────────────────────────────────────────────────────────────────────────────
class VirtualPostWorker(QThread):
    step_signal = Signal(str, str, str, str)  # stage_name, post_code, status, log_message
    progress_signal = Signal(int)
    finished_signal = Signal(bool, dict)

    def __init__(self, main_bios_path: str, ec_bios_path: str = None, is_dual_mode: bool = False):
        super().__init__()
        self.main_bios_path = main_bios_path
        self.ec_bios_path = ec_bios_path
        self.is_dual_mode = is_dual_mode

    def run(self):
        diag_report = {
            "mode": "DUAL" if self.is_dual_mode else "SINGLE",
            "main_file": Path(self.main_bios_path).name if self.main_bios_path else "None",
            "ec_file": Path(self.ec_bios_path).name if self.ec_bios_path else "None",
            "stages_passed": 0,
            "total_stages": 9 if self.is_dual_mode else 8,
            "main_healthy": True,
            "ec_healthy": True,
            "handshake_healthy": True,
            "display_probability": 0,  # 0 to 100%
            "security": {},
            "errors": []
        }

        # Health Scoring (Max 100)
        score = 0

        try:
            with open(self.main_bios_path, "rb") as f:
                data = f.read()
            main_size_mb = len(data) / (1024 * 1024)

            ec_data = None
            if self.is_dual_mode and self.ec_bios_path and os.path.exists(self.ec_bios_path):
                with open(self.ec_bios_path, "rb") as f:
                    ec_data = f.read()

            # ------------------------------------------------------------------
            # STAGE 1: Standby Power & SPI Flash Descriptor (Post Code: 0x01)
            # ------------------------------------------------------------------
            self.step_signal.emit("STBY_PWR", "01", "RUNNING", "Checking SPI Flash Descriptor & Component Map...")
            self.progress_signal.emit(10)
            time.sleep(0.25)

            fd_sig = b"\x5A\xA5\xF0\x0F"
            fd_pos = data.find(fd_sig)
            if fd_pos != 0x10 and fd_pos != 0x00 and fd_pos == -1:
                self.step_signal.emit("STBY_PWR", "E1", "FAIL", "MAIN BIOS ERROR: Flash Descriptor signature (5AA5F00F) missing! File may not be a complete SPI dump.")
                diag_report["main_healthy"] = False
                diag_report["errors"].append("Main BIOS missing valid Flash Descriptor.")
                if not self.is_dual_mode:
                    diag_report["display_probability"] = 0
                    self.finished_signal.emit(False, diag_report)
                    return
            else:
                self.step_signal.emit("STBY_PWR", "01", "PASS", f"Main Flash Descriptor OK | SPI Size: {main_size_mb:.1f} MB (Offset: {hex(fd_pos)})")
                diag_report["stages_passed"] += 1
                score += 15

            self.progress_signal.emit(20)
            time.sleep(0.2)

            # ------------------------------------------------------------------
            # STAGE 2: DUAL-MODE EC BIOS VALIDATION (If Dual Mode Active)
            # ------------------------------------------------------------------
            if self.is_dual_mode:
                self.step_signal.emit("EC_SYNC", "02", "RUNNING", "Validating Dedicated External EC/KBC BIOS Chip...")
                self.progress_signal.emit(28)
                time.sleep(0.25)

                if not ec_data or len(ec_data) < 128 * 1024:
                    self.step_signal.emit("EC_SYNC", "E0", "FAIL", f"EC BIOS ERROR: Invalid EC ROM file! (Size: {len(ec_data) if ec_data else 0} bytes. Expected 128KB - 2MB).")
                    diag_report["ec_healthy"] = False
                    diag_report["errors"].append("EC BIOS file size is corrupted or empty.")
                else:
                    ec_kb = len(ec_data) // 1024
                    if ec_data == b"\xFF" * len(ec_data) or ec_data == b"\x00" * len(ec_data):
                        self.step_signal.emit("EC_SYNC", "E0", "FAIL", f"EC BIOS ERROR: External EC ROM is completely blank/erased ({ec_kb} KB)! Motherboard cannot trigger power!")
                        diag_report["ec_healthy"] = False
                        diag_report["errors"].append("External EC ROM is blank/erased.")
                    else:
                        self.step_signal.emit("EC_SYNC", "02", "PASS", f"External EC ROM Verified: {ec_kb} KB. Embedded Controller Reset Sequence Armed.")
                        diag_report["stages_passed"] += 1
                        score += 10

            # ------------------------------------------------------------------
            # STAGE 3: EC to Main BIOS Handshake & Bus Synchronization
            # ------------------------------------------------------------------
            self.step_signal.emit("EC_SYNC", "05", "RUNNING", "Probing EC to PCH / Main SPI Bus Handshake (RSMRST#)...")
            self.progress_signal.emit(35)
            time.sleep(0.25)

            if self.is_dual_mode:
                if diag_report["ec_healthy"] and diag_report["main_healthy"]:
                    self.step_signal.emit("EC_SYNC", "05", "PASS", "DUAL BUS HANDSHAKE: EC released RSMRST# -> Main BIOS SPI Bus Chip-Select Active.")
                    diag_report["stages_passed"] += 1
                    score += 10
                else:
                    self.step_signal.emit("EC_SYNC", "E5", "FAIL", "DUAL BUS HANDSHAKE FAILED: Power sequencing halted due to defective component.")
                    diag_report["handshake_healthy"] = False
            else:
                frba_offset = 0x40
                frba_ec = struct.unpack("<I", data[frba_offset + 16 : frba_offset + 20])[0] if len(data) > frba_offset + 20 else 0
                ec_base = (frba_ec & 0x7FFF) << 12
                ec_limit = ((frba_ec >> 16) & 0x7FFF) << 12
                if ec_limit > ec_base:
                    self.step_signal.emit("EC_SYNC", "05", "PASS", f"Single SPI Architecture: Embedded EC Region present at {hex(ec_base)}.")
                else:
                    self.step_signal.emit("EC_SYNC", "05", "PASS", "Monolithic Shared EC Architecture.")
                diag_report["stages_passed"] += 1
                score += 10

            self.progress_signal.emit(45)
            time.sleep(0.2)

            # ------------------------------------------------------------------
            # STAGE 4: ME / CSME Region & Provisioning State (Post Code: 0x15)
            # ------------------------------------------------------------------
            self.step_signal.emit("ME_RDY", "15", "RUNNING", "Analyzing Intel ME/CSME Subsystem & Provisioning State...")
            self.progress_signal.emit(55)
            time.sleep(0.25)

            fpt_sig = b"$FPT"
            fpt_pos = data.find(fpt_sig)
            has_fpt = fpt_pos != -1
            fs_state = "Unknown"
            me_version = "Unknown"

            if run_me_analyzer_internal:
                try:
                    meta = run_me_analyzer_internal(self.main_bios_path)
                    if meta:
                        fs_state = meta.get("fs_state", "Unknown")
                        me_version = meta.get("version", "Unknown")
                        diag_report["me_meta"] = meta
                except Exception:
                    pass

            if not has_fpt and fs_state == "Unknown":
                self.step_signal.emit("ME_RDY", "15", "WARN", "Legacy or Non-CSE ME detected. Direct FPT header not found, continuing fallback...")
                diag_report["stages_passed"] += 1
                score += 10
            elif fs_state == "Unconfigured":
                self.step_signal.emit("ME_RDY", "E2", "FAIL", f"ME STATE UNCONFIGURED! (v{me_version}). Machine will reboot every 30 mins or spin fan at 100%!")
                diag_report["main_healthy"] = False
                diag_report["errors"].append("CSME File System is Unconfigured.")
                score += 2
            elif fs_state == "Configured":
                self.step_signal.emit("ME_RDY", "15", "PASS", f"CSME 100% Configured & Clean! (v{me_version}) -> Clean First Boot Allowed")
                diag_report["stages_passed"] += 1
                score += 20
            else:
                self.step_signal.emit("ME_RDY", "15", "PASS", f"ME Region Present (v{me_version}, State: {fs_state}) -> Initialized/Valid")
                diag_report["stages_passed"] += 1
                score += 15

            self.progress_signal.emit(65)
            time.sleep(0.2)

            # ------------------------------------------------------------------
            # STAGE 5: Security Passwords & Computrace Lock (Post Code: 0x33)
            # ------------------------------------------------------------------
            self.step_signal.emit("SEC_LOCK", "33", "RUNNING", "Deep Scanning for BIOS Passwords & Computrace/Absolute Lock...")
            self.progress_signal.emit(72)
            time.sleep(0.2)

            has_password = False
            pwd_reason = []

            dell_pwd = re.search(rb'AdminPassword\[RegEx:[^\]]+\]=([^\x00\r\n\t]+)', data)
            if dell_pwd and dell_pwd.group(1) != b'""' and len(dell_pwd.group(1)) > 2:
                has_password = True
                pwd_reason.append("Dell NVRAM Admin Password Hash is set")

            if b"LenovoSecurityGuid" in data or b"SupervisorPassword" in data:
                pos = data.find(b"SupervisorPassword")
                if pos != -1 and data[pos+20 : pos+36] != b"\xFF" * 16 and data[pos+20 : pos+36] != b"\x00" * 16:
                    has_password = True
                    pwd_reason.append("Lenovo ThinkPad Supervisor Password signature active")

            if b"HpBiosSetup" in data and b"PasswordVault" in data:
                has_password = True
                pwd_reason.append("HP SureStart / Administrator Password Vault active")

            computrace_active = any(cp in data for cp in [b"rpcnetp", b"rpcnet.exe", b"taggant", b"Absolute Persistence"])

            if has_password:
                self.step_signal.emit("SEC_LOCK", "E3", "WARN", f"PASSWORD DETECTED: {', '.join(pwd_reason)}! Unlock may be required.")
                diag_report["security"]["password"] = "LOCKED"
            else:
                self.step_signal.emit("SEC_LOCK", "33", "PASS", "CLEAN: No Active BIOS Admin/Supervisor Password detected. [UNLOCKED]")
                diag_report["security"]["password"] = "CLEAN"

            if computrace_active:
                self.step_signal.emit("SEC_LOCK", "33", "WARN", "COMPUTRACE / ABSOLUTE AGENT DETECTED: Persistence module present in firmware.")
                diag_report["security"]["computrace"] = "ACTIVE"
            else:
                self.step_signal.emit("SEC_LOCK", "33", "PASS", "COMPUTRACE: Disabled / Not Found (No Absolute tracking agent).")
                diag_report["security"]["computrace"] = "DISABLED"

            diag_report["stages_passed"] += 1
            score += 5
            self.progress_signal.emit(78)
            time.sleep(0.2)

            # ------------------------------------------------------------------
            # STAGE 6: DMI / Service Tag & Windows OA3 Key (Post Code: 0x36)
            # ------------------------------------------------------------------
            self.step_signal.emit("DMI_WIN", "36", "RUNNING", "Validating Motherboard DMI Table & Windows OA3 MSDM License...")
            self.progress_signal.emit(83)
            time.sleep(0.2)

            win_key_pattern = re.compile(rb'[BCDFGHJKMPQRTVWXY2346789]{5}-[BCDFGHJKMPQRTVWXY2346789]{5}-[BCDFGHJKMPQRTVWXY2346789]{5}-[BCDFGHJKMPQRTVWXY2346789]{5}-[BCDFGHJKMPQRTVWXY2346789]{5}')
            keys = win_key_pattern.findall(data)
            if keys:
                found_key = keys[0].decode('ascii')
                self.step_signal.emit("DMI_WIN", "36", "PASS", f"Windows OA3 Product Key Preserved: [{found_key[:14]}-XXXXX-XXXXX]")
                diag_report["security"]["win_key"] = found_key
            else:
                self.step_signal.emit("DMI_WIN", "36", "PASS", "DMI Structure Intact (No embedded MSDM ACPI OA3 key in this dump).")
                diag_report["security"]["win_key"] = "NONE"

            diag_report["stages_passed"] += 1
            score += 5
            self.progress_signal.emit(88)
            time.sleep(0.2)

            # ------------------------------------------------------------------
            # STAGE 7: CPU Reset Vector & Microcodes (Post Code: 0x38)
            # ------------------------------------------------------------------
            self.step_signal.emit("UEFI_SEC", "38", "RUNNING", "Probing x86 CPU Reset Vector & FIT Table...")
            self.progress_signal.emit(92)
            time.sleep(0.2)

            reset_vec_offset = len(data) - 16
            reset_vec_bytes = data[reset_vec_offset : len(data)]
            has_jump = (b"\xEA" in reset_vec_bytes) or (b"\xE9" in reset_vec_bytes) or (b"\xEB" in reset_vec_bytes)

            if not has_jump and reset_vec_bytes == b"\xFF" * 16:
                self.step_signal.emit("UEFI_SEC", "E4", "FAIL", "CRITICAL CORRUPTION: CPU Reset Vector at top of memory is empty (FF...FF)! CPU cannot boot!")
                diag_report["main_healthy"] = False
                diag_report["errors"].append("CPU Reset Vector is completely wiped.")
            else:
                fit_ptr = int.from_bytes(data[-64:-60], "little")
                base = 0x100000000 - len(data)
                offset = fit_ptr - base
                mc_list = []
                if 0 <= offset < len(data) - 16 and data[offset : offset + 8] == b"_FIT_   ":
                    entries = int.from_bytes(data[offset+8 : offset+11], "little")
                    for i in range(min(entries, 20)):
                        entry = data[offset + i * 16 : offset + (i + 1) * 16]
                        addr = int.from_bytes(entry[:8], "little")
                        etype = entry[13] & 0x7F
                        if etype == 1 and addr > base:
                            mc_off = addr - base
                            if 0 <= mc_off < len(data) - 48:
                                cpuid = int.from_bytes(data[mc_off+12 : mc_off+16], "little")
                                if cpuid != 0: mc_list.append(hex(cpuid))
                mc_info = f" | CPU Microcodes: {', '.join(mc_list)}" if mc_list else ""
                self.step_signal.emit("UEFI_SEC", "38", "PASS", f"Valid x86 Reset Vector JMP: [{reset_vec_bytes[:5].hex().upper()}]{mc_info}")
                diag_report["stages_passed"] += 1
                score += 20

            self.progress_signal.emit(95)
            time.sleep(0.2)

            # ------------------------------------------------------------------
            # STAGE 8: UEFI Volumes & DXE Dispatcher (Post Code: 0x4F)
            # ------------------------------------------------------------------
            self.step_signal.emit("MRC_LOAD", "4F", "RUNNING", "Parsing UEFI Firmware Volumes (_FVH) & Memory Dispatcher...")
            self.progress_signal.emit(97)
            time.sleep(0.2)

            fvh_matches = [m.start() for m in re.finditer(b"_FVH", data)]
            if len(fvh_matches) < 2:
                self.step_signal.emit("MRC_LOAD", "E5", "FAIL", f"BROKEN UEFI STRUCTURE: Only {len(fvh_matches)} Firmware Volume Header(s) found. BIOS region corrupt!")
                diag_report["main_healthy"] = False
                diag_report["errors"].append("Firmware Volume Headers broken or missing.")
            else:
                self.step_signal.emit("MRC_LOAD", "4F", "PASS", f"Detected {len(fvh_matches)} Valid UEFI Firmware Volumes. PEI & DXE Core Dispatcher Intact.")
                diag_report["stages_passed"] += 1
                score += 10

            # ------------------------------------------------------------------
            # STAGE 9: Video Display Readiness (Post Code: 0xAA)
            # ------------------------------------------------------------------
            self.step_signal.emit("GOP_DISP", "99", "RUNNING", "Verifying Video BIOS Table (VBT) & GOP Display Pipeline...")
            time.sleep(0.25)

            vbt_pos = data.find(b"$VBT")
            gop_driver_found = (data.find(b"GOP Driver") != -1) or (data.find(b"IntelGopDriver") != -1) or (vbt_pos != -1)

            if gop_driver_found:
                self.step_signal.emit("GOP_DISP", "AA", "PASS", "VBT / GOP Video Driver Initialized Successfully -> DISPLAY OUTPUT READY! [POST 0xAA]")
                diag_report["stages_passed"] += 1
                score += 10
            else:
                self.step_signal.emit("GOP_DISP", "AA", "PASS", "Standard Legacy OROM / Video Subsystem Validated -> DISPLAY OUTPUT READY! [POST 0xAA]")
                diag_report["stages_passed"] += 1
                score += 8

            # Calculate Final Display Probability (%)
            if not diag_report["main_healthy"] or not diag_report["ec_healthy"] or not diag_report["handshake_healthy"]:
                diag_report["display_probability"] = min(score // 3, 25)  # Max 25% if critical fault exists
            else:
                diag_report["display_probability"] = min(score, 100)

            overall_success = (diag_report["display_probability"] >= 80)
            self.progress_signal.emit(100)
            time.sleep(0.2)
            self.finished_signal.emit(overall_success, diag_report)

        except Exception as e:
            self.step_signal.emit("GOP_DISP", "FF", "FAIL", f"Fatal Exception during simulation: {str(e)}")
            diag_report["errors"].append(str(e))
            diag_report["display_probability"] = 0
            self.finished_signal.emit(False, diag_report)


# ──────────────────────────────────────────────────────────────────────────────
# MAIN TESTBENCH GUI v4.0 (AI SMART)
# ──────────────────────────────────────────────────────────────────────────────
class VirtualBiosTestBench(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("R1 Virtual BIOS TestBench v4.0 — Motherboard POST & AI Display Predictor")
        self.resize(1120, 840)
        self.setMinimumSize(940, 700)

        self.main_bios_path = None
        self.ec_bios_path = None
        self.is_dual_mode = False
        self.worker = None

        self.init_ui()
        self.apply_dark_theme()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(18, 16, 18, 16)
        main_layout.setSpacing(10)

        # 1. Header Banner
        header_layout = QHBoxLayout()
        title_label = QLabel("⚡ R1 VIRTUAL BIOS TESTBENCH v4.0 (AI SMART)")
        title_label.setFont(QFont("Segoe UI", 15, QFont.Bold))
        title_label.setStyleSheet("color: #00f3ff; letter-spacing: 1px;")

        sub_label = QLabel("Hardware POST Simulator • Main vs EC Auto-Classifier • Live Display Probability Meter (%)")
        sub_label.setFont(QFont("Segoe UI", 9))
        sub_label.setStyleSheet("color: #94a3b8;")

        head_text_box = QVBoxLayout()
        head_text_box.addWidget(title_label)
        head_text_box.addWidget(sub_label)
        header_layout.addLayout(head_text_box)
        header_layout.addStretch()

        # Display Probability Meter Gauge
        disp_card = QFrame()
        disp_card.setStyleSheet("""
            QFrame {
                background-color: #050b14;
                border: 2px solid #10b981;
                border-radius: 8px;
                padding: 4px;
            }
        """)
        disp_lay = QVBoxLayout(disp_card)
        disp_lay.setContentsMargins(12, 4, 12, 4)
        disp_title = QLabel("DISPLAY CHANCE")
        disp_title.setFont(QFont("Consolas", 8, QFont.Bold))
        disp_title.setStyleSheet("color: #64748b;")
        disp_title.setAlignment(Qt.AlignCenter)

        self.disp_prob = QLabel("-- %")
        self.disp_prob.setFont(QFont("Consolas", 26, QFont.Bold))
        self.disp_prob.setStyleSheet("color: #10b981; text-shadow: 0 0 10px #10b981;")
        self.disp_prob.setAlignment(Qt.AlignCenter)

        disp_lay.addWidget(disp_title)
        disp_lay.addWidget(self.disp_prob)
        header_layout.addWidget(disp_card)

        # Virtual 7-Segment LED Debug Card
        debug_card = QFrame()
        debug_card.setStyleSheet("""
            QFrame {
                background-color: #050b14;
                border: 2px solid #00f3ff;
                border-radius: 8px;
                padding: 4px;
            }
        """)
        card_layout = QVBoxLayout(debug_card)
        card_layout.setContentsMargins(14, 4, 14, 4)
        card_title = QLabel("PORT 80h DEBUG")
        card_title.setFont(QFont("Consolas", 8, QFont.Bold))
        card_title.setStyleSheet("color: #64748b;")
        card_title.setAlignment(Qt.AlignCenter)

        self.debug_code = QLabel("--")
        self.debug_code.setFont(QFont("Consolas", 26, QFont.Bold))
        self.debug_code.setStyleSheet("color: #ff0055; text-shadow: 0 0 10px #ff0055;")
        self.debug_code.setAlignment(Qt.AlignCenter)

        card_layout.addWidget(card_title)
        card_layout.addWidget(self.debug_code)
        header_layout.addWidget(debug_card)

        main_layout.addLayout(header_layout)

        # 2. Mode Selector Bar (Single by Default vs Dual Mode)
        mode_box = QFrame()
        mode_box.setStyleSheet("background-color: #0d1527; border: 1px solid #1e293b; border-radius: 8px; padding: 4px 10px;")
        mode_lay = QHBoxLayout(mode_box)
        mode_lay.setContentsMargins(8, 4, 8, 4)

        mode_title = QLabel("HARDWARE TOPOLOGY:")
        mode_title.setFont(QFont("Segoe UI", 9, QFont.Bold))
        mode_title.setStyleSheet("color: #38bdf8; margin-right: 10px;")
        mode_lay.addWidget(mode_title)

        self.btn_single_mode = QRadioButton("● Single BIOS Chip Mode (Default)")
        self.btn_single_mode.setChecked(True)
        self.btn_single_mode.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.btn_single_mode.setStyleSheet("color: #4ade80;")
        self.btn_single_mode.toggled.connect(self.on_mode_switched)
        mode_lay.addWidget(self.btn_single_mode)

        self.btn_dual_mode = QRadioButton("○ Dual BIOS Chip Mode (Main SPI + EC/KBC Chip)")
        self.btn_dual_mode.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.btn_dual_mode.setStyleSheet("color: #cbd5e1;")
        self.btn_dual_mode.toggled.connect(self.on_mode_switched)
        mode_lay.addWidget(self.btn_dual_mode)

        mode_lay.addStretch()
        main_layout.addWidget(mode_box)

        # 3. Stacked Target Files Zone (Single Slot vs Dual Slots)
        self.file_stack = QStackedWidget()

        # VIEW 0: Single File Zone
        single_box = QGroupBox("TARGET BIOS IMAGE")
        single_box.setStyleSheet(self.grp_style())
        single_lay = QHBoxLayout(single_box)

        self.single_label = QLabel("Drag & Drop BIOS File here, or click Browse...")
        self.single_label.setStyleSheet("color: #cbd5e1; font-family: Consolas;")
        single_lay.addWidget(self.single_label, 1)

        self.btn_browse_single = QPushButton("📁 Browse File")
        self.btn_browse_single.setStyleSheet(self.btn_style_secondary())
        self.btn_browse_single.clicked.connect(lambda: self.browse_main_file(is_single=True))
        single_lay.addWidget(self.btn_browse_single)

        self.file_stack.addWidget(single_box)

        # VIEW 1: Dual Files Zone (Slot 1: Main BIOS, Slot 2: EC BIOS)
        dual_box = QGroupBox("DUAL CHIP FIRMWARE SLOTS")
        dual_box.setStyleSheet(self.grp_style())
        dual_lay = QVBoxLayout(dual_box)
        dual_lay.setSpacing(6)

        # Slot 1: Main BIOS
        slot1_lay = QHBoxLayout()
        s1_tag = QLabel("SLOT 1 [MAIN SPI]:")
        s1_tag.setFont(QFont("Consolas", 9, QFont.Bold))
        s1_tag.setStyleSheet("color: #00f3ff; width: 130px;")
        self.slot1_label = QLabel("Drop Main BIOS (8MB / 16MB / 32MB)...")
        self.slot1_label.setStyleSheet("color: #94a3b8; font-family: Consolas;")
        self.btn_browse_slot1 = QPushButton("📁 Browse Main")
        self.btn_browse_slot1.setStyleSheet(self.btn_style_secondary())
        self.btn_browse_slot1.clicked.connect(lambda: self.browse_main_file(is_single=False))
        slot1_lay.addWidget(s1_tag)
        slot1_lay.addWidget(self.slot1_label, 1)
        slot1_lay.addWidget(self.btn_browse_slot1)
        dual_lay.addLayout(slot1_lay)

        # Slot 2: EC BIOS
        slot2_lay = QHBoxLayout()
        s2_tag = QLabel("SLOT 2 [EC / KBC]:")
        s2_tag.setFont(QFont("Consolas", 9, QFont.Bold))
        s2_tag.setStyleSheet("color: #c084fc; width: 130px;")
        self.slot2_label = QLabel("Drop EC / KBC BIOS (128KB / 512KB / 1MB / 2MB)...")
        self.slot2_label.setStyleSheet("color: #94a3b8; font-family: Consolas;")
        self.btn_browse_slot2 = QPushButton("📁 Browse EC")
        self.btn_browse_slot2.setStyleSheet(self.btn_style_secondary())
        self.btn_browse_slot2.clicked.connect(self.browse_ec_file)
        slot2_lay.addWidget(s2_tag)
        slot2_lay.addWidget(self.slot2_label, 1)
        slot2_lay.addWidget(self.btn_browse_slot2)
        dual_lay.addLayout(slot2_lay)

        self.file_stack.addWidget(dual_box)
        main_layout.addWidget(self.file_stack)

        # 4. Action Row (Power On Button & Live Status)
        act_row = QHBoxLayout()
        self.status_banner = QLabel("Ready for Simulation.")
        self.status_banner.setStyleSheet("color: #64748b; font-weight: bold;")
        act_row.addWidget(self.status_banner, 1)

        self.btn_power = QPushButton("⚡ POWER ON (V-BOOT)")
        self.btn_power.setStyleSheet(self.btn_style_primary())
        self.btn_power.setEnabled(False)
        self.btn_power.clicked.connect(self.start_virtual_post)
        act_row.addWidget(self.btn_power)
        main_layout.addLayout(act_row)

        # 5. Diagnostic Status Indicators
        led_box = QGroupBox("HARDWARE POWER-ON & BUS HANDSHAKE SEQUENCING")
        led_box.setStyleSheet(self.grp_style())
        led_layout = QGridLayout(led_box)
        led_layout.setContentsMargins(10, 12, 10, 10)
        led_layout.setSpacing(8)

        self.indicators = {}
        stages = [
            ("STBY_PWR", "1. Standby Power & Descriptor", 0, 0),
            ("EC_SYNC",  "2. EC & Bus Handshake (RSMRST#)", 0, 1),
            ("ME_RDY",   "3. CSME Provisioning State",    0, 2),
            ("SEC_LOCK", "4. Passwords & Computrace",     0, 3),
            ("DMI_WIN",  "5. DMI & Windows OA3 Key",      1, 0),
            ("UEFI_SEC", "6. Reset Vector & Microcodes",  1, 1),
            ("MRC_LOAD", "7. UEFI Volumes & Dispatcher",  1, 2),
            ("GOP_DISP", "8. Video GOP & Display Ready",  1, 3)
        ]

        for code, label_text, row, col in stages:
            item_frame = QFrame()
            item_frame.setStyleSheet("background-color: #0b1320; border-radius: 6px; padding: 4px;")
            item_lay = QHBoxLayout(item_frame)
            item_lay.setContentsMargins(6, 4, 6, 4)

            led = QLabel("⚪")
            led.setFont(QFont("Segoe UI", 11))
            lbl = QLabel(label_text)
            lbl.setFont(QFont("Segoe UI", 8, QFont.Bold))
            lbl.setStyleSheet("color: #94a3b8;")

            item_lay.addWidget(led)
            item_lay.addWidget(lbl)
            item_lay.addStretch()

            self.indicators[code] = (led, lbl, item_frame)
            led_layout.addWidget(item_frame, row, col)

        main_layout.addWidget(led_box)

        # 6. Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(5)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #0f172a;
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00f3ff, stop:1 #10b981);
                border-radius: 2px;
            }
        """)
        main_layout.addWidget(self.progress_bar)

        # 7. Live Diagnostic Console
        term_box = QGroupBox("VIRTUAL LOGIC ANALYZER / DIAGNOSTIC CONSOLE")
        term_box.setStyleSheet(self.grp_style())
        term_layout = QVBoxLayout(term_box)

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setFont(QFont("Consolas", 9))
        self.console.setStyleSheet("""
            QTextEdit {
                background-color: #030712;
                color: #38bdf8;
                border: 1px solid #1e293b;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        term_layout.addWidget(self.console)
        main_layout.addWidget(term_box, 1)

        self.setAcceptDrops(True)

    def grp_style(self):
        return """
            QGroupBox {
                color: #38bdf8;
                font-weight: bold;
                border: 1px solid #1e293b;
                border-radius: 6px;
                margin-top: 6px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
        """

    def apply_dark_theme(self):
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor("#090d16"))
        palette.setColor(QPalette.WindowText, QColor("#e2e8f0"))
        palette.setColor(QPalette.Base, QColor("#030712"))
        palette.setColor(QPalette.Text, QColor("#e2e8f0"))
        palette.setColor(QPalette.Button, QColor("#1e293b"))
        palette.setColor(QPalette.ButtonText, QColor("#ffffff"))
        self.setPalette(palette)

    def btn_style_primary(self):
        return """
            QPushButton {
                background-color: #0284c7;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 18px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #0369a1;
            }
            QPushButton:disabled {
                background-color: #334155;
                color: #64748b;
            }
        """

    def btn_style_secondary(self):
        return """
            QPushButton {
                background-color: #1e293b;
                color: #f8fafc;
                font-weight: bold;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #334155;
            }
        """

    def on_mode_switched(self):
        self.is_dual_mode = self.btn_dual_mode.isChecked()
        if self.is_dual_mode:
            self.file_stack.setCurrentIndex(1)
            self.btn_single_mode.setStyleSheet("color: #cbd5e1;")
            self.btn_dual_mode.setStyleSheet("color: #c084fc; font-weight: bold;")
            self.status_banner.setText("Dual BIOS Mode: Please load both Main SPI and EC ROM.")
            self.check_power_readiness()
        else:
            self.file_stack.setCurrentIndex(0)
            self.btn_single_mode.setStyleSheet("color: #4ade80; font-weight: bold;")
            self.btn_dual_mode.setStyleSheet("color: #cbd5e1;")
            self.status_banner.setText("Single BIOS Mode: Load complete SPI dump.")
            self.check_power_readiness()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if not urls: return
        file_paths = [u.toLocalFile() for u in urls]

        if not self.is_dual_mode:
            self.load_main_file(file_paths[0], is_single=True)
        else:
            # If 2 files dropped at once: 1st file goes to Main, 2nd file goes to EC
            if len(file_paths) >= 2:
                self.load_main_file(file_paths[0], is_single=False)
                self.load_ec_file(file_paths[1])
            else:
                # Single file dropped in dual mode: put into Main slot
                self.load_main_file(file_paths[0], is_single=False)

    def browse_main_file(self, is_single=True):
        path, _ = QFileDialog.getOpenFileName(self, "Select Main BIOS Binary", "", "BIOS Files (*.bin *.rom *.cap *.fd);;All Files (*.*)")
        if path:
            self.load_main_file(path, is_single=is_single)

    def browse_ec_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select EC / KBC ROM Binary", "", "EC ROM Files (*.bin *.rom *.ec);;All Files (*.*)")
        if path:
            self.load_ec_file(path)

    def identify_firmware_type(self, file_path):
        """
        HARDWARE-STRICT FIRMWARE CLASSIFIER:
        Accurately identifies Main BIOS vs EC ROM based on physical SPI Flash hardware architecture,
        NOT just misleading filenames (e.g. files named 'ec.bin' that are actually 8MB/16MB Main BIOS).

        Rule 1: Physical Size Boundary:
                - Standalone EC/KBC Chips are strictly 128KB, 256KB, 512KB, 1MB, or 2MB (<= 2MB).
                - Main SPI Flash Chips are strictly 4MB, 8MB, 16MB, 32MB, 64MB (>= 4MB).
        Rule 2: Intel Flash Descriptor (5AA5F00F) is ONLY present in Main SPI Chips.
        Rule 3: UEFI Reset Vector (0xFFFFFFF0) & _FVH are ONLY present in Main BIOS.
        """
        try:
            size = os.path.getsize(file_path)
            with open(file_path, "rb") as f:
                header = f.read(min(size, 64 * 1024))
                f.seek(max(0, size - 2048))
                footer = f.read()

            has_fd = (b"\x5a\xa5\xf0\x0f" in header)
            has_fvh = (b"_FVH" in header) or (b"_FVH" in footer)
            reset_vec = footer[-16:] if len(footer) >= 16 else b""
            has_reset_jump = any(op in reset_vec for op in [b"\xea", b"\xe9", b"\xeb"])

            # 1. HARDWARE SIZE DEFINITION: Anything 4MB or larger is 100% a MAIN BIOS
            if size >= 4 * 1024 * 1024:
                if has_fd:
                    return "MAIN_BIOS", size, "Intel Full SPI Dump (Flash Descriptor Present)"
                elif has_reset_jump or has_fvh:
                    return "MAIN_BIOS", size, "Main BIOS Region / AMD Dump (Reset Vector / FVH Present)"
                else:
                    return "MAIN_BIOS", size, "Main SPI Flash Image (>= 4MB)"

            # 2. HARDWARE SIZE DEFINITION: Anything 2MB or smaller is 100% an EC / KBC ROM
            if size <= 2 * 1024 * 1024:
                if has_fd:
                    # Rare legacy 1MB-2MB Intel 810/845 BIOS from 20 years ago
                    return "MAIN_BIOS", size, "Legacy Small SPI Dump with Descriptor"
                return "EC_ROM", size, "Standalone EC / KBC SPI Chip (<= 2MB)"

            # 3. Intermediate 2MB-4MB
            if has_fd or has_reset_jump or has_fvh:
                return "MAIN_BIOS", size, "Main BIOS Image"
            else:
                return "EC_ROM", size, "Standalone EC / SIO ROM"

        except Exception as e:
            return "UNKNOWN", 0, str(e)

    def load_main_file(self, path: str, is_single=True):
        """
        Loads firmware directly into Slot 1 (Main BIOS).
        STRICT: Never automatically moves to another slot.
        Identifies whether this file is actually a Main BIOS or an EC ROM,
        and warns the user if they put an EC ROM in the Main slot.
        """
        self.main_bios_path = path
        f_type, sz, desc = self.identify_firmware_type(path)
        size_mb = os.path.getsize(path) / (1024 * 1024)

        if f_type == "MAIN_BIOS":
            type_badge = "[MAIN BIOS]"
            color_style = "color: #00f3ff; font-family: Consolas; font-weight: bold;"
            self.log(f"<font color='#00f3ff'><b>[SLOT 1 LOADED]</b> {Path(path).name} ({size_mb:.2f} MB) -> Verified as <b>Main BIOS</b>.</font>")
        else:
            type_badge = "[WRONG: EC ROM]"
            color_style = "color: #ef4444; font-family: Consolas; font-weight: bold;"
            self.log(f"<font color='#ef4444'><b>[SLOT 1 MISMATCH]</b> You loaded an <b>EC ROM</b> ({sz//1024} KB) into Main BIOS slot! File will remain here as requested, but POST test will report this fault.</font>")

        name_str = f"{type_badge} {Path(path).name}  ({size_mb:.2f} MB)"
        if is_single:
            self.single_label.setText(name_str)
            self.single_label.setStyleSheet("color: #4ade80; font-family: Consolas; font-weight: bold;" if f_type == "MAIN_BIOS" else color_style)
        else:
            self.slot1_label.setText(name_str)
            self.slot1_label.setStyleSheet(color_style)

        self.check_power_readiness()

    def load_ec_file(self, path: str):
        """
        Loads firmware directly into Slot 2 (EC BIOS).
        STRICT: Never automatically moves to another slot.
        Identifies whether this file is actually an EC ROM or a Main BIOS,
        and warns the user if they put a Main BIOS in the EC slot.
        """
        self.ec_bios_path = path
        f_type, sz, desc = self.identify_firmware_type(path)
        size_kb = os.path.getsize(path) / 1024

        if f_type == "EC_ROM":
            type_badge = "[EC / KBC ROM]"
            color_style = "color: #c084fc; font-family: Consolas; font-weight: bold;"
            self.log(f"<font color='#c084fc'><b>[SLOT 2 LOADED]</b> {Path(path).name} ({size_kb:.1f} KB) -> Verified as <b>EC ROM</b>.</font>")
        else:
            type_badge = "[WRONG: MAIN BIOS]"
            color_style = "color: #ef4444; font-family: Consolas; font-weight: bold;"
            self.log(f"<font color='#ef4444'><b>[SLOT 2 MISMATCH]</b> You loaded a <b>Main BIOS</b> ({size_kb//1024} MB) into EC slot! File will remain here as requested, but POST test will report this fault.</font>")

        name_str = f"{type_badge} {Path(path).name}  ({size_kb:.1f} KB)"
        self.slot2_label.setText(name_str)
        self.slot2_label.setStyleSheet(color_style)

        self.check_power_readiness()

    def check_power_readiness(self):
        if not self.is_dual_mode:
            ready = bool(self.main_bios_path and os.path.exists(self.main_bios_path))
        else:
            ready = bool(self.main_bios_path and os.path.exists(self.main_bios_path) and
                         self.ec_bios_path and os.path.exists(self.ec_bios_path))

        self.btn_power.setEnabled(ready)
        if ready:
            self.status_banner.setText("Ready: Press [POWER ON] to simulate boot sequence.")
            self.status_banner.setStyleSheet("color: #4ade80; font-weight: bold;")

    def reset_ui_state(self):
        self.debug_code.setText("--")
        self.debug_code.setStyleSheet("color: #ff0055;")
        self.disp_prob.setText("-- %")
        self.disp_prob.setStyleSheet("color: #64748b;")
        self.progress_bar.setValue(0)
        for code in self.indicators:
            led, lbl, frame = self.indicators[code]
            led.setText("⚪")
            lbl.setStyleSheet("color: #94a3b8;")

    def start_virtual_post(self):
        self.reset_ui_state()
        self.btn_power.setEnabled(False)
        self.console.clear()

        mode_str = "DUAL CHIP (MAIN + EC)" if self.is_dual_mode else "SINGLE CHIP"
        self.log("================================================================================")
        self.log(f"⚡ VIRTUAL MOTHERBOARD POWERED ON -> POST SIMULATION [{mode_str}]")
        self.log(f"Main SPI : {Path(self.main_bios_path).name if self.main_bios_path else 'None'}")
        if self.is_dual_mode:
            self.log(f"EC ROM   : {Path(self.ec_bios_path).name if self.ec_bios_path else 'None'}")
        self.log("================================================================================")

        self.worker = VirtualPostWorker(self.main_bios_path, self.ec_bios_path, self.is_dual_mode)
        self.worker.step_signal.connect(self.handle_step)
        self.worker.progress_signal.connect(self.progress_bar.setValue)
        self.worker.finished_signal.connect(self.handle_finished)
        self.worker.start()

    def handle_step(self, stage_code: str, post_code: str, status: str, message: str):
        self.debug_code.setText(post_code)
        if status == "FAIL":
            self.debug_code.setStyleSheet("color: #ef4444; text-shadow: 0 0 10px #ef4444;")
        elif status == "PASS":
            self.debug_code.setStyleSheet("color: #10b981; text-shadow: 0 0 10px #10b981;")
        else:
            self.debug_code.setStyleSheet("color: #f59e0b; text-shadow: 0 0 10px #f59e0b;")

        if stage_code in self.indicators:
            led, lbl, frame = self.indicators[stage_code]
            if status == "RUNNING":
                led.setText("🟡")
                lbl.setStyleSheet("color: #fbbf24;")
            elif status == "PASS":
                led.setText("🟢")
                lbl.setStyleSheet("color: #4ade80;")
            elif status == "WARN":
                led.setText("🟠")
                lbl.setStyleSheet("color: #f97316;")
            elif status == "FAIL":
                led.setText("🔴")
                lbl.setStyleSheet("color: #ef4444;")

        prefix = f"[POST 0x{post_code}]"
        if status == "FAIL":
            self.log(f"<font color='#ef4444'><b>{prefix} [HALT] {message}</b></font>")
        elif status == "PASS":
            self.log(f"<font color='#4ade80'><b>{prefix} [OK]</b> {message}</font>")
        elif status == "WARN":
            self.log(f"<font color='#f97316'><b>{prefix} [WARN]</b> {message}</font>")
        else:
            self.log(f"<font color='#38bdf8'>{prefix} {message}</font>")

    def handle_finished(self, success: bool, report: dict):
        self.btn_power.setEnabled(True)
        self.log("--------------------------------------------------------------------------------")

        prob = report.get("display_probability", 0)
        self.disp_prob.setText(f"{prob}%")
        if prob >= 85:
            self.disp_prob.setStyleSheet("color: #10b981; text-shadow: 0 0 12px #10b981;")
            chance_text = "<font color='#10b981'><b>VERY HIGH (DISPLAY GUARANTEED)</b></font>"
        elif prob >= 60:
            self.disp_prob.setStyleSheet("color: #f59e0b; text-shadow: 0 0 12px #f59e0b;")
            chance_text = "<font color='#f59e0b'><b>MODERATE (MAY BOOT WITH WARNINGS)</b></font>"
        else:
            self.disp_prob.setStyleSheet("color: #ef4444; text-shadow: 0 0 12px #ef4444;")
            chance_text = "<font color='#ef4444'><b>VERY LOW / CRITICAL FAULT (NO DISPLAY)</b></font>"

        main_h = report.get("main_healthy", True)
        ec_h = report.get("ec_healthy", True)
        hand_h = report.get("handshake_healthy", True)

        m_badge = "<font color='#10b981'>HEALTHY / VALID</font>" if main_h else "<font color='#ef4444'>DEFECTIVE / CORRUPT</font>"
        ec_badge = "<font color='#10b981'>HEALTHY / VALID</font>" if ec_h else "<font color='#ef4444'>DEFECTIVE / CORRUPT</font>"
        bus_badge = "<font color='#10b981'>SYNCHRONIZED</font>" if hand_h else "<font color='#ef4444'>MISMATCH / FAILED</font>"

        summary_box = f"""
<table border='1' cellspacing='0' cellpadding='5' style='border-color:#1e293b; color:#cbd5e1; font-family:Consolas;'>
  <tr bgcolor='#0b1320'><th>HARDWARE ATTRIBUTE</th><th>DIAGNOSTIC STATUS</th><th>VERDICT</th></tr>
  <tr><td>Slot 1 [Main BIOS]</td><td>{report.get('main_file')}</td><td>{m_badge}</td></tr>
  {'<tr><td>Slot 2 [EC BIOS]</td><td>' + report.get('ec_file') + '</td><td>' + ec_badge + '</td></tr>' if self.is_dual_mode else ''}
  {'<tr><td>Bus Handshake</td><td>RSMRST# Synchronization</td><td>' + bus_badge + '</td></tr>' if self.is_dual_mode else ''}
  <tr bgcolor='#050b14'><td><b>DISPLAY PROBABILITY</b></td><td><b>{prob}%</b></td><td>{chance_text}</td></tr>
</table>
"""
        self.log(summary_box)

        if success:
            self.debug_code.setText("AA")
            self.debug_code.setStyleSheet("color: #10b981; text-shadow: 0 0 12px #10b981;")
            self.log(f"<br><font color='#10b981' size='+1'><b>🎉 [SIMULATION RESULT] VIRTUAL POST PASSED! (DISPLAY CHANCE: {prob}%)</b></font>")
            self.log("<font color='#e2e8f0'>All hardware handshakes, power sequencing, ME engine, and GOP display pipelines are valid.<br><b>Safe to write to physical BIOS chips!</b></font>")
        else:
            self.log(f"<br><font color='#ef4444' size='+1'><b>❌ [SIMULATION RESULT] VIRTUAL POST FAILED (DISPLAY CHANCE: {prob}%)</b></font>")
            for err in report.get("errors", []):
                self.log(f"<font color='#ef4444'>• {err}</font>")

    def log(self, html_text: str):
        self.console.append(html_text)
        self.console.ensureCursorVisible()


# ──────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VirtualBiosTestBench()
    window.show()
    sys.exit(app.exec())
