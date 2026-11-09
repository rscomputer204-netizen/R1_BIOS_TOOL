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

    # 1. HP BIOS Family detection (e.g. 'T87 Ver. 01.08.02', '0887D Ver. F.20', 'Q78 Ver. 01.05.00')
    # Pattern: 2-8 alphanumeric characters followed by 'Ver.'
    fam_matches = re.findall(
        rb'(?:(?<=[\x00\xff/_\s])|^)([A-Za-z0-9_-]{2,8})\s+Ver[.]?\s*([0-9A-Za-z._]{3,15})',
        data
    )
    ignored_families = {
        'KBC', 'BINARY', 'COMPATIBLE', 'COPY', 'COPYRIGHT', 'INTEL',
        'AMD', 'VERSION', 'FLASH', 'BUILD', 'SION', 'CODE', 'SIGN', 'ME'
    }

    for fam_bytes, ver_bytes in fam_matches:
        try:
            f_str = fam_bytes.decode('ascii', errors='ignore').strip().upper()
            v_str = ver_bytes.decode('ascii', errors='ignore').strip()
            if f_str and f_str not in ignored_families and len(f_str) >= 2:
                # Discard purely numeric or generic strings
                if not f_str.isdigit() and f_str not in [x['family'] for x in info["board_families"]]:
                    info["board_families"].append({"family": f_str, "version": v_str})
                    if not info["primary_family"]:
                        info["primary_family"] = f_str
                        info["primary_version"] = v_str
        except Exception:
            pass

    # 2. HP BID Detection: e.g. 'BID 0887D', 'BID:0887D', '$BID0887D'
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

    # 3. Check for HP DMI strings or identifiers
    if b"Hewlett-Packard" in data or b"HP " in data or b"103C_" in data:
        info["detected_brand"] = "HP"
    elif b"Dell" in data or b"DELL" in data:
        info["detected_brand"] = "Dell"
    elif b"LENOVO" in data or b"ThinkPad" in data:
        info["detected_brand"] = "Lenovo"

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


def evaluate_candidate(cand_path: str, orig_data: bytes, board_info: dict) -> dict:
    """
    Calculates matching score and recommendation metadata for a single candidate file.
    """
    filename = os.path.basename(cand_path)
    base_name = os.path.splitext(filename)[0]
    try:
        size_bytes = os.path.getsize(cand_path)
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

    primary_fam = board_info.get("primary_family")
    known_families = [f["family"] for f in board_info.get("board_families", [])]
    known_bids = board_info.get("board_ids", [])

    # Check 1: Direct match with detected primary board family (Highest Confidence: 100%)
    if primary_fam and (cand_token == primary_fam or cand_token.startswith(primary_fam) or primary_fam.startswith(cand_token)):
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
    if not is_match and primary_fam:
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

