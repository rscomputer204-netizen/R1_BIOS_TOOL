"""
dell_dmi_extractor.py - R1 BIOS Tool
Dedicated DMI and System Information Extractor for Dell BIOS Firmware.

Handles:
  1. Dell DVAR (Dell Variable Store) block detection & extraction (RawBlocks["DELL_DVAR"])
  2. System Model detection (Latitude, Precision, OptiPlex, XPS, Vostro, Alienware, Inspiron, etc.)
  3. Motherboard PPID / Board Serial Number (CN0...)
  4. Onboard Ethernet MAC Address
  5. Windows OEM Digital License Key (MSDM table / DVAR)
  6. Service Tag extraction with strict validation (eliminating false positive '0123456' digit ramps)
"""

import os
import re


class DellDMIExtractor:
    BLACKLISTED_TAGS = {
        # Sequential digit ramps & common placeholder strings
        "0123456", "1234567", "2345678", "3456789", "4567890", "5678901",
        "0000000", "1111111", "2222222", "3333333", "4444444", "5555555",
        "6666666", "7777777", "8888888", "9999999", "ABCDEFG", "BCDEFGH",
        "PQRSTUV", "QQRSTUV", "XYZ1234", "ASDFGHJ", "AABBCDD", "BBBBBBB",
        "FFFFFFF", "NNNNNNN", "UNKNOWN", "DEFAULT", "SERVTG0", "NOTAG00",
        # Factory / diagnostic flags found inside Dell DVAR structures
        "AFTPASS", "PCBAPASS", "RUNNING", "NVDIAG", "WTDM", "DisableGPU",
        "TearDown", "NV_PASS", "SHELL", "DELLBIO", "DOSPASS", "FLASHOK", "TESTPAS"
    }

    @staticmethod
    def is_valid_service_tag(tag: str) -> bool:
        if not tag or len(tag) != 7:
            return False
        tag_upper = tag.strip().upper()
        if tag_upper in DellDMIExtractor.BLACKLISTED_TAGS:
            return False
        if not re.match(r'^[A-Z0-9]{7}$', tag_upper):
            return False
        # Reject sequential character ramps (e.g. 0123456, 1234567, ABCDEFG)
        is_seq = True
        for i in range(len(tag_upper) - 1):
            if ord(tag_upper[i + 1]) != ord(tag_upper[i]) + 1:
                is_seq = False
                break
        if is_seq:
            return False
        # Reject purely repetitive characters (e.g. AAAAAAA, 1111111)
        if len(set(tag_upper)) <= 2:
            return False
        # Reject common NVRAM / firmware keywords
        if any(kw in tag_upper for kw in ["NVAR", "PASS", "BIOS", "WINDOWS", "DIAG", "SETUP"]):
            return False
        return True

    @staticmethod
    def extract(bios_path: str, log_cb=None) -> dict:
        results = {
            "Brand": "Dell",
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
            _log(f"[Dell] Failed to read BIOS file: {e}")
            return results

        file_len = len(data)

        # ── 1. DETECT DVAR VARIABLE STORE BLOCK ──────────────────────────────
        # Dell stores machine configuration, PPID, MAC, and DMI parameters
        # in the DVAR block (often aligned to 64KB, length 0x10000 or 0x20000).
        dvar_pos = 0
        dvar_found = -1
        while True:
            p = data.find(b'DVAR', dvar_pos)
            if p == -1:
                break
            # DVAR header signature starts with 'DVAR\xff\x0f' or is aligned at 4KB/64KB
            if p % 0x1000 == 0 or data[p:p + 8].startswith(b'DVAR\xff\x0f'):
                dvar_found = p
                break
            dvar_pos = p + 1

        dvar_bytes = b""
        if dvar_found != -1:
            dvar_size = 0x20000
            if dvar_found + dvar_size > file_len:
                dvar_size = file_len - dvar_found
            dvar_bytes = data[dvar_found : dvar_found + dvar_size]
            results["RawBlocks"]["DELL_DVAR"] = {
                "start_offset": f"0x{dvar_found:X}",
                "length": dvar_size,
                "hex": dvar_bytes.hex(),
                "region": "BIOS",
                "relative_offset": f"0x{dvar_found:X}"
            }
            _log(f"[Dell] Found DVAR Variable Store @ 0x{dvar_found:X} (Size: 0x{dvar_size:X})")

            # ── 2. EXTRACT PPID (MOTHERBOARD SERIAL) FROM DVAR ───────────────
            # Dell PPID format: CN0KJMV3WSC001AC2F1EA00 (23-25 alphanumeric chars)
            ppid_m = re.search(rb'CN0[A-Z0-9]{20,23}', dvar_bytes)
            if ppid_m:
                ppid_val = ppid_m.group(0).decode('ascii')
                ppid_off = dvar_found + ppid_m.start()
                results["Details"]["PPID"] = ppid_val
                results["Details"]["Board Serial"] = ppid_val
                results["Offsets"]["PPID"] = f"0x{ppid_off:X}"
                results["Offsets"]["Board Serial"] = f"0x{ppid_off:X}"
                results["Lengths"]["PPID"] = len(ppid_val)
                results["Lengths"]["Board Serial"] = len(ppid_val)
                results["Encodings"]["PPID"] = "ASCII"
                results["Encodings"]["Board Serial"] = "ASCII"
                _log(f"[Dell] Motherboard PPID: {ppid_val} @ 0x{ppid_off:X}")

            # ── 3. EXTRACT ONBOARD ETHERNET MAC ADDRESS FROM DVAR ────────────
            # Stored as 12 uppercase hexadecimal characters (e.g. B445060AD066)
            mac_candidates = re.finditer(rb'(?<![A-F0-9])[0-9A-F]{12}(?![A-F0-9])', dvar_bytes)
            for mc in mac_candidates:
                cand = mc.group(0).decode('ascii')
                if cand not in ['000000000000', 'FFFFFFFFFFFF'] and not re.match(r'^[0-9]+$', cand):
                    mac_formatted = ':'.join([cand[i:i + 2] for i in range(0, 12, 2)])
                    mac_off = dvar_found + mc.start()
                    results["Details"]["MAC Address"] = mac_formatted
                    results["Offsets"]["MAC Address"] = f"0x{mac_off:X}"
                    results["Lengths"]["MAC Address"] = 12
                    results["Encodings"]["MAC Address"] = "ASCII"
                    _log(f"[Dell] MAC Address: {mac_formatted} @ 0x{mac_off:X}")
                    break

            # ── 4. EXTRACT SYSTEM MODEL CANDIDATES FROM DVAR ─────────────────
            model_matches = re.finditer(
                rb'(Latitude|Precision|OptiPlex|XPS|Vostro|Alienware|Inspiron|G3|G5|G7|G15|G16)\s+[A-Z0-9\-]+',
                dvar_bytes, re.IGNORECASE
            )
            for mm in model_matches:
                mv = mm.group(0).decode('ascii').strip()
                mo = dvar_found + mm.start()
                if "System Model" not in results["Details"] or len(mv) > len(results["Details"]["System Model"]):
                    results["Details"]["System Model"] = mv
                    results["Offsets"]["System Model"] = f"0x{mo:X}"
                    results["Lengths"]["System Model"] = len(mv)
                    results["Encodings"]["System Model"] = "ASCII"
                    _log(f"[Dell] System Model (DVAR): {mv} @ 0x{mo:X}")

        # ── 5. GLOBAL FALLBACKS & SCORING FOR SYSTEM MODEL ───────────────────
        # Check all model occurrences across binary
        model_candidates = []
        for mm in re.finditer(
            rb'(Latitude|Precision|OptiPlex|XPS|Vostro|Alienware|Inspiron)\s+([0-9]{3,4}|[A-Z0-9\-]+)',
            data, re.IGNORECASE
        ):
            mv = f"{mm.group(1).decode('ascii')} {mm.group(2).decode('ascii')}".strip()
            mo = mm.start()
            sc = 100
            if re.search(r'\b[0-9]{3,4}\b', mv): sc += 200
            model_candidates.append((mv, mo, sc, "ASCII"))

        # UTF-16LE Dell model search
        names = ['Latitude', 'Inspiron', 'OptiPlex', 'Precision', 'Vostro', 'XPS', 'Alienware']
        u16_pat = rb'(?:' + rb'|'.join([n.encode('utf-16le') for n in names]) + rb')\x20\x00(?:[A-Za-z0-9]\x00){2,10}'
        for u16_mm in re.finditer(u16_pat, data, re.IGNORECASE):
            mv = u16_mm.group(0).decode('utf-16le', errors='ignore').strip()
            mo = u16_mm.start()
            sc = 100
            if re.search(r'\b[0-9]{3,4}\b', mv): sc += 200
            model_candidates.append((mv, mo, sc, "UTF-16LE"))

        if model_candidates:
            model_candidates.sort(key=lambda x: x[2], reverse=True)
            best_m = model_candidates[0]
            curr_model = results["Details"].get("System Model", "")
            # Upgrade if current model lacks numbers or is shorter
            if not curr_model or (not any(c.isdigit() for c in curr_model) and any(c.isdigit() for c in best_m[0])):
                results["Details"]["System Model"] = best_m[0]
                results["Offsets"]["System Model"] = f"0x{best_m[1]:X}"
                results["Lengths"]["System Model"] = len(best_m[0])
                results["Encodings"]["System Model"] = best_m[3]
                _log(f"[Dell] System Model (Best Ranked): {best_m[0]} @ 0x{best_m[1]:X} ({best_m[3]})")

        if "PPID" not in results["Details"]:
            ppid_m = re.search(rb'CN0[A-Z0-9]{20,23}', data)
            if ppid_m:
                ppid_val = ppid_m.group(0).decode('ascii')
                results["Details"]["PPID"] = ppid_val
                results["Details"]["Board Serial"] = ppid_val
                results["Offsets"]["PPID"] = f"0x{ppid_m.start():X}"
                results["Offsets"]["Board Serial"] = f"0x{ppid_m.start():X}"
                results["Lengths"]["PPID"] = len(ppid_val)
                results["Lengths"]["Board Serial"] = len(ppid_val)
                results["Encodings"]["PPID"] = "ASCII"
                results["Encodings"]["Board Serial"] = "ASCII"
                _log(f"[Dell] PPID (scan): {ppid_val} @ 0x{ppid_m.start():X}")

        # ── 6. EXTRACT WINDOWS OEM DIGITAL LICENSE KEY (MSDM) ────────────────
        key_m = re.search(rb'([A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5})', data)
        if key_m:
            key_val = key_m.group(1).decode('ascii')
            results["Details"]["Windows OEM Key"] = key_val
            results["Offsets"]["Windows OEM Key"] = f"0x{key_m.start():X}"
            results["Lengths"]["Windows OEM Key"] = len(key_val)
            results["Encodings"]["Windows OEM Key"] = "ASCII"
            _log(f"[Dell] Windows OEM License Key: {key_val} @ 0x{key_m.start():X}")

        # ── 7. EXTRACT SERVICE TAG & ASSET TAG (MULTI-TIERED FORENSIC SCAN) ───
        st_candidates = []
        found_asset_tag = None
        found_asset_off = None

        # Tier 1: Dell DMI Slash Pattern /<TAG>/ or /<TAG>/<ASSET>/ (Primary modern/classic Dell DMI standard)
        # Examples: /JV197M3/              /  or  /JV197M3/CNCMK0022N34B4/
        for m in re.finditer(rb'/([A-Z0-9]{7})/(?:([A-Za-z0-9\s]{0,24})/)?', data):
            tag_str = m.group(1).decode('ascii')
            if DellDMIExtractor.is_valid_service_tag(tag_str):
                st_candidates.append((tag_str, m.start(1), 180, "ASCII (Dell DMI Slash)"))
                if m.group(2) and not found_asset_tag:
                    at_val = m.group(2).decode('ascii', errors='ignore').strip()
                    if at_val and len(at_val) >= 3 and at_val not in ["NONE", "DEFAULT", "UNKNOWN"]:
                        found_asset_tag = at_val
                        found_asset_off = m.start(2)

        # Tier 1b: UTF-16LE Dell DMI Slash Pattern
        u16_slash = rb'/\x00((?:[A-Z0-9]\x00){7})/\x00'
        for m in re.finditer(u16_slash, data):
            tag_str = m.group(1).decode('utf-16le', errors='ignore')
            if DellDMIExtractor.is_valid_service_tag(tag_str):
                st_candidates.append((tag_str, m.start(1), 180, "UTF-16LE (Dell DMI Slash)"))

        # Tier 2: Standard Label Proximity in ASCII & UTF-16LE
        labels_ascii = [
            b'Service Tag:', b'Service Tag', b'ServiceTag:', b'ServiceTag',
            b'ST=', b'ST:', b'SVC TAG', b'TAG:', b'Dell Service Tag',
            b'S/N:', b'Serial Number:', b'System Service Tag'
        ]
        labels_u16 = [l.decode('ascii').encode('utf-16le') for l in labels_ascii]

        for lbl in labels_ascii:
            pos = 0
            while True:
                p = data.find(lbl, pos)
                if p == -1:
                    break
                chunk = data[p : p + len(lbl) + 64]
                matches = re.finditer(rb'(?<![A-Z0-9])[A-Z0-9]{7}(?![A-Z0-9])', chunk)
                for m in matches:
                    tag_str = m.group(0).decode('ascii')
                    if DellDMIExtractor.is_valid_service_tag(tag_str):
                        st_candidates.append((tag_str, p + m.start(), 150, "ASCII (Label)"))
                pos = p + 1

        for lbl in labels_u16:
            pos = 0
            while True:
                p = data.find(lbl, pos)
                if p == -1:
                    break
                chunk = data[p : p + len(lbl) + 128]
                matches = re.finditer(rb'(?:[A-Z0-9]\x00){7}', chunk)
                for m in matches:
                    tag_str = m.group(0).decode('utf-16le', errors='ignore')
                    if DellDMIExtractor.is_valid_service_tag(tag_str):
                        st_candidates.append((tag_str, p + m.start(), 150, "UTF-16LE (Label)"))
                pos = p + 1

        # Tier 3: SMBIOS Type 1 / Type 2 Table String Pool Proximity
        # Search for null-terminated 7-char alphanumeric tag within +/- 2KB of Dell manufacturer headers
        for smb_hdr in [b'Dell Inc.', b'Dell Computer Corporation', b'Dell Computer Corp', b'Dell System']:
            pos = 0
            while True:
                p = data.find(smb_hdr, pos)
                if p == -1:
                    break
                window_start = max(0, p - 2048)
                window_end = min(file_len, p + 2048)
                window = data[window_start : window_end]
                for m in re.finditer(rb'\x00([A-Z0-9]{7})\x00', window):
                    tag_str = m.group(1).decode('ascii')
                    if DellDMIExtractor.is_valid_service_tag(tag_str):
                        st_candidates.append((tag_str, window_start + m.start(1), 130, "ASCII (SMBIOS)"))
                pos = p + 1

        # Tier 4: DVAR Variable Store 7-character search
        if dvar_bytes:
            matches = re.finditer(rb'(?<![A-Z0-9])[A-Z0-9]{7}(?![A-Z0-9])', dvar_bytes)
            for m in matches:
                tag_str = m.group(0).decode('ascii')
                if DellDMIExtractor.is_valid_service_tag(tag_str):
                    if re.search(r'[A-Z]', tag_str):
                        tag_off = dvar_found + m.start()
                        st_candidates.append((tag_str, tag_off, 100, "ASCII (DVAR)"))

        # Selection of best candidate
        if st_candidates:
            # Score bonus for tags that contain both digits and letters (standard Dell Service Tag syntax)
            scored_candidates = []
            for tag_str, off, base_score, enc in st_candidates:
                score = base_score
                if any(c.isdigit() for c in tag_str) and any(c.isalpha() for c in tag_str):
                    score += 20
                if re.search(r'[G-Z]', tag_str):
                    score += 10
                scored_candidates.append((tag_str, off, score, enc))

            best_tag, best_off, best_score, best_enc = max(scored_candidates, key=lambda x: x[2])
            results["Details"]["Service Tag"] = best_tag
            results["Details"]["Serial Number"] = best_tag
            results["Offsets"]["Service Tag"] = f"0x{best_off:X}"
            results["Offsets"]["Serial Number"] = f"0x{best_off:X}"
            results["Lengths"]["Service Tag"] = len(best_tag)
            results["Lengths"]["Serial Number"] = len(best_tag)
            results["Encodings"]["Service Tag"] = best_enc
            results["Encodings"]["Serial Number"] = best_enc
            _log(f"[Dell] Service Tag: {best_tag} @ 0x{best_off:X} ({best_enc})")

        if found_asset_tag and "Asset Tag" not in results["Details"]:
            results["Details"]["Asset Tag"] = found_asset_tag
            results["Offsets"]["Asset Tag"] = f"0x{found_asset_off:X}"
            results["Lengths"]["Asset Tag"] = len(found_asset_tag)
            results["Encodings"]["Asset Tag"] = "ASCII"
            _log(f"[Dell] Asset Tag: {found_asset_tag} @ 0x{found_asset_off:X}")

        # ── 8. NORMALIZATION ────────────────────────────────────────────────
        if "Serial Number" not in results["Details"] and "PPID" in results["Details"]:
            results["Details"]["Serial Number"] = results["Details"]["PPID"]
            results["Offsets"]["Serial Number"] = results["Offsets"]["PPID"]
            results["Lengths"]["Serial Number"] = results["Lengths"]["PPID"]
            results["Encodings"]["Serial Number"] = results["Encodings"]["PPID"]
            _log(f"[Dell] Using PPID as Serial Number fallback: {results['Details']['Serial Number']}")

        # ── 9. MULTI-OCCURRENCE SCANNER ──────────────────────────────────────
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
        if "Service Tag" in results["Details"]:
            _record_all_instances("Service Tag", results["Details"]["Service Tag"], results["Offsets"].get("Service Tag", ""), "Service Tag")
            _record_all_instances("Serial Number", results["Details"]["Service Tag"], results["Offsets"].get("Serial Number", ""), "Serial Number")
        if "Asset Tag" in results["Details"]:
            _record_all_instances("Asset Tag", results["Details"]["Asset Tag"], results["Offsets"].get("Asset Tag", ""), "Asset Tag")
        if "PPID" in results["Details"]:
            _record_all_instances("PPID", results["Details"]["PPID"], results["Offsets"].get("PPID", ""), "PPID")

        return results
