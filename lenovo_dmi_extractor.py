"""
lenovo_dmi_extractor.py - R1 BIOS Tool
Dedicated DMI and Vital Product Data (VPD) Extractor for Lenovo BIOS Firmware.

Supports:
  1. Lenovo ThinkPad Series (T480, T490, T14, X1 Carbon, E490, P-series, etc.)
  2. Lenovo IdeaPad / Legion / Yoga Series (LCFC, Compal, Quanta, Wistron boards)
  3. VPD / UVPD / LENV raw block extraction (RawBlocks["LENOVO_VPD"])
  4. System Model detection (literal strings or verified BIOS family identifiers)
  5. Machine Type Model (MTM) / Product Number (10-character e.g. 20N8..., 81DE...)
  6. Serial Number (1S barcode format, 8-character prefix format, or tracking ID)
  7. Board Product / Part Number (SDK... WIN)
  8. Windows OEM Digital License Key (MSDM table & NVRAM store)
  9. Motherboard / System UUID
"""

import os
import re


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

    LENOVO_SERIAL_PREFIXES = [
        b'PF', b'MP', b'YD', b'PC', b'PW', b'R9', b'L3', b'8S',
        b'MJ', b'LR', b'VK', b'W4', b'HA', b'PH', b'PK', b'PL'
    ]

    @staticmethod
    def extract(bios_path: str, log_cb=None) -> dict:
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
        if not os.path.exists(bios_path):
            return results

        def _log(m):
            if log_cb:
                log_cb(m)

        try:
            with open(bios_path, 'rb') as f:
                data = f.read()
        except Exception as e:
            _log(f"[Lenovo] Failed to read BIOS file: {e}")
            return results

        file_len = len(data)

        # ── 1. DETECT VPD / LENV RAW BLOCK ─────────────────────────────────
        vpd_off = -1
        # Check \xaa\x55VPD\x00 or VPD\x00 or LENV\x00
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
            # Bonus for generation/model number (e.g. T480, X1 Carbon, 15ADA05, G2, Gen 8)
            if re.search(r'\b(?:T|X|P|E|L)[0-9]{3}\b', s, re.IGNORECASE):
                sc += 250.0
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

        if model_candidates:
            model_candidates.sort(key=lambda x: x[2], reverse=True)
            m_val, m_off, _ = model_candidates[0]
            results["Details"]["System Model"] = m_val
            results["Offsets"]["System Model"] = f"0x{m_off:X}"
            results["Lengths"]["System Model"] = len(m_val)
            results["Encodings"]["System Model"] = "ASCII"
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
        mtm_m = re.search(rb'\b(20[A-Z0-9]{8}|21[A-Z0-9]{8}|8[0-3][A-Z0-9]{8})\b', data)
        if mtm_m:
            mtm_val = mtm_m.group(1).decode('ascii')
            results["Details"]["MTM"] = mtm_val
            results["Details"]["Product Number"] = mtm_val
            results["Offsets"]["MTM"] = f"0x{mtm_m.start():X}"
            results["Offsets"]["Product Number"] = f"0x{mtm_m.start():X}"
            results["Lengths"]["MTM"] = len(mtm_val)
            results["Lengths"]["Product Number"] = len(mtm_val)
            results["Encodings"]["MTM"] = "ASCII"
            results["Encodings"]["Product Number"] = "ASCII"
            _log(f"[Lenovo] MTM / Product Number: {mtm_val} @ 0x{mtm_m.start():X}")

        # ── 4. SERIAL NUMBER EXTRACTION ────────────────────────────────────
        sn_found = None

        # Check 1S barcode format: 1S + MTM (10 chars) + 8-char SN
        barcode_m = re.search(rb'1S([A-Z0-9]{10})([A-Z0-9]{8})\b', data)
        if barcode_m:
            full_bc = barcode_m.group(0).decode('ascii')
            mtm_part = barcode_m.group(1).decode('ascii')
            sn_part = barcode_m.group(2).decode('ascii')
            sn_found = (sn_part, barcode_m.start() + 12)
            results["Details"]["Barcode"] = full_bc
            results["Offsets"]["Barcode"] = f"0x{barcode_m.start():X}"
            if "MTM" not in results["Details"]:
                results["Details"]["MTM"] = mtm_part
                results["Offsets"]["MTM"] = f"0x{barcode_m.start() + 2:X}"
                results["Lengths"]["MTM"] = len(mtm_part)
                results["Encodings"]["MTM"] = "ASCII"

        # Check standard 8-character serial number with known prefixes
        if not sn_found:
            for pref in LenovoDMIExtractor.LENOVO_SERIAL_PREFIXES:
                for sm in re.finditer(re.escape(pref) + rb'[A-Z0-9]{6}\b', data):
                    p = sm.start()
                    ctx = data[max(0, p - 16): p + 24]
                    ascii_count = sum(32 <= b <= 126 or b == 0 for b in ctx)
                    if ascii_count >= len(ctx) - 2:
                        s = sm.group(0).decode('ascii')
                        sn_found = (s, p)
                        break
                if sn_found:
                    break

        # Check Board Tracking ID / Serial fallback (e.g. 3305114311668)
        if not sn_found:
            trk_m = re.search(rb'\b330[0-9]{10}\b', data)
            if trk_m:
                s = trk_m.group(0).decode('ascii')
                sn_found = (s, trk_m.start())

        if sn_found:
            s_val, s_off = sn_found
            results["Details"]["Serial Number"] = s_val
            results["Offsets"]["Serial Number"] = f"0x{s_off:X}"
            results["Lengths"]["Serial Number"] = len(s_val)
            results["Encodings"]["Serial Number"] = "ASCII"
            _log(f"[Lenovo] Serial Number: {s_val} @ 0x{s_off:X}")

        # ── 5. BOARD PRODUCT / PART NUMBER ─────────────────────────────────
        sdk_m = re.search(rb'(SDK[A-Z0-9]{6,12}\s+WIN)', data)
        if sdk_m:
            sdk_val = sdk_m.group(1).decode('ascii').strip()
            results["Details"]["Board Product"] = sdk_val
            results["Offsets"]["Board Product"] = f"0x{sdk_m.start():X}"
            results["Lengths"]["Board Product"] = len(sdk_val)
            results["Encodings"]["Board Product"] = "ASCII"
            _log(f"[Lenovo] Board Product: {sdk_val} @ 0x{sdk_m.start():X}")

        # ── 6. WINDOWS OEM DIGITAL LICENSE KEY (MSDM) ──────────────────────
        key_m = re.search(rb'([A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5})', data)
        if key_m:
            key_val = key_m.group(1).decode('ascii')
            results["Details"]["Windows OEM Key"] = key_val
            results["Offsets"]["Windows OEM Key"] = f"0x{key_m.start():X}"
            results["Lengths"]["Windows OEM Key"] = len(key_val)
            results["Encodings"]["Windows OEM Key"] = "ASCII"
            _log(f"[Lenovo] Windows OEM Key: {key_val} @ 0x{key_m.start():X}")

        # ── 8. MULTI-OCCURRENCE SCANNER ──────────────────────────────────────
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
                except:
                    pass

            for enc in ['utf-16-le', 'ascii']:
                try:
                    b_target = val_clean.encode(enc)
                    enc_label = "UTF-16LE" if enc == 'utf-16-le' else "ASCII"
                    pos = 0
                    while True:
                        idx = data.find(b_target, pos)
                        if idx == -1: break
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
                except:
                    pass

        if "System Model" in results["Details"]:
            _record_all_instances("System Model", results["Details"]["System Model"], results["Offsets"].get("System Model", ""), "Model")
        if "Serial Number" in results["Details"]:
            _record_all_instances("Serial Number", results["Details"]["Serial Number"], results["Offsets"].get("Serial Number", ""), "Serial")
        if "MTM" in results["Details"]:
            _record_all_instances("MTM", results["Details"]["MTM"], results["Offsets"].get("MTM", ""), "MTM")

        return results
