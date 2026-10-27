"""
analysis_ui.py
MEAnalyzer-powered Firmware Analysis Dashboard.
Opens as a standalone QDialog, populated from FirmwareAnalyzer results.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget, QWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea,
    QGroupBox, QFrame, QTreeWidget, QTreeWidgetItem, QSplitter,
    QAbstractItemView,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QBrush, QPainter, QPen


# ─────────────────────────────────────────────────────────────────────────────
#  Colour palette
# ─────────────────────────────────────────────────────────────────────────────
_BG        = "#0a0b10"
_BG2       = "#0e0f1b"
_BG3       = "#131422"
_BORDER    = "#1f2233"
_CYAN      = "#00f3ff"
_GREEN     = "#00ff41"
_ORANGE    = "#ffaa00"
_RED       = "#ff3333"
_PURPLE    = "#ff00ff"
_TEXT      = "#d4d4d4"
_LABEL     = "#888899"

_TAB_STYLE = f"""
QTabWidget::pane  {{ border: 1px solid {_BORDER}; background: {_BG2}; }}
QTabBar::tab      {{ background: {_BG3}; color: {_LABEL}; padding: 8px 18px;
                     border: 1px solid {_BORDER}; border-bottom: none;
                     border-top-left-radius: 4px; border-top-right-radius: 4px;
                     margin-right: 2px; }}
QTabBar::tab:selected {{ background: {_BG}; color: {_CYAN}; font-weight: bold; }}
QTabBar::tab:hover:!selected {{ background: #1a1c2e; }}
"""

_TABLE_STYLE = f"""
QTableWidget {{
    background: {_BG};
    color: {_TEXT};
    gridline-color: {_BORDER};
    border: none;
    alternate-background-color: {_BG3};
    font-family: 'Consolas', monospace;
    font-size: 11px;
}}
QTableWidget::item          {{ padding: 4px 6px; }}
QTableWidget::item:selected {{ background: #0d3452; color: white; }}
QHeaderView::section {{
    background: {_BG3};
    color: {_CYAN};
    border: 1px solid {_BORDER};
    padding: 5px 6px;
    font-weight: bold;
    font-size: 11px;
}}
"""

_DIALOG_STYLE = f"""
QDialog          {{ background: {_BG};  color: {_TEXT}; font-family: 'Segoe UI'; }}
QGroupBox        {{ border: 1px solid {_BORDER}; border-radius: 6px;
                    color: {_CYAN}; font-weight: bold; margin-top: 8px;
                    padding-top: 6px; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; }}
QScrollArea      {{ border: none; background: transparent; }}
QLabel           {{ color: {_TEXT}; }}
QTreeWidget {{
    background: {_BG2};
    color: {_TEXT};
    border: 1px solid {_BORDER};
    font-family: 'Consolas', monospace;
    font-size: 11px;
}}
QTreeWidget::item:selected {{ background: #0d3452; }}
QHeaderView::section {{
    background: {_BG3};
    color: {_CYAN};
    border: 1px solid {_BORDER};
    padding: 4px;
    font-weight: bold;
}}
"""


# ─────────────────────────────────────────────────────────────────────────────
#  Helper widgets
# ─────────────────────────────────────────────────────────────────────────────

class _HealthBar(QWidget):
    """Draws a coloured segmented health bar."""
    def __init__(self, score: int, parent=None):
        super().__init__(parent)
        self.score = max(0, min(100, score))
        self.setMinimumHeight(16)
        self.setMaximumHeight(16)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Track
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(_BORDER)))
        p.drawRoundedRect(0, 0, w, h, 4, 4)

        # Fill
        fill_w = int(w * self.score / 100)
        colour = _GREEN if self.score >= 80 else (_ORANGE if self.score >= 50 else _RED)
        p.setBrush(QBrush(QColor(colour)))
        p.drawRoundedRect(0, 0, fill_w, h, 4, 4)


def _divider():
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet(f"color: {_BORDER};")
    return f


def _section_label(text):
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"color: {_CYAN}; font-size: 11px; font-weight: bold; "
        f"letter-spacing: 1px; margin-top: 8px;"
    )
    return lbl


def _make_table(headers, rows):
    t = QTableWidget(len(rows), len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.setStyleSheet(_TABLE_STYLE)
    t.setAlternatingRowColors(True)
    t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    t.verticalHeader().setVisible(False)
    t.horizontalHeader().setStretchLastSection(True)
    t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

    for r_i, row in enumerate(rows):
        for c_i, key in enumerate(headers):
            val = str(row.get(key, ""))
            item = QTableWidgetItem(val)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            t.setItem(r_i, c_i, item)
    return t


def _empty_label(msg="No data available."):
    lbl = QLabel(msg)
    lbl.setStyleSheet(f"color: {_LABEL}; padding: 20px; font-style: italic;")
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return lbl


# ─────────────────────────────────────────────────────────────────────────────
#  Property grid  (key → value pairs)
# ─────────────────────────────────────────────────────────────────────────────

def _property_grid(data_dict: dict) -> QScrollArea:
    """Renders a dict as a two-column property grid inside a scroll area."""
    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(10, 10, 10, 10)
    layout.setSpacing(6)

    for key, value in data_dict.items():
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(10)

        k_lbl = QLabel(f"{key}:")
        k_lbl.setFixedWidth(220)
        k_lbl.setStyleSheet(
            f"color: {_LABEL}; font-weight: bold; font-size: 12px;"
        )
        k_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        v_lbl = QLabel(str(value))
        v_lbl.setStyleSheet(
            f"color: {_GREEN}; font-family: 'Consolas', monospace; font-size: 12px;"
        )
        v_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        v_lbl.setWordWrap(True)

        row_layout.addWidget(k_lbl)
        row_layout.addWidget(v_lbl, 1)
        layout.addWidget(row_widget)

    layout.addStretch()
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(container)
    return scroll


# ─────────────────────────────────────────────────────────────────────────────
#  Main Dashboard Dialog
# ─────────────────────────────────────────────────────────────────────────────

class AnalysisDashboard(QDialog):
    """
    Firmware Analysis Dashboard.
    Call with the dict returned by FirmwareAnalyzer.run_analysis()
    and the report_manager.settings dict.
    """

    def __init__(self, data: dict, parent=None, settings: dict = None):
        super().__init__(parent)
        self.data = data
        self.s = settings or {}

        self.setWindowTitle("Firmware Analysis Dashboard  —  MEAnalyzer Engine")
        self.resize(1100, 720)
        self.setStyleSheet(_DIALOG_STYLE)
        self._build_ui()

    # ── UI build ──────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header banner ────────────────────────────────────────────
        header = QWidget()
        header.setStyleSheet(f"background: {_BG3}; border-bottom: 1px solid {_BORDER};")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(20, 12, 20, 12)

        title = QLabel("FIRMWARE ANALYSIS DASHBOARD")
        title.setStyleSheet(
            f"color: {_CYAN}; font-size: 16px; font-weight: bold; letter-spacing: 2px;"
        )
        subtitle = QLabel("Powered by MEAnalyzer Engine")
        subtitle.setStyleSheet(f"color: {_LABEL}; font-size: 11px;")

        h_layout.addWidget(title)
        h_layout.addStretch()
        h_layout.addWidget(subtitle)
        root.addWidget(header)

        # ── Body: left tabs + right health panel ─────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(6)
        splitter.setStyleSheet(f"QSplitter::handle {{ background: {_BORDER}; }}")

        # Left: Tab widget
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(_TAB_STYLE)
        self._add_tabs()
        splitter.addWidget(self.tabs)

        # Right: Health panel
        health_widget = self._build_health_panel()
        splitter.addWidget(health_widget)
        splitter.setSizes([750, 350])

        root.addWidget(splitter, 1)

    def _add_tabs(self):
        general = self.data.get("general", {})
        firmware = self.data.get("firmware", {})
        fpt  = self.data.get("fpt",  [])
        bpdt = self.data.get("bpdt", [])

        # ── General File Info (always shown) ──────────────────────────
        if general:
            self.tabs.addTab(_property_grid(general), "General Info")

        # ── Management Engine ─────────────────────────────────────────
        if self.s.get("mea_show_me", True):
            me_entries = firmware.get("Management Engine", [])
            tab = self._firmware_section_tab(me_entries, "Intel ME")
            self.tabs.addTab(tab, "Intel ME")

        # ── PMC / PCHC / PHY / OROM / TXE / SPS ─────────────────────
        if self.s.get("mea_show_pmc", True):
            other_tab = QWidget()
            other_layout = QVBoxLayout(other_tab)
            other_layout.setContentsMargins(0, 0, 0, 0)
            other_tabs = QTabWidget()
            other_tabs.setStyleSheet(_TAB_STYLE)

            OTHER_SECTIONS = [
                "Power Management Controller",
                "Platform Controller Hub Configuration",
                "USB Type C Physical",
                "Graphics Option ROM",
                "Trusted Execution Engine",
                "Server Platform Services",
                "Graphics System Controller",
            ]
            found_any = False
            for sec_name in OTHER_SECTIONS:
                entries = firmware.get(sec_name, [])
                if entries:
                    found_any = True
                    tab = self._firmware_section_tab(entries, sec_name)
                    short = sec_name.split()[-1]  # abbreviation
                    other_tabs.addTab(tab, short)

            if found_any:
                other_layout.addWidget(other_tabs)
            else:
                other_layout.addWidget(_empty_label("No PMC / PCHC / PHY data found."))

            self.tabs.addTab(other_tab, "IUP Firmware")

        # ── FPT ───────────────────────────────────────────────────────
        if self.s.get("mea_show_fpt", True):
            if fpt:
                headers = list(fpt[0].keys())
                tab = _make_table(headers, fpt)
            else:
                tab = _empty_label("No Flash Partition Table data found.\n(-dfpt flag returned empty)")
            self.tabs.addTab(tab, "FPT")

        # ── BPDT ──────────────────────────────────────────────────────
        if self.s.get("mea_show_bpdt", True):
            if bpdt:
                headers = list(bpdt[0].keys())
                tab = _make_table(headers, bpdt)
            else:
                tab = _empty_label("No BPDT / IFWI data found.")
            self.tabs.addTab(tab, "BPDT / IFWI")

    def _firmware_section_tab(self, entries: list, section_name: str) -> QWidget:
        """Build a scroll area with one property grid per firmware entry."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        if not entries:
            layout.addWidget(_empty_label(f"No {section_name} data found."))
            return container

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(10, 10, 10, 10)
        inner_layout.setSpacing(12)

        for i, entry in enumerate(entries):
            if len(entries) > 1:
                inner_layout.addWidget(_section_label(f"Entry #{i + 1}"))
            for key, val in entry.items():
                row = QWidget()
                rl = QHBoxLayout(row)
                rl.setContentsMargins(0, 0, 0, 0)
                rl.setSpacing(10)

                k = QLabel(f"{key}:")
                k.setFixedWidth(240)
                k.setStyleSheet(f"color: {_LABEL}; font-weight: bold;")
                k.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

                v = QLabel(str(val))
                v.setStyleSheet(f"color: {_GREEN}; font-family: 'Consolas', monospace;")
                v.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                v.setWordWrap(True)

                rl.addWidget(k)
                rl.addWidget(v, 1)
                inner_layout.addWidget(row)

            if i < len(entries) - 1:
                inner_layout.addWidget(_divider())

        inner_layout.addStretch()
        scroll.setWidget(inner)
        layout.addWidget(scroll)
        return container

    # ── Health panel ─────────────────────────────────────────────────

    def _build_health_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet(f"background: {_BG2}; border-left: 1px solid {_BORDER};")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        health = self.data.get("health", {})
        score  = health.get("score", 0)
        suggestions = health.get("suggestions", [])
        messages = self.data.get("messages", [])

        # ── Score ─────────────────────────────────────────────────────
        score_title = QLabel("HEALTH SCORE")
        score_title.setStyleSheet(
            f"color: {_LABEL}; font-size: 10px; font-weight: bold; letter-spacing: 2px;"
        )
        layout.addWidget(score_title)

        colour = _GREEN if score >= 80 else (_ORANGE if score >= 50 else _RED)
        score_lbl = QLabel(f"{score} / 100")
        score_lbl.setStyleSheet(
            f"color: {colour}; font-size: 36px; font-weight: bold;"
        )
        layout.addWidget(score_lbl)

        bar = _HealthBar(score)
        layout.addWidget(bar)

        layout.addWidget(_divider())

        # ── Messages ──────────────────────────────────────────────────
        if self.s.get("mea_show_messages", True) and messages:
            layout.addWidget(_section_label("MEA MESSAGES"))
            msg_tree = QTreeWidget()
            msg_tree.setHeaderHidden(True)
            msg_tree.setStyleSheet(
                f"QTreeWidget {{ background: {_BG}; color: {_TEXT}; "
                f"border: 1px solid {_BORDER}; font-size: 11px; }}"
            )
            msg_tree.setWordWrap(True)
            for msg in messages:
                item = QTreeWidgetItem([msg])
                if any(w in msg.lower() for w in ("error", "corrupt", "invalid", "rom-bypass")):
                    item.setForeground(0, QBrush(QColor(_RED)))
                elif "warning" in msg.lower():
                    item.setForeground(0, QBrush(QColor(_ORANGE)))
                elif msg.startswith("[OK]"):
                    item.setForeground(0, QBrush(QColor(_GREEN)))
                else:
                    item.setForeground(0, QBrush(QColor(_LABEL)))
                msg_tree.addTopLevelItem(item)
            layout.addWidget(msg_tree, 1)
            layout.addWidget(_divider())

        # ── Suggestions ───────────────────────────────────────────────
        if suggestions:
            layout.addWidget(_section_label("REPAIR SUGGESTIONS"))
            for sugg in suggestions:
                s_lbl = QLabel(f"• {sugg}")
                s_lbl.setStyleSheet(f"color: {_CYAN}; font-size: 11px;")
                s_lbl.setWordWrap(True)
                layout.addWidget(s_lbl)

        layout.addStretch()
        return panel
