"""
R1 BIOS Tool — Smart Board ID & Family Matcher Engine
=====================================================
Analyzes loaded original BIOS dumps and matches extracted update candidates
(e.g. from HP SoftPaq, Dell, Lenovo packages) to guarantee that the technician
flashes the correct board revision and avoids black screen / bricked boards.
"""

import os
import re
import math
from pathlib import Path


def format_size(size_bytes: int) -> str:
    """Formats bytes into human readable KB/MB string."""
    if not size_bytes or size_bytes <= 0:
        return "0 B"
    size_names = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"


def detect_board_info(orig_bios_path_or_data) -> dict:
    """
    Scans the loaded original BIOS dump for Board IDs, BIOS Families,
    and platform identifiers (HP, Lenovo, Dell, ASUS).
    """
    info = {
        "board_families": [],       # e.g. [{'family': 'T87', 'version': '01.08.02'}]
        "primary_family": None,     # e.g. 'T87'
        "primary_version": None,    # e.g. '01.08.02'
        "board_ids": [],            # e.g. ['0887D', 'T87']
        "detected_brand": "Unknown",
        "details_summary": ""
    }

    data = None
    if isinstance(orig_bios_path_or_data, (str, Path)):
        if os.path.exists(orig_bios_path_or_data):
            try:
                with open(orig_bios_path_or_data, "rb") as f:
                    data = f.read()
            except Exception:
                return info
    elif isinstance(orig_bios_path_or_data, (bytes, bytearray)):
        data = bytes(orig_bios_path_or_data)

    if not data:
        return info

    # 1. Brand Detection (Strict multi-byte signatures)
    if b"LENOVO" in data or b"ThinkPad" in data or b"Lenovo" in data:
        info["detected_brand"] = "Lenovo"
    elif b"Hewlett-Packard" in data or b"HP BIOS" in data or b"103C_" in data or b"HP Inc." in data:
        info["detected_brand"] = "HP"
    elif b"Dell" in data or b"DELL" in data:
        info["detected_brand"] = "Dell"
    elif b"ASUSTeK" in data or b"ASUS" in data:
        info["detected_brand"] = "ASUS"

    # 2. Lenovo ThinkPad Detection
    if info["detected_brand"] == "Lenovo":
        tp_matches = re.findall(rb'([A-Z0-9]{3})(ET)([0-9]{2})W', data)
        if tp_matches:
            fam_bytes, tag_bytes, ver_bytes = tp_matches[-1]
            fam = fam_bytes.decode('ascii', errors='ignore')
            ver = f"{fam}ET{ver_bytes.decode('ascii', errors='ignore')}W"
            info["board_families"].append({"family": fam, "version": ver})
            info["primary_family"] = fam
            info["primary_version"] = ver
            info["board_ids"].append(fam)
            info["board_ids"].append(f"{fam}ET")
        else:
            tp_any = re.findall(rb'([A-Z0-9]{3})(?:HT|RM)([0-9]{2})W', data)
            if tp_any:
                fam = tp_any[-1][0].decode('ascii', errors='ignore')
                info["primary_family"] = fam
                info["board_ids"].append(fam)

    # 3. HP BIOS Family detection (only if brand is HP or unknown)
    if info["detected_brand"] in ("HP", "Unknown"):
        fam_matches = re.findall(
            rb'(?:(?<=[\x00\xff/_\s])|^)([A-Za-z0-9_-]{2,8})\s+Ver[.]?\s*([0-9A-Za-z._]{3,15})',
            data
        )
        ignored_families = {
            'KBC', 'BINARY', 'COMPATIBLE', 'COPY', 'COPYRIGHT', 'INTEL',
            'AMD', 'VERSION', 'FLASH', 'BUILD', 'SION', 'CODE', 'SIGN', 'ME',
            'IP', 'TCP', 'UDP', 'HTTP', 'IPV4', 'IPV6', 'STACK', 'DRIVER',
            'SERVER', 'CLIENT', 'TYPE2', 'REV', 'TYPE', 'DATA', 'FILE', 'BIOS',
            'BOOT', 'CORE', 'SYS', 'ACPI', 'TABLE', 'TABLES'
        }

        for fam_bytes, ver_bytes in fam_matches:
            try:
                f_str = fam_bytes.decode('ascii', errors='ignore').strip().upper()
                v_str = ver_bytes.decode('ascii', errors='ignore').strip()
                if f_str and f_str not in ignored_families and len(f_str) >= 2:
                    if not f_str.isdigit() and f_str not in [x['family'] for x in info["board_families"]]:
                        info["board_families"].append({"family": f_str, "version": v_str})
                        if not info["primary_family"]:
                            info["primary_family"] = f_str
                            info["primary_version"] = v_str
            except Exception:
                pass

        # HP BID Detection
        bid_matches = re.findall(rb'(?:BID\s*[:=]\s*|\$BID\s*)([A-Za-z0-9]{3,8})', data)
        for b_bytes in bid_matches:
            try:
                b_str = b_bytes.decode('ascii', errors='ignore').strip().upper()
                if b_str and b_str not in info["board_ids"] and b_str not in ignored_families:
                    info["board_ids"].append(b_str)
                    if not info["primary_family"]:
                        info["primary_family"] = b_str
            except Exception:
                pass

    if info["primary_family"]:
        v_part = f" (v{info['primary_version']})" if info["primary_version"] else ""
        info["details_summary"] = f"Board / Family: {info['primary_family']}{v_part}"

    return info


def parse_candidate_version(filename: str) -> str:
    """Extracts human-readable version from candidate filename if present."""
    base = os.path.splitext(filename)[0]
    # e.g. T87_01250100 -> 01.25.01
    parts = base.split('_')
    if len(parts) > 1:
        raw_ver = parts[1]
        if len(raw_ver) == 8 and raw_ver.isdigit():
            # 01250100 -> 01.25.01
            return f"{raw_ver[:2]}.{raw_ver[2:4]}.{raw_ver[4:6]}"
        elif len(raw_ver) >= 4 and raw_ver.isalnum():
            return raw_ver
    return ""


def safe_path(p: str) -> str:
    """Returns extended-length path on Windows to avoid MAX_PATH (260) limitations."""
    if not p:
        return p
    p_abs = os.path.abspath(p)
    if os.name == 'nt' and not p_abs.startswith('\\\\?\\'):
        return '\\\\?\\' + p_abs
    return p_abs


def evaluate_candidate(cand_path: str, orig_data: bytes, board_info: dict) -> dict:
    """
    Calculates matching score and recommendation metadata for a single candidate file.
    """
    cand_path_safe = safe_path(cand_path)
    filename = os.path.basename(cand_path)
    base_name, ext = os.path.splitext(filename)
    ext = ext.lower()
    parent_dir = os.path.basename(os.path.dirname(cand_path))
    try:
        size_bytes = os.path.getsize(cand_path_safe)
    except Exception:
        size_bytes = 0

    size_str = format_size(size_bytes)
    cand_version = parse_candidate_version(filename)

    # Extract prefix / token (e.g. T87 from T87_01250100.bin)
    tokens = [t for t in re.split(r'[_.-]', base_name) if len(t) >= 2]
    cand_token = tokens[0].upper() if tokens else base_name.upper()

    score = 0
    matched_id = None
    reason = "No board identifier match found."
    is_match = False

    # Check Reset Vector match against original dump
    if orig_data and len(orig_data) >= 64 and size_bytes >= 64:
        try:
            with open(cand_path_safe, "rb") as cf:
                cf.seek(size_bytes - 64)
                cand_tail = cf.read(64)
            if cand_tail == orig_data[-64:] or cand_tail[-16:] == orig_data[-16:]:
                score = 100
                is_match = True
                matched_id = "Reset Vector Match"
                reason = "Exact match with loaded BIOS Entry Point & Reset Vector."
        except Exception:
            pass

    # Check CPU Flavor match (e.g. U-series vs H-series, Low Power LP vs Standard H)
    fname_upper = filename.upper()
    is_u_flavor = any(k in fname_upper for k in ["-U", "_U", " U ", "VPRO LP", "BRECKENRIDGE-U"])
    is_h_flavor = any(k in fname_upper for k in ["-H", "_H", " H ", "VPRO H", "BRECKENRIDGE-H"])

    if orig_data:
        orig_data_upper = orig_data.upper()
        # Check if dump has Low Power LP or KBP-LP or SPT-LP
        has_lp = (b"-LP" in orig_data or b"KBP-LP" in orig_data or b"SPT-LP" in orig_data or
                  b"LP SERIES" in orig_data_upper or b"CORPORATE LP" in orig_data_upper or b"CONSUMER LP" in orig_data_upper)
        has_h = (b"-H" in orig_data or b"KBP-H" in orig_data or b"SPT-H" in orig_data or
                 b"H SERIES" in orig_data_upper or b"CORPORATE H" in orig_data_upper or b"CONSUMER H" in orig_data_upper)

        # Direct board string match in dump (e.g. Breckenridge-U / Breckenridge-H)
        for b_name in ["BRECKENRIDGE-U", "BRECKENRIDGE-H"]:
            if b_name.encode('ascii') in orig_data_upper:
                if b_name in fname_upper:
                    score += 200
                    matched_id = b_name
                    is_match = True
                    reason = f"Exact Board Model Matched in Backup: {b_name}"

        if is_u_flavor and has_lp:
            score += 150
            if not matched_id or matched_id == "Reset Vector Match":
                matched_id = "U-Series (LP Match)"
                reason = "Matches Low-Power (U-Series / LP) Processor & Chipset Architecture."
        elif is_h_flavor and has_h:
            score += 150
            if not matched_id or matched_id == "Reset Vector Match":
                matched_id = "H-Series (HQ Match)"
                reason = "Matches High-Performance (H-Series / HQ) Processor Architecture."
        elif is_u_flavor and has_h:
            score -= 100
        elif is_h_flavor and has_lp:
            score -= 100

    primary_fam = board_info.get("primary_family")
    known_families = [f["family"] for f in board_info.get("board_families", [])]
    known_bids = board_info.get("board_ids", [])

    # Special Case: Lenovo ThinkPad update packages (.FL1 = Main BIOS, .FL2 = EC)
    if ext == ".fl1":
        p_str = f" ({parent_dir})" if parent_dir else ""
        if primary_fam and (primary_fam in base_name.upper() or (parent_dir and primary_fam in parent_dir.upper())):
            score = 100
            matched_id = f"{primary_fam}{p_str}"
            is_match = True
            v_orig = board_info.get("primary_version", "")
            reason = f"Matches Motherboard BIOS Family: {primary_fam}{f' (Backup {v_orig} -> Update {parent_dir})' if v_orig and parent_dir else ''}"
        elif board_info.get("detected_brand") == "Lenovo":
            score = 90
            matched_id = f"Lenovo BIOS{p_str}"
            is_match = True
            reason = f"Lenovo Main System BIOS Image{p_str}."
        else:
            score = 80
            matched_id = "Main BIOS (.FL1)"
            is_match = True
            reason = "Main System BIOS Firmware Image."
    elif ext in (".fl2", ".fl3"):
        score = 20
        matched_id = "EC Firmware"
        is_match = False
        reason = "EC/KBC Firmware (Not Main System BIOS Region)."
    elif ext == ".efi":
        score = 10
        matched_id = "EFI Utility"
        is_match = False
        reason = "EFI Executable/Utility (Not System BIOS Image)."

    # Check 1: Direct match with detected primary board family (Highest Confidence: 100%)
    elif primary_fam and (cand_token == primary_fam or cand_token.startswith(primary_fam) or primary_fam.startswith(cand_token)):
        score = 100
        matched_id = primary_fam
        is_match = True
        v_orig = board_info.get("primary_version", "")
        v_cand = f" → Update v{cand_version}" if cand_version else ""
        reason = f"Matches Motherboard Board ID: {primary_fam}{f' (v{v_orig})' if v_orig else ''}{v_cand}"

    # Check 2: Match with any detected secondary family
    elif any(cand_token == kf for kf in known_families):
        score = 90
        matched_id = cand_token
        is_match = True
        reason = f"Matches Motherboard BIOS Family: {cand_token}"

    # Check 3: Match with detected Board IDs (BIDs)
    elif any(cand_token == kb for kb in known_bids):
        score = 85
        matched_id = cand_token
        is_match = True
        reason = f"Matches Motherboard Board ID (BID): {cand_token}"

    # Check 4: Fast pattern search in original binary for '<cand_token> Ver.'
    elif orig_data:
        tok_bytes = cand_token.encode('ascii', errors='ignore')
        pattern_ver = tok_bytes + b' Ver.'
        idx = orig_data.find(pattern_ver)
        if idx != -1:
            score = 95
            matched_id = cand_token
            is_match = True
            ver_slice = orig_data[idx+len(pattern_ver):idx+len(pattern_ver)+15]
            detected_ver = ver_slice.split(b'\x00')[0].decode('ascii', errors='ignore').strip()
            v_cand = f" → Update v{cand_version}" if cand_version else ""
            reason = f"Matches Board Family in Firmware: {cand_token} (Backup v{detected_ver}){v_cand}"

    # If no match:
    if not is_match and primary_fam and reason == "No board identifier match found.":
        reason = f"Board Mismatch: Package is for '{cand_token}', but loaded board is '{primary_fam}'."

    return {
        "path": cand_path,
        "filename": filename,
        "token": cand_token,
        "size_bytes": size_bytes,
        "size_str": size_str,
        "cand_version": cand_version,
        "score": score,
        "is_match": is_match,
        "matched_id": matched_id or cand_token,
        "reason": reason
    }


def rank_candidates(candidate_paths: list, orig_bios_path_or_data) -> tuple[list, dict]:
    """
    Scores and ranks all candidate files against the original BIOS dump.
    Returns: (ranked_candidates_list, detected_board_info)
    The best matching file will always be at index 0.
    """
    board_info = detect_board_info(orig_bios_path_or_data)

    orig_data = None
    if isinstance(orig_bios_path_or_data, (str, Path)) and os.path.exists(orig_bios_path_or_data):
        try:
            with open(orig_bios_path_or_data, "rb") as f:
                orig_data = f.read()
        except Exception:
            pass
    elif isinstance(orig_bios_path_or_data, (bytes, bytearray)):
        orig_data = bytes(orig_bios_path_or_data)

    evaluated = []
    for p in candidate_paths:
        res = evaluate_candidate(p, orig_data, board_info)
        evaluated.append(res)

    # Sort: matched files first, highest score first, then by filename
    evaluated.sort(key=lambda x: (x["score"], x["size_bytes"]), reverse=True)
    return evaluated, board_info

