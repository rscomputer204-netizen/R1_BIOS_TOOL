"""
lenovo_dmi_extractor.py - R1 BIOS Tool
Dedicated DMI and Vital Product Data (VPD) Extractor for Lenovo BIOS Firmware.

Supports:
  1. Lenovo ThinkPad Series (T480, T490, T14, X1 Carbon, E490, P-series, etc.)
  2. Lenovo IdeaPad / Legion / Yoga Series (LCFC, Compal, Quanta, Wistron boards)
  3. VPD / UVPD / LENV raw block extraction (RawBlocks["LENOVO_VPD"])
  4. System Model detection (literal strings or verified BIOS family identifiers)
  5. Machine Type Model (MTM) / Product Number (10-character e.g. 20L6..., 81DE...)
  6. Authentic Serial Number extraction (1S barcode, proximity DMI table, or verified prefix)
  7. Motherboard / System UUID (RFC 4122 binary table & ASCII formats)
  8. Board Product / Part Number (SDK... WIN)
  9. Windows OEM Digital License Key (MSDM table & NVRAM store)
  10. Motherboard Tracking ID (Isolated from Serial Number to prevent user confusion)
"""

import os
import re
import uuid
from typing import Union


class LenovoDMIExtractor:
    # ThinkPad BIOS Family Mapping for firmware where the model name is resolved via BIOS ID
    THINKPAD_BIOS_MAP = {
        "N24ET": "ThinkPad T480",
        "N24HT": "ThinkPad T480",
        "N27ET": "ThinkPad T490",
        "N2IET": "ThinkPad T490 / T590",
        "N2EET": "ThinkPad P1 / X1 Extreme",
        "N2BET": "ThinkPad P52",
        "N1MET": "ThinkPad X131e",
        "N1UET": "ThinkPad T470s",
        "N1QET": "ThinkPad T470",
        "N1OET": "ThinkPad T570",
        "R0YET": "ThinkPad E490 / E590",
        "R0UET": "ThinkPad E480 / E580",
        "R15ET": "ThinkPad E14 / E15 Gen 2",
        "R1EET": "ThinkPad E14 / E15 Gen 3",
        "R1FET": "ThinkPad E14 / E15 Gen 4",
        "N34ET": "ThinkPad T14 Gen 2",
        "N3MET": "ThinkPad T14 Gen 3",
        "N3CET": "ThinkPad T14 Gen 4",
    }

    # Standard Lenovo 2-character Serial Number prefixes (ThinkPad, IdeaPad, Legion, Yoga)
    LENOVO_SERIAL_PREFIXES = [
        b'PF', b'MP', b'YD', b'PC', b'PW', b'R9', b'L3', b'8S',
        b'MJ', b'LR', b'VK', b'W4', b'HA', b'PH', b'PK', b'PL',
        b'YM', b'ZN', b'1S', b'SN'
    ]

    @staticmethod
    def extract(bios_input: Union[str, bytes, bytearray], log_cb=None) -> dict:
        results = {
            "Brand": "Lenovo",
            "Details": {},
            "Offsets": {},
            "EndOffsets": {},
            "Lengths": {},
            "Encodings": {},
            "Regions": {},
            "RelativeOffsets": {},
            "RawBlocks": {}
        }

        def _log(m):
            if log_cb:
                log_cb(m)

        if isinstance(bios_input, (bytes, bytearray)):
            data = bytes(bios_input)
        elif isinstance(bios_input, str):
            if not os.path.exists(bios_input):
                return results
            try:
                with open(bios_input, 'rb') as f:
                    data = f.read()
            except Exception as e:
                _log(f"[Lenovo] Failed to read BIOS file: {e}")
                return results
        else:
            return results

        file_len = len(data)
        if file_len < 0x1000:
            return results

        # ── 1. DETECT VPD / LENV RAW BLOCK ─────────────────────────────────
        vpd_off = -1
        for p in [data.find(b'\xaa\x55VPD\x00'), data.find(b'LENV\x00'), data.find(b'LENC\x00')]:
            if p != -1:
                vpd_off = p
                break

        if vpd_off != -1:
            vpd_size = 0x1000  # 4KB standard for VPD
            if vpd_off + vpd_size <= file_len:
                vpd_bytes = data[vpd_off : vpd_off + vpd_size]
                results["RawBlocks"]["LENOVO_VPD"] = {
                    "start_offset": f"0x{vpd_off:X}",
                    "length": vpd_size,
                    "hex": vpd_bytes.hex(),
                    "region": "BIOS",
                    "relative_offset": f"0x{vpd_off:X}"
                }
                _log(f"[Lenovo] Found VPD Vital Product Data Block @ 0x{vpd_off:X} (Size: {vpd_size}B)")

        # ── 2. SYSTEM MODEL DETECTION (Scored Multi-Candidate) ─────────────
        def _score_lenovo_model(s: str) -> float:
            sc = 100.0
            sl = s.lower()
            if any(term in sl for term in ["product", "setup", "lenovo", "default"]):
                sc -= 50.0
            # Strong bonus for specific generation/model number (e.g. T480, X1 Carbon, 15ADA05, G2, Gen 8)
            if re.search(r'\b(?:T|X|P|E|L)[0-9]{3}\b', s, re.IGNORECASE):
                sc += 300.0
            elif re.search(r'\b[0-9]{1,2}[A-Z]{3,6}[0-9]{1,3}\b', s, re.IGNORECASE):
                sc += 250.0
            elif re.search(r'\bGen\s+[0-9]\b', s, re.IGNORECASE):
                sc += 200.0
            elif re.search(r'\b[0-9]{1,2}\s+[A-Z0-9]+\b', s):
                sc += 150.0
            elif re.search(r'\b[0-9]{3,4}\b', s):
                sc += 100.0
            return sc

        model_candidates = []
        for m in re.finditer(
            rb'(ThinkPad\s+[A-Za-z0-9\s\-]+|IdeaPad\s+[A-Za-z0-9\s\-]+|Legion\s+[A-Za-z0-9\s\-]+|Yoga\s+[A-Za-z0-9\s\-]+|ThinkBook\s+[A-Za-z0-9\s\-]+)',
            data, re.IGNORECASE
        ):
            raw = m.group(0).split(b'\x00')[0].strip()
            s = raw.decode('ascii', errors='ignore').strip()
            if len(s) >= 8 and not s.lower().startswith("thinkpad product ca"):
                s = re.sub(r'[\r\n\t]+.*', '', s).strip()
                model_candidates.append((s, m.start(), _score_lenovo_model(s)))

        model_off = None
        if model_candidates:
            model_candidates.sort(key=lambda x: x[2], reverse=True)
            m_val, m_off, _ = model_candidates[0]
            results["Details"]["System Model"] = m_val
            results["Offsets"]["System Model"] = f"0x{m_off:X}"
            results["EndOffsets"]["System Model"] = f"0x{m_off + len(m_val):X}"
            results["Lengths"]["System Model"] = len(m_val)
            results["Encodings"]["System Model"] = "ASCII"
            model_off = m_off
            _log(f"[Lenovo] System Model: {m_val} @ 0x{m_off:X}")
        else:
            # Fallback: check ThinkPad BIOS release ID (e.g. N24ET, N27ET, R0YET)
            for prefix, model_name in LenovoDMIExtractor.THINKPAD_BIOS_MAP.items():
                if prefix.encode('ascii') in data:
                    results["Details"]["System Model"] = model_name
                    results["Offsets"]["System Model"] = "UNKNOWN"
                    results["Lengths"]["System Model"] = len(model_name)
                    results["Encodings"]["System Model"] = "ASCII"
                    _log(f"[Lenovo] System Model (derived from BIOS ID {prefix}): {model_name}")
                    break

        # ── 3. MACHINE TYPE MODEL (MTM) / PRODUCT NUMBER ───────────────────
        # MTM pattern: ThinkPad (20..., 21...), IdeaPad/Legion (80..., 81..., 82..., 83..., 90...)
        mtm_pattern = rb'\b(20[A-Z0-9]{8}|21[A-Z0-9]{8}|8[0-3][A-Z0-9]{8}|90[A-Z0-9]{8})\b'
        mtm_val = None
        mtm_off = None

        # Proximity search near System Model first (guarantees real MTM over build timestamps)
        if model_off is not None:
            win_start = max(0, model_off - 1024)
            win_end = min(file_len, model_off + 1024)
            for m in re.finditer(mtm_pattern, data[win_start:win_end]):
                cand_str = m.group(1).decode('ascii')
                # Filter out pure-digit dates (e.g. 2025051000)
                if cand_str.isdigit() and cand_str.startswith(('201', '202', '203')):
                    continue
                mtm_val = cand_str
                mtm_off = win_start + m.start()
                break

        # Global search fallback
        if not mtm_val:
            for m in re.finditer(mtm_pattern, data):
                cand_str = m.group(1).decode('ascii')
                if cand_str.isdigit() and cand_str.startswith(('201', '202', '203')):
                    continue
                mtm_val = cand_str
                mtm_off = m.start()
                break

        if mtm_val and mtm_off is not None:
            results["Details"]["MTM"] = mtm_val
            results["Details"]["Product Number"] = mtm_val
            results["Offsets"]["MTM"] = f"0x{mtm_off:X}"
            results["Offsets"]["Product Number"] = f"0x{mtm_off:X}"
            results["EndOffsets"]["MTM"] = f"0x{mtm_off + len(mtm_val):X}"
            results["EndOffsets"]["Product Number"] = f"0x{mtm_off + len(mtm_val):X}"
            results["Lengths"]["MTM"] = len(mtm_val)
            results["Lengths"]["Product Number"] = len(mtm_val)
            results["Encodings"]["MTM"] = "ASCII"
            results["Encodings"]["Product Number"] = "ASCII"
            _log(f"[Lenovo] MTM / Product Number: {mtm_val} @ 0x{mtm_off:X}")

        # ── 4. AUTHENTIC SERIAL NUMBER EXTRACTION ──────────────────────────
        sn_val = None
        sn_off = None

        # Strategy 0: ThinkPad DMI Table Slot (Exact slot at Model + 0x43 or MTM + 0x86)
        if model_off is not None:
            for delta in (0x43, 0x44, 0x42, 0x45):
                cand_pos = model_off + delta
                if 0 <= cand_pos <= file_len - 8:
                    cand_raw = data[cand_pos : cand_pos + 8]
                    if re.match(rb'^[A-Z0-9]{8}$', cand_raw):
                        cand_str = cand_raw.decode('ascii')
                        b_before = data[cand_pos - 1] if cand_pos > 0 else 0
                        b_after = data[cand_pos + 8] if cand_pos + 8 < file_len else 0
                        if b_before in (0, 0xFF) and b_after in (0, 0xFF):
                            sn_val = cand_str
                            sn_off = cand_pos
                            _log(f"[Lenovo] ThinkPad DMI Slot match (Model + 0x{delta:X}) @ 0x{sn_off:X} -> SN: {sn_val}")
                            break

        # Strategy A: Check 1S barcode format (1S + 10-char MTM + 8-char SN)
        if not sn_val:
            barcode_m = re.search(rb'1S([A-Z0-9]{10})([A-Z0-9]{8})\b', data)
            if barcode_m:
                full_bc = barcode_m.group(0).decode('ascii')
                mtm_part = barcode_m.group(1).decode('ascii')
                sn_part = barcode_m.group(2).decode('ascii')
                sn_val = sn_part
                sn_off = barcode_m.start() + 12
                results["Details"]["Barcode"] = full_bc
                results["Offsets"]["Barcode"] = f"0x{barcode_m.start():X}"
                results["EndOffsets"]["Barcode"] = f"0x{barcode_m.start() + len(full_bc):X}"
                results["Lengths"]["Barcode"] = len(full_bc)
                results["Encodings"]["Barcode"] = "ASCII"
                if "MTM" not in results["Details"]:
                    results["Details"]["MTM"] = mtm_part
                    results["Details"]["Product Number"] = mtm_part
                    results["Offsets"]["MTM"] = f"0x{barcode_m.start() + 2:X}"
                    results["Offsets"]["Product Number"] = f"0x{barcode_m.start() + 2:X}"
                    results["Lengths"]["MTM"] = len(mtm_part)
                    results["Lengths"]["Product Number"] = len(mtm_part)
                    results["Encodings"]["MTM"] = "ASCII"
                    results["Encodings"]["Product Number"] = "ASCII"
                _log(f"[Lenovo] Found 1S Barcode @ 0x{barcode_m.start():X} -> SN: {sn_val}")

        # Strategy B: Proximity DMI Block Search near MTM / System Model
        pref_pattern = rb'\b(?:GM|PF|MP|YD|PC|PW|R9|L3|8S|MJ|LR|VK|W4|HA|PH|PK|PL|YM|ZN|W8|1S|2S|AA|BA|CA)[A-Z0-9]{6}\b'
        anchor_off = mtm_off if mtm_off is not None else model_off

        if not sn_val and anchor_off is not None:
            win_start = max(0, anchor_off - 2048)
            win_end = min(file_len, anchor_off + 2048)
            prox_matches = list(re.finditer(pref_pattern, data[win_start:win_end]))
            if prox_matches:
                # Sort by distance to the DMI anchor (MTM or Model)
                prox_matches.sort(key=lambda m: abs((win_start + m.start()) - anchor_off))
                best = prox_matches[0]
                sn_val = best.group(0).decode('ascii')
                sn_off = win_start + best.start()
                _log(f"[Lenovo] Proximity DMI match near MTM/Model @ 0x{sn_off:X} -> SN: {sn_val}")
            else:
                # Fallback within anchor window: any 8-char alphanumeric surrounded by 0x00 or 0xFF
                for m in re.finditer(rb'[A-Z0-9]{8}', data[win_start:win_end]):
                    p = win_start + m.start()
                    if p == mtm_off:
                        continue
                    b_bef = data[p - 1] if p > 0 else 0
                    b_aft = data[p + 8] if p + 8 < file_len else 0
                    if b_bef in (0, 0xFF) and b_aft in (0, 0xFF):
                        cand_s = m.group(0).decode('ascii')
                        if not cand_s.isdigit() and not cand_s.startswith(('201', '202', '203')):
                            sn_val = cand_s
                            sn_off = p
                            _log(f"[Lenovo] Proximity slot match @ 0x{sn_off:X} -> SN: {sn_val}")
                            break

        # Strategy C: Global Serial Number Search with Flash Padding (0x00 and 0xFF) Validation
        if not sn_val:
            scored_candidates = []
            for sm in re.finditer(pref_pattern, data):
                p = sm.start()
                # Check byte boundary: byte before must be null, 0xFF, whitespace, newline, or punctuation
                b_before = data[p - 1] if p > 0 else 0
                b_after = data[p + 8] if p + 8 < file_len else 0
                if b_before in (0, 0xFF, 0x20, 0x0A, 0x0D, ord(':'), ord('='), ord(','), ord('"'), ord('>')) and \
                   b_after in (0, 0xFF, 0x20, 0x0A, 0x0D, ord(','), ord(';'), ord('"'), ord('<'), ord('\t')):
                    cand_str = sm.group(0).decode('ascii')
                    sc = 100.0
                    # Bonus if near any occurrence of 'LENOVO'
                    for lenovo_pos in [m.start() for m in re.finditer(rb'LENOVO', data)]:
                        dist = abs(p - lenovo_pos)
                        if dist < 4096:
                            sc += max(0, 400.0 - (dist / 10.0))
                            break
                    # Bonus if clean 0x00 or 0xFF padding
                    if b_before in (0, 0xFF) and b_after in (0, 0xFF):
                        sc += 150.0
                    scored_candidates.append((cand_str, p, sc))

            if scored_candidates:
                scored_candidates.sort(key=lambda x: x[2], reverse=True)
                sn_val, sn_off, _ = scored_candidates[0]
                _log(f"[Lenovo] Global scored match @ 0x{sn_off:X} -> SN: {sn_val}")

        # Check standalone BIOS / ROM ID (e.g. N46ET25W)
        rom_sn_m = re.search(rb'\b([A-Z0-9]{2,6}ET[0-9]{2}[A-Z])\s*\(', data)
        rom_sn_val = None
        rom_sn_off = None
        if rom_sn_m:
            rom_sn_val = rom_sn_m.group(1).decode('ascii')
            rom_sn_off = rom_sn_m.start(1)
            results["Details"]["BIOS ID"] = rom_sn_val
            results["Offsets"]["BIOS ID"] = f"0x{rom_sn_off:X}"
            results["EndOffsets"]["BIOS ID"] = f"0x{rom_sn_off + len(rom_sn_val):X}"
            results["Lengths"]["BIOS ID"] = len(rom_sn_val)
            results["Encodings"]["BIOS ID"] = "ASCII"
            _log(f"[Lenovo] BIOS / Firmware ID: {rom_sn_val} @ 0x{rom_sn_off:X}")

        # The authentic hardware Chassis Serial (e.g. GM0RXP9K, PF1503FD) ALWAYS takes precedence for the DMI Box
        if sn_val and sn_off is not None:
            results["Details"]["Serial Number"] = sn_val
            results["Offsets"]["Serial Number"] = f"0x{sn_off:X}"
            results["EndOffsets"]["Serial Number"] = f"0x{sn_off + len(sn_val):X}"
            results["Lengths"]["Serial Number"] = len(sn_val)
            results["Encodings"]["Serial Number"] = "ASCII"

            results["Details"]["Chassis Serial"] = sn_val
            results["Offsets"]["Chassis Serial"] = f"0x{sn_off:X}"
            results["EndOffsets"]["Chassis Serial"] = f"0x{sn_off + len(sn_val):X}"
            results["Lengths"]["Chassis Serial"] = len(sn_val)
            results["Encodings"]["Chassis Serial"] = "ASCII"
            _log(f"[Lenovo] Authentic Chassis Serial Number (DMI Box): {sn_val} @ 0x{sn_off:X}")
        elif rom_sn_val and rom_sn_off is not None:
            # Fallback only if no chassis serial exists anywhere in DMI
            sn_val = rom_sn_val
            sn_off = rom_sn_off
            results["Details"]["Serial Number"] = sn_val
            results["Offsets"]["Serial Number"] = f"0x{sn_off:X}"
            results["EndOffsets"]["Serial Number"] = f"0x{sn_off + len(sn_val):X}"
            results["Lengths"]["Serial Number"] = len(sn_val)
            results["Encodings"]["Serial Number"] = "ASCII"
            _log(f"[Lenovo] Serial Number fallback from ROM ID: {sn_val} @ 0x{sn_off:X}")

        # ── 5. BOARD TRACKING ID / PART BARCODE (Isolated from Serial Number) ──
        # 13-digit tracking code (e.g. 3305146554645, 3556191310685) from manufacturing / MSDM block
        trk_m = re.search(rb'\b(3[0-9]{12})\b', data)
        if trk_m:
            trk_val = trk_m.group(1).decode('ascii')
            results["Details"]["Board Tracking ID"] = trk_val
            results["Offsets"]["Board Tracking ID"] = f"0x{trk_m.start():X}"
            results["EndOffsets"]["Board Tracking ID"] = f"0x{trk_m.start() + len(trk_val):X}"
            results["Lengths"]["Board Tracking ID"] = len(trk_val)
            results["Encodings"]["Board Tracking ID"] = "ASCII"
            _log(f"[Lenovo] Board Tracking ID: {trk_val} @ 0x{trk_m.start():X}")

        # ── 5b. UEFI BIOS VERSION & RELEASE DATE EXTRACTION ─────────────────
        bios_v_m = re.search(rb'(?:RESERVE)?([A-Z0-9]{2,6}ET[0-9]{2}[A-Z])(?:\s*\(([^)]+)\))?', data)
        if bios_v_m:
            bios_id = bios_v_m.group(1).decode('ascii')
            full_str = bios_v_m.group(0).decode('ascii', errors='ignore').replace('RESERVE', '').strip()
            bios_off = bios_v_m.start(1)
            results["Details"]["BIOS Version"] = full_str
            results["Offsets"]["BIOS Version"] = f"0x{bios_off:X}"
            results["EndOffsets"]["BIOS Version"] = f"0x{bios_off + len(full_str):X}"
            results["Lengths"]["BIOS Version"] = len(full_str)
            results["Encodings"]["BIOS Version"] = "ASCII"

            results["Details"]["BIOS ID"] = bios_id
            results["Offsets"]["BIOS ID"] = f"0x{bios_off:X}"
            results["EndOffsets"]["BIOS ID"] = f"0x{bios_off + len(bios_id):X}"
            results["Lengths"]["BIOS ID"] = len(bios_id)
            results["Encodings"]["BIOS ID"] = "ASCII"
            _log(f"[Lenovo] UEFI BIOS Version: {full_str} (ID: {bios_id}) @ 0x{bios_off:X}")

            # Check if release date is nearby (+/- 128 bytes)
            win_date = data[max(0, bios_off - 64) : min(file_len, bios_off + 128)]
            date_m = re.search(rb'(\d{2}/\d{2}/\d{4})', win_date)
            if date_m:
                date_val = date_m.group(1).decode('ascii')
                date_off = max(0, bios_off - 64) + date_m.start()
                results["Details"]["BIOS Date"] = date_val
                results["Offsets"]["BIOS Date"] = f"0x{date_off:X}"
                results["EndOffsets"]["BIOS Date"] = f"0x{date_off + len(date_val):X}"
                results["Lengths"]["BIOS Date"] = len(date_val)
                results["Encodings"]["BIOS Date"] = "ASCII"
                _log(f"[Lenovo] BIOS Release Date: {date_val} @ 0x{date_off:X}")

        # ── 6. SYSTEM UUID EXTRACTION (RFC 4122 Binary & ASCII) ────────────
        uuid_val = None
        uuid_off = None
        uuid_enc = "ASCII"

        # Check ASCII standard 36-char UUID format first
        u_ascii = re.search(rb'\b([0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})\b', data)
        if u_ascii:
            uuid_val = u_ascii.group(1).decode('ascii').upper()
            uuid_off = u_ascii.start()
            uuid_enc = "ASCII"

        # Proximity binary UUID search in DMI block near Serial Number or MTM
        if not uuid_val and (sn_off is not None or anchor_off is not None):
            ref_off = sn_off if sn_off is not None else anchor_off
            # In ThinkPads, UUID is typically within 128 bytes after the serial number entry
            win_start = max(0, ref_off - 128)
            win_end = min(file_len, ref_off + 256)
            win_data = data[win_start:win_end]
            for i in range(len(win_data) - 16):
                raw16 = win_data[i : i + 16]
                # Reject padding bytes and false sliding alignment
                if b'\xff\xff' in raw16[:2] or b'\xff\xff' in raw16[-2:]:
                    continue
                if raw16[:4] == b'\x00\x00\x00\x00' or raw16[-4:] == b'\x00\x00\x00\x00':
                    continue
                if raw16 != b'\x00' * 16 and raw16 != b'\xff' * 16:
                    try:
                        cand_u = uuid.UUID(bytes_le=raw16)
                        # Hardware UUIDs in SMBIOS/UEFI are RFC 4122 Version 1 (time-based) or Version 4 (random)
                        if cand_u.variant == uuid.RFC_4122 and cand_u.version in (1, 4):
                            uuid_val = str(cand_u).upper()
                            uuid_off = win_start + i
                            uuid_enc = "BINARY"
                            break
                    except Exception:
                        pass

        if uuid_val and uuid_off is not None:
            results["Details"]["UUID"] = uuid_val
            results["Offsets"]["UUID"] = f"0x{uuid_off:X}"
            results["EndOffsets"]["UUID"] = f"0x{uuid_off + (16 if uuid_enc == 'BINARY' else len(uuid_val)):X}"
            results["Lengths"]["UUID"] = 16 if uuid_enc == "BINARY" else len(uuid_val)
            results["Encodings"]["UUID"] = uuid_enc
            _log(f"[Lenovo] System UUID: {uuid_val} @ 0x{uuid_off:X} ({uuid_enc})")

        # ── 7. BOARD PRODUCT / PART NUMBER ─────────────────────────────────
        sdk_m = re.search(rb'(SDK[A-Z0-9]{6,12}\s+WIN)', data)
        if sdk_m:
            sdk_val = sdk_m.group(1).decode('ascii').strip()
            results["Details"]["Board Product"] = sdk_val
            results["Offsets"]["Board Product"] = f"0x{sdk_m.start():X}"
            results["EndOffsets"]["Board Product"] = f"0x{sdk_m.start() + len(sdk_val):X}"
            results["Lengths"]["Board Product"] = len(sdk_val)
            results["Encodings"]["Board Product"] = "ASCII"
            _log(f"[Lenovo] Board Product: {sdk_val} @ 0x{sdk_m.start():X}")

        # ── 8. WINDOWS OEM DIGITAL LICENSE KEY (MSDM) ──────────────────────
        key_m = re.search(rb'([A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5})', data)
        if key_m:
            key_val = key_m.group(1).decode('ascii')
            results["Details"]["Windows OEM Key"] = key_val
            results["Offsets"]["Windows OEM Key"] = f"0x{key_m.start():X}"
            results["EndOffsets"]["Windows OEM Key"] = f"0x{key_m.start() + len(key_val):X}"
            results["Lengths"]["Windows OEM Key"] = len(key_val)
            results["Encodings"]["Windows OEM Key"] = "ASCII"
            _log(f"[Lenovo] Windows OEM Key: {key_val} @ 0x{key_m.start():X}")

        # ── 9. MULTI-OCCURRENCE SCANNER ────────────────────────────────────
        results["AllOccurrences"] = {}

        def _record_all_instances(field_name, search_val, primary_off_str, role_desc):
            if not search_val or not isinstance(search_val, str) or len(search_val.strip()) < 4:
                return
            val_clean = search_val.strip()
            if field_name not in results["AllOccurrences"]:
                results["AllOccurrences"][field_name] = []

            seen_offsets = set()
            p_off = None
            if primary_off_str and str(primary_off_str).strip() not in ("N/A", "UNKNOWN", "None", ""):
                try:
                    p_off = int(str(primary_off_str), 16) if str(primary_off_str).lower().startswith("0x") else int(primary_off_str)
                except Exception:
                    pass

            for enc in ['utf-16-le', 'ascii']:
                try:
                    b_target = val_clean.encode(enc)
                    enc_label = "UTF-16LE" if enc == 'utf-16-le' else "ASCII"
                    pos = 0
                    while True:
                        idx = data.find(b_target, pos)
                        if idx == -1:
                            break
                        if idx not in seen_offsets:
                            seen_offsets.add(idx)
                            is_primary = (p_off is not None and idx == p_off)
                            role = f"Primary {role_desc}" if is_primary else f"Secondary {role_desc} (Mirror)"
                            results["AllOccurrences"][field_name].append({
                                "value": val_clean,
                                "offset": f"0x{idx:X}",
                                "end_offset": f"0x{idx + len(b_target):X}",
                                "length": len(b_target),
                                "encoding": enc_label,
                                "role": role,
                                "is_primary": is_primary
                            })
                        pos = idx + 1
                except Exception:
                    pass

        for fld, role_name in [
            ("System Model", "Model"),
            ("Serial Number", "Serial"),
            ("MTM", "MTM"),
            ("BIOS Version", "BIOS Version"),
            ("BIOS ID", "BIOS ID"),
            ("Board Tracking ID", "Board Tracking ID"),
            ("UUID", "UUID"),
            ("Windows OEM Key", "Windows Key")
        ]:
            if fld in results["Details"]:
                _record_all_instances(fld, results["Details"][fld], results["Offsets"].get(fld, ""), role_name)

        # Cross-reference BIOS ID in Serial Number occurrences as secondary firmware ID
        if "BIOS ID" in results["Details"]:
            b_id = results["Details"]["BIOS ID"]
            b_off = results["Offsets"].get("BIOS ID", "")
            if "Serial Number" not in results["AllOccurrences"]:
                results["AllOccurrences"]["Serial Number"] = []
            if b_off and b_off.startswith("0x"):
                b_off_int = int(b_off, 16)
                # Avoid duplicates if it's already primary
                if not any(occ.get("value") == b_id and occ.get("is_primary") for occ in results["AllOccurrences"]["Serial Number"]):
                    results["AllOccurrences"]["Serial Number"].append({
                        "value": b_id,
                        "offset": b_off,
                        "end_offset": f"0x{b_off_int + len(b_id):X}",
                        "length": len(b_id),
                        "encoding": "ASCII",
                        "role": "BIOS Version / Firmware ID (ROM)",
                        "is_primary": False
                    })

        return results
