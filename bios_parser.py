import os
import sys
import struct
import json
import subprocess
import threading
from pathlib import Path
from path_utils import get_app_root, get_python_cmd, get_subprocess_env

# Constants
INTEL_FD_SIGNATURE = b'\x5a\xa5\xf0\x0f'


# ─────────────────────────────────────────────────────────────────────────────
# UTILITY
# ─────────────────────────────────────────────────────────────────────────────

def print_terminal_log(callback, message, level="INFO"):
    """Sends a message to the terminal UI callback with safe encoding."""
    prefix = f"[{level}] " if level else ""
    full_msg = f"{prefix}{message}"
    if callback:
        try:
            callback(full_msg)
        except Exception:
            pass
    else:
        try:
            print(full_msg)
        except UnicodeEncodeError:
            print(full_msg.encode(sys.stdout.encoding or 'utf-8', errors='replace').decode(sys.stdout.encoding or 'utf-8', errors='replace'))


# ─────────────────────────────────────────────────────────────────────────────
# FILE LOADING & DETECTION
# ─────────────────────────────────────────────────────────────────────────────

def load_bios_file(file_path, terminal_callback=None):
    """Loads a BIOS file and performs basic validation. Returns: file_data (bytes) or None."""
    path = Path(file_path)

    if not path.exists():
        print_terminal_log(terminal_callback, f"ERROR: File not found: {file_path}", "ERROR")
        return None

    file_size = path.stat().st_size

    if file_size < 512 * 1024:
        print_terminal_log(terminal_callback, "ERROR: Invalid BIOS file size (too small).", "ERROR")
        return None

    try:
        with open(file_path, "rb") as f:
            data = f.read()
        print_terminal_log(terminal_callback, f"BIOS file loaded: {path.name}")
        return data
    except Exception as e:
        print_terminal_log(terminal_callback, f"ERROR: Failed to read file: {str(e)}", "ERROR")
        return None


def detect_spi_flash(data, terminal_callback=None):
    """Analyzes binary data to determine if it is a valid SPI firmware image."""
    size = len(data)
    size_mb = size / (1024 * 1024)
    typical_sizes = [1, 2, 4, 8, 16, 32, 64]
    print_terminal_log(terminal_callback, "Scanning SPI firmware structure...")
    if size_mb in typical_sizes or (size_mb * 1024 % 1024 == 0 and size_mb >= 0.5):
        print_terminal_log(terminal_callback, f"SPI flash image detected (Size: <font color='#ffff00'>{size_mb:.0f} MB</font>)")
        return True
    else:
        print_terminal_log(terminal_callback, f"WARNING: Non-standard SPI flash size: {size_mb:.2f} MB", "WARNING")
        return True


def find_flash_descriptor(data, terminal_callback=None):
    """Searches for Intel Flash Descriptor signature and returns its offset."""
    offset = data.find(INTEL_FD_SIGNATURE)
    if offset != -1:
        return offset
    else:
        if terminal_callback:
            print_terminal_log(terminal_callback, "WARNING: Flash descriptor not detected. Firmware may be non-Intel or corrupted.", "WARNING")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# SPI REGION MAP
# ─────────────────────────────────────────────────────────────────────────────

import hashlib

def get_region_color(rn_lower):
    """Dynamically assigns or generates a color for a given region name."""
    if "descriptor" in rn_lower:
        return "#00FF00"
    elif "me/csme" in rn_lower or "me" in rn_lower or "csme" in rn_lower:
        return "#FF0055"
    elif "bios" in rn_lower:
        return "#00FFFF"
    elif "gbe2" in rn_lower:
        return "#FFD700"
    elif "gbe" in rn_lower:
        return "#FFFF00"
    elif "platform data" in rn_lower:
        return "#FFA500"
    elif "microcode" in rn_lower:
        return "#8A2BE2"
    elif "ec" in rn_lower:
        return "#00FA9A"
    else:
        hash_val = int(hashlib.md5(rn_lower.encode()).hexdigest(), 16)
        r = (hash_val & 0xFF) % 150 + 105
        g = ((hash_val >> 8) & 0xFF) % 150 + 105
        b = ((hash_val >> 16) & 0xFF) % 150 + 105
        return f"#{r:02X}{g:02X}{b:02X}"


def parse_spi_regions(data, signature_offset, terminal_callback=None):
    """Parses the Intel Flash Descriptor to find SPI regions."""
    try:
        desc_base = signature_offset - 0x10
        flmap0 = struct.unpack_from("<I", data, desc_base + 0x14)[0]
        frba_val = (flmap0 >> 16) & 0xFF
        frba_offset = desc_base + (frba_val << 4)

        regions = {}
        region_names = [
            "Descriptor", "BIOS", "ME/CsME", "GbE", "Platform Data",
            "DevExp", "BIOS2", "Microcode", "EC", "GbE2",
            "IE", "PMC", "PCHC", "PHY", "Reserved", "PTT"
        ]

        print_terminal_log(callback=terminal_callback, message=f"Parsing Regions from FRBA at 0x{frba_offset:X}...", level="INFO")

        region_list = []
        for i in range(16):
            reg_val = struct.unpack_from("<I", data, frba_offset + (i * 4))[0]
            base_raw  = reg_val & 0x7FFF
            limit_raw = (reg_val >> 16) & 0x7FFF

            if base_raw == 0x7FFF or limit_raw < base_raw:
                continue

            base  = base_raw << 12
            limit = (limit_raw << 12) | 0x0FFF
            size  = (limit - base) + 1

            name      = region_names[i] if i < len(region_names) else f"Region_{i}"
            safe_name = name.lower().replace("/", "_").replace(" ", "_")
            color     = get_region_color(safe_name)

            regions[safe_name] = {"offset": base, "size": size, "index": i, "color": color}

            size_str = f"{size/1024:.0f} KB" if size < 1024*1024 else f"{size/1024/1024:.2f} MB"
            region_list.append((name, f"0x{base:08X}", f"0x{limit:08X}", size_str, color))

        if region_list:
            def fmt(text, width, color=None, is_link=False):
                padded = text.ljust(width).replace(" ", "&nbsp;")
                if is_link and text.startswith("0x"):
                    padded = padded.replace(text, f'<a href="hexjump:///{text}" style="color:{color}; text-decoration:underline;">{text}</a>', 1)
                if color:
                    return f"<font color='{color}'>{padded}</font>"
                return padded

            print_terminal_log(terminal_callback, f"<font color='#00c8ff'><b>{'━'*50}</b></font>", level=None)
            print_terminal_log(terminal_callback, f"<font color='#00c8ff'><b>📍 SPI REGION MAP</b></font>", level=None)
            print_terminal_log(terminal_callback, f"<font color='#00c8ff'><b>{'━'*50}</b></font>", level=None)

            print_terminal_log(terminal_callback, "╔" + "═"*18 + "╦" + "═"*16 + "╦" + "═"*16 + "╦" + "═"*14 + "╗", level=None)

            h_rn = fmt("REGION NAME", 16)
            h_st = fmt("START OFFSET", 14, "#00f3ff")
            h_en = fmt("END OFFSET",   14, "#00f3ff")
            h_sz = fmt("SIZE",         12)
            print_terminal_log(terminal_callback, f"║&nbsp;{h_rn}&nbsp;║&nbsp;{h_st}&nbsp;║&nbsp;{h_en}&nbsp;║&nbsp;{h_sz}&nbsp;║", level=None)

            print_terminal_log(terminal_callback, "╠" + "═"*18 + "╬" + "═"*16 + "╬" + "═"*16 + "╬" + "═"*14 + "╣", level=None)

            for rn, start, end, sz, color in region_list:
                r_rn = fmt(rn,    16, color)
                r_st = fmt(start, 14, color, is_link=True)
                r_en = fmt(end,   14, color, is_link=True)
                r_sz = fmt(sz,    12, color)
                print_terminal_log(terminal_callback, f"║&nbsp;{r_rn}&nbsp;║&nbsp;{r_st}&nbsp;║&nbsp;{r_en}&nbsp;║&nbsp;{r_sz}&nbsp;║", level=None)

            print_terminal_log(terminal_callback, "╚" + "═"*18 + "╩" + "═"*16 + "╩" + "═"*16 + "╩" + "═"*14 + "╝", level=None)

        return regions
    except Exception as e:
        print_terminal_log(terminal_callback, f"ERROR: Failed to parse SPI regions: {str(e)}", "ERROR")
        return None


def generate_spi_region_report(data, signature_offset, terminal_callback):
    """Report 1 — SPI Region Map."""
    parse_spi_regions(data, signature_offset, terminal_callback)


# ─────────────────────────────────────────────────────────────────────────────
# ME ANALYZER — FETCH OUTPUT (runs once, shared by all MEA-based reports)
# ─────────────────────────────────────────────────────────────────────────────

def fetch_mea_output(file_path, report_settings=None):
    """
    Runs ME Analyzer on the BIOS file with selected settings and returns stdout_text.
    If partition tables (FPT, BPDT, CSE Layout) are requested, passes -dfpt.
    MEA is invoked once; its output is shared among all downstream report functions.
    """
    mea_dir = os.path.join(get_app_root(), "ME Analyzer")
    mea_py  = os.path.join(mea_dir, "MEA.py")

    if not os.path.exists(mea_py):
        return None

    startupinfo = None
    creationflags = 0
    if os.name == 'nt':
        creationflags = 0x08000000
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0

    python_exe = get_python_cmd()
    if report_settings is None:
        report_settings = {}

    needs_dfpt = any([
        report_settings.get("show_flash_partition", False),
        report_settings.get("show_bpdt", False),
        report_settings.get("show_cse_layout", False),
    ])

    cmd = [python_exe, mea_py, file_path, "-skip", "-exit", "-duc", "-dcm"]
    if needs_dfpt:
        cmd.append("-dfpt")

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding='utf-8', errors='ignore',
            creationflags=creationflags, startupinfo=startupinfo,
            env=get_subprocess_env()
        )
        return result.stdout if result else None
    except Exception:
        return None


def _extract_mea_table(mea_output, title_keyword):
    """
    Extracts an ASCII box table from MEA output by its title keyword.
    Starts at the table top border or title and ends at the closing bottom border.
    """
    if not mea_output:
        return []
    lines = []
    recording = False
    for line in mea_output.splitlines():
        s = line.strip()
        if not s:
            if recording and lines and lines[-1].strip().startswith('╚'):
                break
            continue
        if not recording:
            if title_keyword.lower() in s.lower() and any(c in s for c in ['║', '╔']):
                recording = True
                lines.append(line)
        else:
            lines.append(line)
            if s.startswith('╚') and s.endswith('╝'):
                break
            # Guard against runaway recording if another section begins
            if any(k in s for k in [
                "Flash Partition Table", "Boot Partition Descriptor Table",
                "CSE Region Layout Table", "Power Management Controller",
                "Platform Controller Hub"
            ]) and title_keyword.lower() not in s.lower():
                lines.pop()
                break
    return lines


# ─────────────────────────────────────────────────────────────────────────────
# REPORT 9 — NORMAL ANALYZE (BASIC SCAN)
# ─────────────────────────────────────────────────────────────────────────────

def generate_normal_analysis_report(mea_output, terminal_callback):
    """Report 9 — Normal Analyze (Basic Scan output)."""
    if not mea_output:
        print_terminal_log(terminal_callback, "WARNING: ME Analyzer output unavailable for Basic Scan.", "WARNING")
        return

    ui_lines = []
    ui_lines.append("<font color='#A855F7'><b>" + "━"*52 + "</b></font>")
    ui_lines.append("<font color='#A855F7'><b>🔍 NORMAL ANALYZE REPORT (BASIC SCAN)</b></font>")
    ui_lines.append("<font color='#A855F7'><b>" + "━"*52 + "</b></font>")

    skip_next_sep = False
    for line in mea_output.splitlines():
        s = line.strip()
        if any(k in s.lower() for k in ["outdated me analyzer", "outdated database", "download the latest from", "github.com/platomav"]):
            skip_next_sep = True
            continue
        if skip_next_sep and (not s or all(c in "═━-=" for c in s)):
            skip_next_sep = False
            continue
        skip_next_sep = False

        # Replace spaces to preserve horizontal formatting in HTML text browser
        formatted = line.replace(' ', '&nbsp;')
        ui_lines.append(f"<font color='#d0d0e0'>{formatted}</font>")

    for l in ui_lines:
        print_terminal_log(terminal_callback, l)


# ─────────────────────────────────────────────────────────────────────────────
# REPORT 2 — FLASH PARTITION TABLE (FPT)
# ─────────────────────────────────────────────────────────────────────────────

def generate_flash_partition_report(mea_output, terminal_callback):
    """Report 2 — Flash Partition Table (FPT) only."""
    if not mea_output:
        print_terminal_log(terminal_callback, "WARNING: ME Analyzer output unavailable for FPT report.", "WARNING")
        return

    table_lines = _extract_mea_table(mea_output, "Flash Partition Table")
    if not table_lines:
        print_terminal_log(terminal_callback, "<font color='#888'>ℹ Flash Partition Table (FPT) not found in this firmware image.</font>")
        return

    color = '#FFA500'
    print_terminal_log(terminal_callback, f"<font color='{color}'><b>{'━'*52}</b></font>")
    print_terminal_log(terminal_callback, f"<font color='{color}'><b>📋 FLASH PARTITION TABLE  (FPT)</b></font>")
    print_terminal_log(terminal_callback, f"<font color='{color}'><b>{'━'*52}</b></font>")

    for line in table_lines:
        formatted = line.rstrip().replace(' ', '&nbsp;')
        print_terminal_log(terminal_callback, f"<font color='{color}'>{formatted}</font>")


# ─────────────────────────────────────────────────────────────────────────────
# REPORT 3 — BOOT PARTITION DESCRIPTOR TABLE (BPDT / IFWI)
# ─────────────────────────────────────────────────────────────────────────────

def generate_bpdt_report(mea_output, terminal_callback):
    """Report 3 — Boot Partition Descriptor Table (BPDT / IFWI)."""
    if not mea_output:
        print_terminal_log(terminal_callback, "WARNING: ME Analyzer output unavailable for BPDT report.", "WARNING")
        return

    table_lines = _extract_mea_table(mea_output, "Boot Partition Descriptor Table")
    if not table_lines:
        print_terminal_log(terminal_callback, "<font color='#888'>ℹ Boot Partition Descriptor Table (BPDT) not found in this firmware image.</font>")
        return

    color = '#9C27B0'
    print_terminal_log(terminal_callback, f"<font color='{color}'><b>{'━'*52}</b></font>")
    print_terminal_log(terminal_callback, f"<font color='{color}'><b>🗂 BOOT PARTITION DESCRIPTOR TABLE  (BPDT / IFWI)</b></font>")
    print_terminal_log(terminal_callback, f"<font color='{color}'><b>{'━'*52}</b></font>")

    for line in table_lines:
        formatted = line.rstrip().replace(' ', '&nbsp;')
        print_terminal_log(terminal_callback, f"<font color='{color}'>{formatted}</font>")


# ─────────────────────────────────────────────────────────────────────────────
# REPORT 4 — CSE LAYOUT TABLE (LT)
# ─────────────────────────────────────────────────────────────────────────────

def generate_cse_layout_report(mea_output, terminal_callback):
    """Report 4 — CSE Layout Table (Code/Data partition layout)."""
    if not mea_output:
        print_terminal_log(terminal_callback, "WARNING: ME Analyzer output unavailable for CSE Layout report.", "WARNING")
        return

    table_lines = _extract_mea_table(mea_output, "CSE Region Layout Table")
    if not table_lines:
        table_lines = _extract_mea_table(mea_output, "CSE Layout Table")
    if not table_lines:
        print_terminal_log(terminal_callback, "<font color='#888'>ℹ CSE Layout Table not found in this firmware image.</font>")
        return

    color = '#FFD700'
    print_terminal_log(terminal_callback, f"<font color='{color}'><b>{'━'*52}</b></font>")
    print_terminal_log(terminal_callback, f"<font color='{color}'><b>🏗 CSE LAYOUT TABLE  (LT)</b></font>")
    print_terminal_log(terminal_callback, f"<font color='{color}'><b>{'━'*52}</b></font>")

    for line in table_lines:
        formatted = line.rstrip().replace(' ', '&nbsp;')
        print_terminal_log(terminal_callback, f"<font color='{color}'>{formatted}</font>")


# ─────────────────────────────────────────────────────────────────────────────
# REPORT 5 — BIOS ANALYSIS REPORT (ME/CSME main info)
# ─────────────────────────────────────────────────────────────────────────────

def generate_bios_analysis_report(mea_output, terminal_callback=None, legacy_param=None):
    """
    Report 5 — BIOS / ME Analysis Report.
    Extracts Family, Version, SKU, Release, Type, Platform/Chipset, Date, Health, etc.
    Compatible with calls passing (mea_output, mea_json, terminal_callback) or (mea_output, terminal_callback).
    """
    if callable(legacy_param):
        terminal_callback = legacy_param
    elif callable(terminal_callback):
        pass
    elif callable(mea_output):
        terminal_callback = mea_output

    if not mea_output or not isinstance(mea_output, str):
        print_terminal_log(terminal_callback, "WARNING: ME Analyzer output unavailable for BIOS Analysis.", "WARNING")
        return

    color = '#00ff88'
    ALLOWED_KEYS = {
        "Family": "Family",
        "Version": "Version",
        "Release": "Release",
        "Type": "Type",
        "SKU": "SKU",
        "Chipset": "Platform / Chipset",
        "TCB Security Version Number": "TCB SVN",
        "ARB Security Version Number": "ARB SVN",
        "Version Control Number": "VCN",
        "Production Ready": "Production Ready",
        "OEM Configuration": "OEM Config",
        "FWUpdate Support": "FWUpdate Support",
        "Date": "Release Date",
        "File System State": "File System / Health",
        "Size": "Firmware Size",
        "Flash Image Tool": "FIT Version",
        "Latest": "Latest Version Available",
    }

    in_me_table = False
    found_rows = []

    for line in mea_output.splitlines():
        s = line.strip()
        if not s:
            continue

        # Detect start of main Engine/ME table
        if ("Family" in s and any(k in s for k in ['ME', 'TXE', 'SPS', 'CSE'])) and ('│' in s or '║' in s):
            in_me_table = True

        # Stop when independent firmware or partition table starts
        if in_me_table and any(x in s for x in [
            "Power Management Controller", "Platform Controller Hub",
            "USB Physical Layer", "USB Type-C", "Flash Partition Table",
            "Boot Partition Descriptor Table", "CSE Region Layout Table"
        ]):
            in_me_table = False
            break

        if in_me_table:
            if s.startswith('╚') and s.endswith('╝'):
                in_me_table = False
                break

            cleaned = s.strip('║│| \t')
            if '│' in cleaned:
                parts = cleaned.split('│')
            elif '|' in cleaned:
                parts = cleaned.split('|')
            else:
                parts = []

            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip()
                if key in ALLOWED_KEYS and val:
                    found_rows.append((ALLOWED_KEYS[key], val))

    if not found_rows:
        print_terminal_log(terminal_callback, "<font color='#888'>ℹ No Intel ME/CSME firmware details detected.</font>")
        return

    print_terminal_log(terminal_callback, f"<font color='{color}'><b>{'━'*52}</b></font>")
    print_terminal_log(terminal_callback, f"<font color='{color}'><b>🔍 BIOS / ME ANALYSIS REPORT</b></font>")
    print_terminal_log(terminal_callback, f"<font color='{color}'><b>{'━'*52}</b></font>")
    print_terminal_log(terminal_callback, "<font color='#00ff88'>╔" + "═"*24 + "╦" + "═"*32 + "╗</font>")

    for label, val in found_rows:
        k = label.ljust(22).replace(' ', '&nbsp;')
        v = val.ljust(30).replace(' ', '&nbsp;')
        row_html = (
            f"<font color='#00ff88'>║&nbsp;</font>"
            f"<font color='#ffffff'><b>{k}</b></font>"
            f"<font color='#00ff88'>&nbsp;║&nbsp;</font>"
            f"<font color='#ffff00'><b>{v}</b></font>"
            f"<font color='#00ff88'>&nbsp;║</font>"
        )
        print_terminal_log(terminal_callback, row_html)

    print_terminal_log(terminal_callback, "<font color='#00ff88'>╚" + "═"*24 + "╩" + "═"*32 + "╝</font>")


# ─────────────────────────────────────────────────────────────────────────────
# REPORT 6 — PMC / PCHC / PHY INDEPENDENT FIRMWARE
# ─────────────────────────────────────────────────────────────────────────────

def generate_pmc_pchc_phy_report(mea_output, terminal_callback):
    """Report 6 — Power Management Controller, PCHC and USB PHY firmware info."""
    if not mea_output:
        print_terminal_log(terminal_callback, "WARNING: ME Analyzer output unavailable for PMC/PCHC/PHY report.", "WARNING")
        return

    SECTION_MARKERS = {
        "Power Management Controller": ("#00f3ff", "⚡ POWER MANAGEMENT CONTROLLER  (PMC)"),
        "Platform Controller Hub": ("#4FC3F7", "🔧 PLATFORM CONTROLLER HUB CONFIG  (PCHC)"),
        "Physical Layer": ("#26C6DA", "🔌 USB TYPE-C PHYSICAL LAYER  (PHY)"),
        "Graphics Option ROM": ("#80DEEA", "🎮 GRAPHICS OPTION ROM  (OROM)"),
    }

    current_sec = None
    sections = {}

    for line in mea_output.splitlines():
        s = line.strip()
        if not s:
            continue

        matched = None
        for marker, (color, title) in SECTION_MARKERS.items():
            if marker in s and not any(c in s for c in ['│', '|']):
                matched = (marker, color, title)
                break

        if matched:
            current_sec = matched
            sections[current_sec[2]] = (current_sec[1], [])
            continue

        if current_sec:
            if s.startswith('╚') and s.endswith('╝'):
                current_sec = None
                continue

            cleaned = s.strip('║│| \t')
            parts = [p.strip() for p in cleaned.split('│')] if '│' in cleaned else [p.strip() for p in cleaned.split('|')]
            if len(parts) == 2 and parts[0] and parts[1]:
                sections[current_sec[2]][1].append((parts[0], parts[1]))

    found_any = False
    for title, (col, rows) in sections.items():
        if rows:
            found_any = True
            print_terminal_log(terminal_callback, f"<font color='{col}'><b>{'━'*52}</b></font>")
            print_terminal_log(terminal_callback, f"<font color='{col}'><b>{title}</b></font>")
            print_terminal_log(terminal_callback, f"<font color='{col}'><b>{'━'*52}</b></font>")
            print_terminal_log(terminal_callback, f"<font color='{col}'>╔" + "═"*28 + "╦" + "═"*28 + "╗</font>")
            for k, v in rows:
                k_pad = k.ljust(26).replace(' ', '&nbsp;')
                v_pad = v.ljust(26).replace(' ', '&nbsp;')
                row_html = (
                    f"<font color='{col}'>║&nbsp;</font>"
                    f"<font color='#ffffff'>{k_pad}</font>"
                    f"<font color='{col}'>&nbsp;║&nbsp;</font>"
                    f"<font color='#ffff00'><b>{v_pad}</b></font>"
                    f"<font color='{col}'>&nbsp;║</font>"
                )
                print_terminal_log(terminal_callback, row_html)
            print_terminal_log(terminal_callback, f"<font color='{col}'>╚" + "═"*28 + "╩" + "═"*28 + "╝</font>")

    if not found_any:
        print_terminal_log(terminal_callback, "<font color='#555'>ℹ No PMC/PCHC/PHY independent firmware found in this image.</font>")


# ─────────────────────────────────────────────────────────────────────────────
# REPORT 7 — ME FIRMWARE WARNINGS & NOTES
# ─────────────────────────────────────────────────────────────────────────────

def generate_me_warnings_report(mea_output, terminal_callback):
    """Report 7 — ME Analyzer Notes, Warnings, Errors and Advisory messages."""
    if not mea_output:
        print_terminal_log(terminal_callback, "WARNING: ME Analyzer output unavailable for Warnings report.", "WARNING")
        return

    WARNING_KEYWORDS = ("Warning:", "Error:", "Note:", "Advisory:")
    found = []

    IGNORE_WARNINGS = ("outdated me analyzer", "outdated database", "download the latest from", "github.com/platomav")

    for line in mea_output.splitlines():
        s = line.strip()
        if not s: continue
        if any(ign in s.lower() for ign in IGNORE_WARNINGS):
            continue
        for kw in WARNING_KEYWORDS:
            if kw in s:
                found.append((kw, s))
                break

    color_map = {
        "Warning:":  "#FFA500",
        "Error:":    "#FF4444",
        "Note:":     "#00f3ff",
        "Advisory:": "#FFD700",
    }

    if not found:
        print_terminal_log(terminal_callback, "<font color='#555'>✅ No warnings or errors detected by ME Analyzer.</font>")
        return

    print_terminal_log(terminal_callback, f"<font color='#FF4444'><b>{'━'*52}</b></font>")
    print_terminal_log(terminal_callback, f"<font color='#FF4444'><b>⚠ ME FIRMWARE NOTES &amp; WARNINGS</b></font>")
    print_terminal_log(terminal_callback, f"<font color='#FF4444'><b>{'━'*52}</b></font>")

    for kw, msg in found:
        col = color_map.get(kw, "#AAAAAA")
        safe = msg.replace(' ', '&nbsp;')
        print_terminal_log(terminal_callback, f"<font color='{col}'>{safe}</font>")


# ─────────────────────────────────────────────────────────────────────────────
# REPORT 8 — INTEL MICROCODE AUDIT (via MCExtractor)
# ─────────────────────────────────────────────────────────────────────────────

def generate_microcode_report(file_path, terminal_callback):
    """
    Report 8 — Intel Microcode Audit using MCExtractor (MCE.py + MCE.db).
    Parses the microcode entries embedded in the BIOS image.
    """
    color  = '#ff88ff'
    mce_dir = os.path.join(get_app_root(), "MCExtractor")
    mce_py  = os.path.join(mce_dir, "MCE.py")
    mce_db  = os.path.join(mce_dir, "MCE.db")

    print_terminal_log(terminal_callback, f"<font color='{color}'><b>{'━'*52}</b></font>")
    print_terminal_log(terminal_callback, f"<font color='{color}'><b>🧮 INTEL MICROCODE AUDIT</b></font>")
    print_terminal_log(terminal_callback, f"<font color='{color}'><b>{'━'*52}</b></font>")

    if not os.path.exists(mce_py):
        print_terminal_log(terminal_callback, "<font color='#FF4444'>❌ MCExtractor not found. Place MCE.py and MCE.db in the MCExtractor/ folder.</font>")
        return
    if not os.path.exists(mce_db):
        print_terminal_log(terminal_callback, "<font color='#FF4444'>❌ MCE.db database not found inside MCExtractor/ folder.</font>")
        return

    startupinfo = None
    creationflags = 0
    if os.name == 'nt':
        creationflags = 0x08000000
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0

    python_exe = get_python_cmd()
    # -skip  → skip interactive prompts
    # -exit  → no "press enter" at end
    # -duc   → disable update check
    cmd = [python_exe, mce_py, file_path, "-skip", "-exit", "-duc"]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding='utf-8', errors='ignore',
            creationflags=creationflags, startupinfo=startupinfo,
            env=get_subprocess_env()
        )
        output = result.stdout or ""
    except Exception as e:
        print_terminal_log(terminal_callback, f"<font color='#FF4444'>❌ MCExtractor failed: {str(e)}</font>")
        return

    if not output.strip():
        print_terminal_log(terminal_callback, "<font color='#888'>ℹ MCExtractor returned no output. No microcode entries found.</font>")
        return

    SKIP_MCE = {"MC Extractor v", "Intel, AMD", "Copyright", "Press enter",
                "Option(s):", "Files:", "Download"}

    entries_found = 0
    for line in output.splitlines():
        s = line.strip()
        if not s: continue
        if any(x in s for x in SKIP_MCE): continue

        is_border = any(c in s for c in ['╔', '╚', '╠', '═', '╩', '╦'])
        if is_border:
            print_terminal_log(terminal_callback, f"<font color='{color}'>{line.rstrip().replace(' ', '&nbsp;')}</font>")
            continue

        if s.count('║') >= 3:
            parts = s.split('║')
            if len(parts) >= 3:
                key   = parts[1].strip()
                value = parts[2].split('|')[0].strip()
                if key and value:
                    entries_found += 1
                    text = f"║ {key:18} ║ {value:28} ║".replace(' ', '&nbsp;')
                    print_terminal_log(terminal_callback, f"<font color='{color}'>{text}</font>")
        elif s.count('║') == 2:
            print_terminal_log(terminal_callback, f"<font color='{color}'>{line.rstrip().replace(' ', '&nbsp;')}</font>")
        elif not any(c in s for c in ['║', '╔', '═']):
            print_terminal_log(terminal_callback, f"<font color='{color}'>{line.rstrip().replace(' ', '&nbsp;')}</font>")

    if entries_found == 0:
        print_terminal_log(terminal_callback, "<font color='#888'>ℹ No Intel Microcode entries detected in this image.</font>")


# ─────────────────────────────────────────────────────────────────────────────
# DISPATCHER — Main Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def get_bios_metadata(file_path, terminal_callback=None, mea_handler=None, report_settings=None, raw_data=None):
    """
    Main entry point for BIOS parsing logic.
    Reads configuration and dispatches each independent report independently.
    Returns structured data for the application core.
    """
    if report_settings is None:
        report_settings = {}

    # ── 1. Silent internal parse ──────────────────────────────────────────────
    if raw_data is not None:
        data = raw_data
    else:
        data = load_bios_file(file_path, None)
    if not data:
        return None

    descriptor_offset = find_flash_descriptor(data, None)

    regions = None
    if descriptor_offset is not None:
        regions = parse_spi_regions(data, descriptor_offset, terminal_callback=None)
        firmware_type = "AMD SPI" if (b'AuthenticAMD' in data or b'AGESA' in data) else "Intel SPI"
    else:
        firmware_type = "AMD SPI" if (b'AuthenticAMD' in data or b'AGESA' in data) else "Unknown"

    file_size_mb = len(data) // (1024 * 1024)

    # ── 2. Read configuration ─────────────────────────────────────────────────
    show_spi      = report_settings.get("show_spi_region_map",  True)
    show_fpt      = report_settings.get("show_flash_partition",  True)
    show_bpdt     = report_settings.get("show_bpdt",             True)
    show_cse      = report_settings.get("show_cse_layout",       True)
    show_normal   = report_settings.get("show_normal_analysis",  False)
    show_bios     = report_settings.get("show_bios_analysis",    True)
    show_pmc      = report_settings.get("show_pmc_pchc_phy",     False)
    show_warnings = report_settings.get("show_me_warnings",      True)
    show_micro    = report_settings.get("show_microcode",         True)

    needs_mea = any([show_fpt, show_bpdt, show_cse, show_bios, show_pmc, show_warnings, show_normal])

    # ── 3. Guard: nothing selected ────────────────────────────────────────────
    if not any([show_spi, show_fpt, show_bpdt, show_cse,
                show_bios, show_pmc, show_warnings, show_micro, show_normal]):
        print_terminal_log(terminal_callback, "⚠ WARNING: No reports selected. All report options are disabled.", "WARNING")
        if mea_handler:
            mea_handler([], [])
        return {"file_size": len(data), "firmware_type": firmware_type,
                "descriptor_offset": descriptor_offset, "regions": regions}

    # ── 4. Report 1: SPI Region Map (synchronous — fast) ─────────────────────
    if show_spi:
        print_terminal_log(terminal_callback, f"BIOS file loaded: {Path(file_path).name}")
        detect_spi_flash(data, terminal_callback)
        if descriptor_offset is not None:
            print_terminal_log(terminal_callback, f"Intel Flash Descriptor found at offset 0x{descriptor_offset:X}")
        print_terminal_log(terminal_callback, f"Firmware Size: <font color='#ffff00'>{file_size_mb} MB</font>")
        print_terminal_log(terminal_callback, f"Firmware Type: <font color='#00f3ff'><b>{firmware_type}</b></font>")

        if descriptor_offset is not None:
            generate_spi_region_report(data, descriptor_offset, terminal_callback)

    # ── 5. Reports 2-7: MEA-based (async — single MEA run) ───────────────────
    if needs_mea or show_micro:
        def _run_async():
            mea_stdout = None

            if needs_mea:
                print_terminal_log(terminal_callback, "[INFO] Starting ME Analyzer...")
                mea_stdout = fetch_mea_output(file_path, report_settings=report_settings)

            # Report 2 — FPT
            if show_fpt:
                generate_flash_partition_report(mea_stdout, terminal_callback)

            # Report 3 — BPDT
            if show_bpdt:
                generate_bpdt_report(mea_stdout, terminal_callback)

            # Report 4 — CSE Layout Table
            if show_cse:
                generate_cse_layout_report(mea_stdout, terminal_callback)

            # Report 5 — BIOS Analysis
            if show_bios:
                generate_bios_analysis_report(mea_stdout, terminal_callback)

            # Report 6 — PMC / PCHC / PHY
            if show_pmc:
                generate_pmc_pchc_phy_report(mea_stdout, terminal_callback)

            # Report 7 — Warnings
            if show_warnings:
                generate_me_warnings_report(mea_stdout, terminal_callback)

            # Report 9 — Normal Analyze (Basic Scan)
            if show_normal:
                generate_normal_analysis_report(mea_stdout, terminal_callback)

            # Report 8 — Microcode (separate MCExtractor subprocess)
            if show_micro:
                generate_microcode_report(file_path, terminal_callback)

            # Done
            print_terminal_log(terminal_callback, "═" * 52)
            print_terminal_log(terminal_callback, "[SUCCESS] Report generation complete.")
            if mea_handler:
                raw_file_lines = mea_stdout.splitlines() if mea_stdout else []
                mea_handler([], raw_file_lines)

        t = threading.Thread(target=_run_async, daemon=True)
        t.start()
    else:
        # Only SPI was selected (no async needed)
        if mea_handler:
            mea_handler([], [])

    return {
        "file_size":         len(data),
        "firmware_type":     firmware_type,
        "descriptor_offset": descriptor_offset,
        "regions":           regions,
    }
