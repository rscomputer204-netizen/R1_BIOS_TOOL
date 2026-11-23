import sys
import os
import re
import json
import subprocess
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QColor, QIcon, QCursor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QFrame, QScrollArea, QMessageBox, QAbstractItemView
)

# Base directory for all FIT tools (points to project's official external FLASH System Tools)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.join(CURRENT_DIR, "external", "FLASH System Tools")
if not os.path.exists(TOOLS_DIR):
    TOOLS_DIR = os.path.join(CURRENT_DIR, "ALL_FIT_TOOLS_UNZIPPED")

# Hardware / CPU Generation metadata mapping by Major/Minor version
GENERATION_MAP = {
    18: "Intel Arrow Lake / Lunar Lake (CSME v18)",
    17: "Intel Meteor Lake / Arrow Lake (CSME v17)",
    16: "Intel 12th/13th/14th Gen (Alder Lake / Raptor Lake / Meteor Lake) (CSME v16)",
    15: "Intel 11th Gen Core (Tiger Lake / Rocket Lake) (CSME v15)",
    14: "Intel 10th Gen Core Desktop/Mobile (Comet Lake) (CSME v14)",
    13: "Intel 10th Gen Core Mobile (Ice Lake) (CSME v13)",
    12: "Intel 8th/9th Gen Core (Coffee Lake Refresh / Cannon Lake) (CSME v12)",
    11: "Intel 6th/7th/8th Gen Core (Skylake / Kaby Lake / Coffee Lake) (CSME v11)",
    10: "Intel 5th Gen Core (Broadwell / Wildcat Point) (ME v10)",
    9:  "Intel 4th Gen Core (Haswell / Shark Bay / Lynx Point) (ME v9)",
    8:  "Intel 3rd Gen Core (Ivy Bridge / Panther Point) (ME v8)",
    7:  "Intel 2nd Gen Core (Sandy Bridge / Cougar Point) (ME v7)",
    6:  "Intel 1st Gen Core (Nehalem / Westmere / Ibex Peak) (ME v6)",
    5:  "Intel Core 2 Duo / Centrino 2 (Cantiga / ICH9-ICH10) (ME v5)",
    4:  "Intel Core 2 Duo / Centrino (ICH8-ICH9) (ME v4)",
    3:  "Intel Core 2 Duo (ICH8/ICH9) (ME v3)",
    2:  "Intel Core 2 Duo (ICH7/ICH8) (ME v2)",
    1:  "Intel Core / Pentium M (ICH6/ICH7) (ME v1)",
}

TXE_GENERATION_MAP = {
    4: "Intel Gemini Lake (CSTXE v4)",
    3: "Intel Apollo Lake (CSTXE v3)",
    2: "Intel Braswell / Cherry Trail (CSTXE v2)",
    1: "Intel Bay Trail (CSTXE v1)",
}

def scan_and_index_tools(base_dir):
    """Scans the tools directory using fit_info.json / fit_registry.json metadata."""
    if not os.path.exists(base_dir):
        return []
    
    # 1. Try registry file first
    reg_candidates = [
        os.path.join(base_dir, "fit_registry.json"),
        os.path.join(CURRENT_DIR, "fit_registry.json")
    ]
    for reg_path in reg_candidates:
        if os.path.exists(reg_path):
            try:
                with open(reg_path, "r", encoding="utf-8") as f:
                    reg_data = json.load(f)
                    tools_list = []
                    for item in reg_data:
                        folder_name = item.get("folder", "")
                        folder_path = os.path.join(base_dir, folder_name)
                        exe_name = item.get("executable", "fit.exe")
                        exe_path = os.path.join(folder_path, exe_name)
                        if not os.path.exists(exe_path):
                            for cand in ["mfit.exe", "fit.exe", "fitc.exe", "ftoolc.exe"]:
                                cp = os.path.join(folder_path, cand)
                                if os.path.exists(cp):
                                    exe_name = cand
                                    exe_path = cp
                                    break
                        ver_str = item.get("version", "")
                        ver_parts = [item.get("major", 0), item.get("minor", 0), item.get("patch", 0), item.get("build", 0)]
                        tools_list.append({
                            "folder": folder_name,
                            "path": folder_path,
                            "exe": exe_name,
                            "exe_path": exe_path,
                            "ver": ver_str,
                            "ver_parts": [p for p in ver_parts if p > 0] or [0],
                            "type": item.get("type", "FIT"),
                            "generation": item.get("generation", "Intel Platform"),
                            "is_txe": item.get("is_txe", False)
                        })
                    if tools_list:
                        return tools_list
            except Exception:
                pass

    # 2. Dynamic scan from fit_info.json in each directory
    entries = sorted(os.listdir(base_dir))
    tools_list = []
    
    for f in entries:
        p = os.path.join(base_dir, f)
        if not os.path.isdir(p):
            continue
            
        info_path = os.path.join(p, "fit_info.json")
        if os.path.exists(info_path):
            try:
                with open(info_path, "r", encoding="utf-8") as inf_f:
                    meta = json.load(inf_f)
                    exe_name = meta.get("executable", "fit.exe")
                    exe_path = os.path.join(p, exe_name)
                    ver_str = meta.get("version", "")
                    ver_parts = [meta.get("major", 0), meta.get("minor", 0), meta.get("patch", 0), meta.get("build", 0)]
                    tools_list.append({
                        "folder": f,
                        "path": p,
                        "exe": exe_name,
                        "exe_path": exe_path,
                        "ver": ver_str,
                        "ver_parts": [x for x in ver_parts if x > 0] or [0],
                        "type": meta.get("type", "FIT"),
                        "generation": meta.get("generation", "Intel Platform"),
                        "is_txe": meta.get("is_txe", False)
                    })
                    continue
            except:
                pass
                
        # Fallback if no fit_info.json
        exes = [e for e in os.listdir(p) if e.lower().endswith('.exe')]
        main_exe = exes[0] if exes else None
        m_ver = re.search(r'v(\d+(?:\.\d+)*)', f, re.IGNORECASE)
        ver_str = m_ver.group(1) if m_ver else ""
        ver_parts = [int(x) for x in ver_str.split('.') if x.isdigit()]
        tools_list.append({
            "folder": f,
            "path": p,
            "exe": main_exe,
            "exe_path": os.path.join(p, main_exe) if main_exe else "",
            "ver": ver_str,
            "ver_parts": ver_parts,
            "type": "MFIT" if "MFIT" in f.upper() else ("CSTXE" if "CSTXE" in f.upper() else "FIT"),
            "generation": "Intel Core Platform",
            "is_txe": "CSTXE" in f.upper()
        })
        
    return tools_list


class FITFinderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Intel Flash Image Tool (FIT & MFIT) Version Matcher & Launcher")
        self.resize(1120, 780)
        self.setMinimumSize(950, 620)
        
        # Load indexed tools
        self.all_tools = scan_and_index_tools(TOOLS_DIR)
        self.current_filtered_tools = list(self.all_tools)
        self.selected_tool = self.all_tools[0] if self.all_tools else None
        
        self.setup_ui()
        self.apply_dark_theme()
        self.on_search_changed("")

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(18, 16, 18, 16)
        main_layout.setSpacing(12)
        
        # --- HEADER SECTION ---
        header_layout = QHBoxLayout()
        header_title_layout = QVBoxLayout()
        
        title_label = QLabel("INTEL FLASH IMAGE TOOL FINDER")
        title_label.setObjectName("headerTitle")
        
        sub_title = QLabel("Real-time Version Matcher & Direct Launcher for 116 Intel FIT, FITC & MFIT Tools")
        sub_title.setObjectName("headerSub")
        
        header_title_layout.addWidget(title_label)
        header_title_layout.addWidget(sub_title)
        header_layout.addLayout(header_title_layout)
        header_layout.addStretch()
        
        # Total tools badge
        self.badge_count = QLabel(f"TOTAL TOOLS: {len(self.all_tools)}")
        self.badge_count.setObjectName("badgeCount")
        header_layout.addWidget(self.badge_count)
        
        main_layout.addLayout(header_layout)
        
        # --- SEARCH & QUICK FILTER BAR ---
        search_frame = QFrame()
        search_frame.setObjectName("searchFrame")
        search_layout = QVBoxLayout(search_frame)
        search_layout.setContentsMargins(14, 12, 14, 12)
        search_layout.setSpacing(10)
        
        # Search Box
        search_row = QHBoxLayout()
        search_icon_label = QLabel("SEARCH BIOS / ME VERSION:")
        search_icon_label.setObjectName("searchLabel")
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Type BIOS or ME version (e.g., 16.1.42.2872, 12.0.40, 11.8.50, 8.1, 15.0, TXE 3)...")
        self.search_input.setObjectName("searchInput")
        self.search_input.textChanged.connect(self.on_search_changed)
        
        self.btn_clear = QPushButton("CLEAR")
        self.btn_clear.setObjectName("btnClear")
        self.btn_clear.clicked.connect(lambda: self.search_input.clear())
        
        search_row.addWidget(search_icon_label)
        search_row.addWidget(self.search_input, 1)
        search_row.addWidget(self.btn_clear)
        search_layout.addLayout(search_row)
        
        # Filter Chips
        chips_row = QHBoxLayout()
        chips_label = QLabel("Quick Presets:")
        chips_label.setStyleSheet("color: #7b8ea5; font-size: 11px; font-weight: bold;")
        chips_row.addWidget(chips_label)
        
        presets = [
            ("ALL (116)", ""),
            ("CSME 16/18", "16"),
            ("CSME 15", "15"),
            ("CSME 14", "14"),
            ("CSME 13", "13"),
            ("CSME 12", "12"),
            ("CSME 11", "11"),
            ("ME 10", "10"),
            ("ME 9", "9"),
            ("ME 8", "8"),
            ("CSTXE", "TXE"),
            ("MFIT", "MFIT"),
        ]
        
        for name, query in presets:
            btn = QPushButton(name)
            btn.setObjectName("chipBtn")
            btn.clicked.connect(lambda checked=False, q=query: self.set_preset_search(q))
            chips_row.addWidget(btn)
            
        chips_row.addStretch()
        search_layout.addLayout(chips_row)
        
        main_layout.addWidget(search_frame)
        
        # --- RECOMMENDED / BEST MATCH HERO CARD ---
        self.hero_card = QFrame()
        self.hero_card.setObjectName("heroCard")
        hero_layout = QVBoxLayout(self.hero_card)
        hero_layout.setContentsMargins(16, 14, 16, 14)
        hero_layout.setSpacing(8)
        
        hero_top_row = QHBoxLayout()
        self.match_status_badge = QLabel("READY - SELECT OR TYPE VERSION")
        self.match_status_badge.setObjectName("matchBadge")
        
        self.match_score_label = QLabel("")
        self.match_score_label.setStyleSheet("color: #8da4be; font-size: 11px;")
        
        hero_top_row.addWidget(self.match_status_badge)
        hero_top_row.addWidget(self.match_score_label)
        hero_top_row.addStretch()
        hero_layout.addLayout(hero_top_row)
        
        hero_mid_row = QHBoxLayout()
        hero_info_layout = QVBoxLayout()
        
        self.hero_tool_name = QLabel("No Tool Selected")
        self.hero_tool_name.setObjectName("heroToolName")
        
        self.hero_details = QLabel("Select any tool from the table or search by version above.")
        self.hero_details.setObjectName("heroDetails")
        
        self.hero_path = QLabel("")
        self.hero_path.setObjectName("heroPath")
        
        hero_info_layout.addWidget(self.hero_tool_name)
        hero_info_layout.addWidget(self.hero_details)
        hero_info_layout.addWidget(self.hero_path)
        hero_mid_row.addLayout(hero_info_layout, 1)
        
        # Hero Action Buttons
        hero_actions_layout = QVBoxLayout()
        hero_actions_layout.setSpacing(8)
        
        self.btn_hero_launch = QPushButton("RUN FLASH IMAGE TOOL")
        self.btn_hero_launch.setObjectName("btnHeroLaunch")
        self.btn_hero_launch.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_hero_launch.clicked.connect(self.launch_current_tool)
        
        self.btn_hero_folder = QPushButton("OPEN TOOL FOLDER")
        self.btn_hero_folder.setObjectName("btnHeroFolder")
        self.btn_hero_folder.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_hero_folder.clicked.connect(self.open_current_folder)
        
        hero_actions_layout.addWidget(self.btn_hero_launch)
        hero_actions_layout.addWidget(self.btn_hero_folder)
        hero_mid_row.addLayout(hero_actions_layout)
        
        hero_layout.addLayout(hero_mid_row)
        main_layout.addWidget(self.hero_card)
        
        # --- TOOLS LIST / TABLE ---
        table_header_layout = QHBoxLayout()
        self.table_title = QLabel("AVAILABLE FIT / MFIT PACKAGES (116)")
        self.table_title.setObjectName("sectionTitle")
        table_header_layout.addWidget(self.table_title)
        table_header_layout.addStretch()
        
        self.lbl_table_hint = QLabel("Double-click any row to instantly launch the tool")
        self.lbl_table_hint.setStyleSheet("color: #00d2ff; font-size: 11px;")
        table_header_layout.addWidget(self.lbl_table_hint)
        main_layout.addLayout(table_header_layout)
        
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "#", "Tool Package Name", "Tool Type", "ME / CSME Version", "Target Hardware / Generation", "Executable"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.itemSelectionChanged.connect(self.on_table_selection_changed)
        self.table.itemDoubleClicked.connect(lambda item: self.launch_current_tool())
        
        main_layout.addWidget(self.table, 1)
        
        # --- BOTTOM STATUS BAR ---
        status_layout = QHBoxLayout()
        self.status_bar_label = QLabel(f"Directory: {TOOLS_DIR}")
        self.status_bar_label.setObjectName("statusLabel")
        status_layout.addWidget(self.status_bar_label)
        status_layout.addStretch()
        
        btn_refresh = QPushButton("RE-SCAN DIRECTORY")
        btn_refresh.setObjectName("btnRefresh")
        btn_refresh.clicked.connect(self.refresh_tools)
        status_layout.addWidget(btn_refresh)
        
        main_layout.addLayout(status_layout)

    def set_preset_search(self, text):
        self.search_input.setText(text)
        self.search_input.setFocus()

    def on_search_changed(self, query):
        query = query.strip()
        scored_results = self.match_tools(query)
        self.current_filtered_tools = [item[1] for item in scored_results]
        
        self.populate_table(scored_results)
        
        if scored_results:
            best_match = scored_results[0]
            self.selected_tool = best_match[1]
            self.update_hero_card(best_match, is_search=bool(query))
        else:
            self.selected_tool = None
            self.update_hero_card(None, is_search=bool(query))

    def match_tools(self, query):
        if not query:
            return [(0, t, "Available") for t in self.all_tools]
            
        q_lower = query.lower()
        q_tokens = [tok for tok in re.split(r'[\s,_\-]+', q_lower) if tok]
        
        # Check if query contains version digits
        q_ver_match = re.search(r'(\d+(?:\.\d+)*)', query)
        q_parts = [int(x) for x in q_ver_match.group(1).split('.')] if q_ver_match else []
        
        is_txe_query = any(tok in ["txe", "cstxe"] for tok in q_tokens)
        
        scored = []
        for t in self.all_tools:
            score = 0
            reasons = []
            folder_lower = t["folder"].lower()
            type_lower = t["type"].lower()
            
            # TXE preference matching
            if is_txe_query:
                if t["is_txe"]:
                    score += 80
                    reasons.append("TXE tool family")
                else:
                    score -= 50
            elif t["is_txe"]:
                # If query wasn't asking for TXE, slight penalty
                score -= 10
                
            # Token matching
            for tok in q_tokens:
                if tok in folder_lower:
                    score += 35
                    reasons.append(f"Contains '{tok}'")
                elif tok in type_lower:
                    score += 25
                    reasons.append(f"Type matches '{tok}'")
                    
            t_parts = t["ver_parts"]
            if q_parts and t_parts:
                # Major version comparison
                if q_parts[0] == t_parts[0]:
                    score += 70
                    reasons.append(f"Major v{q_parts[0]} match")
                    
                    # Minor version comparison
                    if len(q_parts) > 1 and len(t_parts) > 1:
                        if q_parts[1] == t_parts[1]:
                            score += 45
                            reasons.append(f"Minor v{q_parts[0]}.{q_parts[1]} match")
                            
                            # Patch comparison (3rd part)
                            if len(q_parts) > 2 and len(t_parts) > 2:
                                if q_parts[2] == t_parts[2]:
                                    score += 250  # Top priority for exact 3-part match (Major.Minor.Patch)
                                    reasons.append("Exact 3-part match (Major.Minor.Patch)")
                        else:
                            diff = abs(q_parts[1] - t_parts[1])
                            score -= min(15, diff * 2)
                            
            if score > 0:
                scored.append((score, t, ", ".join(reasons)))
                
        scored.sort(key=lambda x: (x[0], x[1]["ver_parts"]), reverse=True)
        return scored

    def populate_table(self, scored_results):
        self.table.setRowCount(len(scored_results))
        self.table_title.setText(f"MATCHING FIT / MFIT PACKAGES ({len(scored_results)})")
        
        for row, (score, tool, reason) in enumerate(scored_results):
            # Column 0: Index
            idx_item = QTableWidgetItem(f"{row+1:03d}")
            idx_item.setTextAlignment(Qt.AlignCenter)
            
            # Column 1: Folder / Package Name
            name_item = QTableWidgetItem(tool["folder"])
            
            # Column 2: Tool Type
            type_item = QTableWidgetItem(tool["type"])
            type_item.setTextAlignment(Qt.AlignCenter)
            
            # Column 3: ME Version
            ver_text = f"v{tool['ver']}" if tool['ver'] else "-"
            ver_item = QTableWidgetItem(ver_text)
            ver_item.setTextAlignment(Qt.AlignCenter)
            
            # Column 4: Hardware Generation
            gen_item = QTableWidgetItem(tool["generation"])
            
            # Column 5: Executable
            exe_item = QTableWidgetItem(tool["exe"] if tool["exe"] else "MISSING")
            exe_item.setTextAlignment(Qt.AlignCenter)
            if not tool["exe"]:
                exe_item.setForeground(QColor("#ff4757"))
            else:
                exe_item.setForeground(QColor("#00d2ff"))
                
            self.table.setItem(row, 0, idx_item)
            self.table.setItem(row, 1, name_item)
            self.table.setItem(row, 2, type_item)
            self.table.setItem(row, 3, ver_item)
            self.table.setItem(row, 4, gen_item)
            self.table.setItem(row, 5, exe_item)
            
        if scored_results:
            self.table.selectRow(0)

    def on_table_selection_changed(self):
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            return
        row = selected_rows[0].row()
        if 0 <= row < len(self.current_filtered_tools):
            self.selected_tool = self.current_filtered_tools[row]
            # Update hero card for selected tool
            self.hero_tool_name.setText(self.selected_tool["folder"])
            self.hero_details.setText(
                f"Type: {self.selected_tool['type']}  |  Version: v{self.selected_tool['ver']}  |  Generation: {self.selected_tool['generation']}"
            )
            self.hero_path.setText(f"Executable: {self.selected_tool['exe_path']}")
            
            has_exe = bool(self.selected_tool["exe"] and os.path.exists(self.selected_tool["exe_path"]))
            self.btn_hero_launch.setEnabled(has_exe)
            self.btn_hero_launch.setText(f"RUN {self.selected_tool['exe']}" if has_exe else "EXE NOT FOUND")

    def update_hero_card(self, best_match, is_search=False):
        if not best_match:
            self.match_status_badge.setText("NO COMPATIBLE FIT TOOL FOUND")
            self.match_status_badge.setStyleSheet("background: #ff3344; color: white;")
            self.match_score_label.setText("")
            self.hero_tool_name.setText("No Matching Tool Available for This Version")
            self.hero_details.setText("Please check your entered version or try searching with major version (e.g. 16, 12, 11).")
            self.hero_path.setText("")
            self.btn_hero_launch.setEnabled(False)
            self.btn_hero_folder.setEnabled(False)
            return
            
        score, tool, reason = best_match
        self.selected_tool = tool
        
        if is_search:
            if score >= 120:
                self.match_status_badge.setText("EXACT / PERFECT COMPATIBLE MATCH")
                self.match_status_badge.setStyleSheet("background: #00e676; color: #041208; font-weight: bold;")
            elif score >= 60:
                self.match_status_badge.setText("RECOMMENDED COMPATIBLE FIT TOOL")
                self.match_status_badge.setStyleSheet("background: #00d2ff; color: #021a24; font-weight: bold;")
            else:
                self.match_status_badge.setText("CLOSEST AVAILABLE MATCH")
                self.match_status_badge.setStyleSheet("background: #ffb300; color: #211500; font-weight: bold;")
            self.match_score_label.setText(f"Match Criteria: {reason}")
        else:
            self.match_status_badge.setText("SELECTED FLASH IMAGE TOOL")
            self.match_status_badge.setStyleSheet("background: #1e293b; color: #00d2ff; font-weight: bold;")
            self.match_score_label.setText("")
            
        self.hero_tool_name.setText(tool["folder"])
        self.hero_details.setText(
            f"Type: {tool['type']}  |  Version: v{tool['ver']}  |  Generation: {tool['generation']}"
        )
        self.hero_path.setText(f"Executable: {tool['exe_path']}")
        
        has_exe = bool(tool["exe"] and os.path.exists(tool["exe_path"]))
        self.btn_hero_launch.setEnabled(has_exe)
        self.btn_hero_folder.setEnabled(True)
        self.btn_hero_launch.setText(f"RUN {tool['exe']}" if has_exe else "EXE NOT FOUND")

    def launch_current_tool(self):
        if not self.selected_tool:
            return
        exe_path = self.selected_tool["exe_path"]
        if not exe_path or not os.path.exists(exe_path):
            QMessageBox.critical(self, "Error", f"Executable not found:\n{exe_path}")
            return
            
        try:
            folder = os.path.dirname(exe_path)
            subprocess.Popen([exe_path], cwd=folder)
        except Exception as e:
            QMessageBox.critical(self, "Launch Failed", f"Could not launch executable:\n{str(e)}")

    def open_current_folder(self):
        if not self.selected_tool:
            return
        folder = self.selected_tool["path"]
        if os.path.exists(folder):
            os.startfile(folder)
        else:
            QMessageBox.warning(self, "Folder Missing", f"Folder does not exist:\n{folder}")

    def refresh_tools(self):
        self.all_tools = scan_and_index_tools(TOOLS_DIR)
        self.badge_count.setText(f"TOTAL TOOLS: {len(self.all_tools)}")
        self.on_search_changed(self.search_input.text())
        QMessageBox.information(self, "Refreshed", f"Successfully rescanned {len(self.all_tools)} FIT/MFIT packages.")

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0b111b;
            }
            QWidget {
                color: #e2e8f0;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            #headerTitle {
                color: #00d2ff;
                font-size: 20px;
                font-weight: 800;
                letter-spacing: 1px;
            }
            #headerSub {
                color: #8da4be;
                font-size: 12px;
            }
            #badgeCount {
                background-color: #162438;
                color: #00d2ff;
                border: 1px solid #1e3a5f;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 700;
            }
            #searchFrame {
                background-color: #111a28;
                border: 1px solid #1f2f45;
                border-radius: 8px;
            }
            #searchLabel {
                color: #00d2ff;
                font-size: 12px;
                font-weight: 700;
            }
            #searchInput {
                background-color: #0a0f18;
                border: 1px solid #243b5a;
                border-radius: 6px;
                color: #ffffff;
                padding: 8px 12px;
                font-size: 13px;
            }
            #searchInput:focus {
                border: 1px solid #00d2ff;
            }
            #btnClear {
                background-color: #1f2b3e;
                color: #a0aec0;
                border: 1px solid #2d3f58;
                border-radius: 6px;
                padding: 8px 14px;
                font-size: 11px;
                font-weight: 700;
            }
            #btnClear:hover {
                background-color: #2d3f58;
                color: #ffffff;
            }
            #chipBtn {
                background-color: #162234;
                color: #a0c0e0;
                border: 1px solid #223550;
                border-radius: 4px;
                padding: 4px 9px;
                font-size: 11px;
                font-weight: 600;
            }
            #chipBtn:hover {
                background-color: #00d2ff;
                color: #041208;
                font-weight: bold;
            }
            #heroCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #121d2d, stop:1 #0c1421);
                border: 1px solid #1e3656;
                border-left: 4px solid #00d2ff;
                border-radius: 8px;
            }
            #matchBadge {
                border-radius: 4px;
                padding: 3px 10px;
                font-size: 11px;
            }
            #heroToolName {
                color: #ffffff;
                font-size: 18px;
                font-weight: 800;
            }
            #heroDetails {
                color: #a0c2de;
                font-size: 12px;
            }
            #heroPath {
                color: #5c7490;
                font-size: 11px;
                font-family: Consolas, monospace;
            }
            #btnHeroLaunch {
                background-color: #00d2ff;
                color: #021422;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: 800;
                letter-spacing: 0.5px;
            }
            #btnHeroLaunch:hover {
                background-color: #33dcff;
            }
            #btnHeroLaunch:disabled {
                background-color: #243548;
                color: #62758d;
            }
            #btnHeroFolder {
                background-color: #19273a;
                color: #e2e8f0;
                border: 1px solid #2b4263;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 700;
            }
            #btnHeroFolder:hover {
                background-color: #243852;
                color: #ffffff;
            }
            #sectionTitle {
                color: #00d2ff;
                font-size: 13px;
                font-weight: 800;
                letter-spacing: 0.5px;
            }
            QTableWidget {
                background-color: #0e1623;
                border: 1px solid #1a283c;
                border-radius: 6px;
                gridline-color: transparent;
                selection-background-color: #1b3558;
                selection-color: #00d2ff;
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 6px;
                border-bottom: 1px solid #142031;
            }
            QTableWidget::item:selected {
                background-color: #183354;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #131e2e;
                color: #8da4be;
                padding: 8px;
                font-weight: 700;
                font-size: 11px;
                border: none;
                border-bottom: 1px solid #1e324c;
            }
            #statusLabel {
                color: #5c7490;
                font-size: 11px;
            }
            #btnRefresh {
                background-color: transparent;
                color: #7b94b0;
                border: 1px solid #203148;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 11px;
            }
            #btnRefresh:hover {
                background-color: #1a283c;
                color: #ffffff;
            }
            QScrollBar:vertical {
                background: #0e1623;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #243852;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #00d2ff;
            }
        """)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FITFinderApp()
    window.show()
    sys.exit(app.exec())
