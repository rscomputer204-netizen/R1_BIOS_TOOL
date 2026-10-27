"""
acer_dmi_extractor.py - R1 BIOS Tool
Dedicated DMI and Variable Extractor for Acer BIOS Firmware (InsydeH2O / AMI / Phoenix).

Supports:
  1. Acer Series: Aspire, Nitro, Predator, Swift, Spin, TravelMate, Extensa, ConceptD, Enduro, Gateway, Packard Bell
  2. InsydeH2O $BVD$ and CustomDmiVar Raw Block Extraction (RawBlocks["ACER_BVD"] / RawBlocks["ACER_DMI"])
  3. System Model Extraction (Aspire, Nitro, Predator, Swift, TravelMate, etc.)
  4. 22-Character Acer Serial Numbers (NX..., NH..., UN..., DT..., NC..., LU..., LX..., etc.)
  5. Acer SNID (11 or 12 decimal digits)
  6. BaseBoard Serial Number
  7. System UUID (Binary GUID or 32-hex / 36-char formatted string)
  8. Windows OEM Digital License Key (ACPI MSDM table)
"""

import os
import re


class AcerDMIExtractor:
    ACER_SERIAL_PREFIXES = [
        b'NX', b'NH', b'UN', b'DT', b'NC', b'MR', b'MF',
        b'LU', b'LX', b'ZL', b'PO', b'MM', b'SK', b'SV', b'BL', b'PF'
    ]

    BLACKLISTED_KEYS = {
        "VK7JG-NPHTM-C97JM-9MPGT-3V66T",
        "YTMG3-N6DKC-DKB77-7M9GH-8HVX7",
        "BT79Q-G7N6G-PGBYW-4YWX6-6F4BT",
        "TX9XD-98N7V-6WMQ6-BX7FG-H8Q99",
        "BBBBB-BBBBB-BBBBB-BBBBB-BBBBB",
        "11111-11111-11111-11111-11111",
        "00000-00000-00000-00000-00000",
        "XXXXX-XXXXX-XXXXX-XXXXX-XXXXX",
    }

    BLACKLISTED_SERIALS = {
        "0000000000000000000000",
        "1111111111111111111111",
        "FFFFFFFFFFFFFFFFFFFFFF",
        "1234567890123456789012",
        "0123456789012345678901",
        "ABCDEFGHIJKLMNOPQRSTUV",
    }

    @staticmethod
    def _is_valid_snid(snid_str: str) -> bool:
        if not snid_str or len(snid_str) not in (11, 12) or not snid_str.isdigit():
            return False
        if len(set(snid_str)) <= 2:
            return False
        if snid_str in ("01234567890", "12345678901", "23456789012", "012345678901", "123456789012"):
            return False
        return True

    @staticmethod
    def _is_valid_serial(sn: str) -> bool:
        if not sn or len(sn) != 22:
            return False
        if sn in AcerDMIExtractor.BLACKLISTED_SERIALS:
            return False
        if not re.match(r'^[A-Z0-9]{22}$', sn):
            return False
        if len(set(sn)) <= 3:
            return False
        return True

    @staticmethod
    def extract(bios_path: str, log_cb=None) -> dict:
        results = {
            "Brand": "Acer",
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
            _log(f"[Acer] Failed to read BIOS file: {e}")
            return results

        file_len = len(data)

        # ── 1. DETECT INSYDEH2O $BVD$ / DMI RAW BLOCKS ─────────────────────
        # Check InsydeH2O $BVD$ header
        bvd_off = data.find(b'$BVD$')
        if bvd_off != -1:
            # $BVD$ typically holds 1KB to 2KB version and config data
            bvd_size = 0x800  # 2KB
            if bvd_off + bvd_size <= file_len:
                results["RawBlocks"]["ACER_BVD"] = {
                    "start_offset": f"0x{bvd_off:X}",
                    "length": bvd_size,
                    "hex": data[bvd_off : bvd_off + bvd_size].hex(),
                    "region": "BIOS",
                    "relative_offset": f"0x{bvd_off:X}"
                }
                _log(f"[Acer] Found InsydeH2O $BVD$ Structure @ 0x{bvd_off:X} ({bvd_size}B)")

        # Check Insyde CustomDmiVar / DmiVar variable store
        dmi_var_off = -1
        for sig in [b'CustomDmiVar\x00', b'CustomDmiVar', b'DmiVar\x00']:
            p = data.find(sig)
            if p != -1:
                dmi_var_off = p
                break

        # Check Insyde DmiVar GUID: 2F90832F-650B-4813-8E5A-A61F03358004 in LE
        insyde_guid = b'\x2F\x83\x90\x2F\x0B\x65\x13\x48\x8E\x5A\xA6\x1F\x03\x35\x80\x04'
        if dmi_var_off == -1:
            dmi_var_off = data.find(insyde_guid)

        if dmi_var_off != -1:
            var_size = 0x1000  # 4KB block
            # Align down to 0x100 boundary if near
            start_align = max(0, (dmi_var_off // 0x100) * 0x100)
            if start_align + var_size <= file_len:
                results["RawBlocks"]["ACER_DMI"] = {
                    "start_offset": f"0x{start_align:X}",
                    "length": var_size,
                    "hex": data[start_align : start_align + var_size].hex(),
                    "region": "BIOS",
                    "relative_offset": f"0x{start_align:X}"
                }
                _log(f"[Acer] Found Acer/Insyde DMI Variable Store @ 0x{start_align:X} ({var_size}B)")

        # ── 2. SYSTEM MODEL DETECTION ──────────────────────────────────────
        # Acer line-ups: Aspire, Nitro, Predator, Swift, TravelMate, Spin, Extensa, ConceptD, Enduro, Gateway
        model_patterns = [
            # Aspire: Aspire 5 A515-56G, Aspire A715-79G, Aspire Vero AV15-51, Aspire 3 A315-58
            rb'(Aspire(?:\s+(?:[0-9]|Vero|E|V|S|One|Switch))*\s+[A-Z0-9]+-[A-Z0-9]+)',
            # Nitro: Nitro 5 AN515-58, Nitro 16 AN16-41, Nitro AN515-45
            rb'(Nitro(?:\s+[0-9]+)?\s+[A-Z0-9]+-[A-Z0-9]+)',
            # Predator: Predator Helios 300 PH315-54, Predator Triton 500 PT515-52
            rb'(Predator(?:\s+[A-Za-z0-9]+)*\s+[A-Z0-9]+-[A-Z0-9]+)',
            # Swift: Swift 3 SF314-511, Swift Go SFG14-71, Swift Edge SFE16-43, Swift X SFX14-41G
            rb'(Swift(?:\s+(?:[0-9]|Go|Edge|X))*\s+[A-Z0-9]+-[A-Z0-9]+)',
            # TravelMate: TravelMate P214-53, TravelMate Spin B3 TMB311R-32, TravelMate Vero TMV15-51
            rb'(TravelMate(?:\s+[A-Za-z0-9]+)*\s+[A-Z0-9]+-[A-Z0-9]+)',
            # Spin: Spin 3 SP314-54N, Spin 5 SP513-55N
            rb'(Spin(?:\s+[0-9]+)?\s+[A-Z0-9]+-[A-Z0-9]+)',
            # Extensa: Extensa 15 EX215-54
            rb'(Extensa(?:\s+[0-9]+)?\s+[A-Z0-9]+-[A-Z0-9]+)',
            # ConceptD: ConceptD 3 CC314-72G, ConceptD 5 CN515-72
            rb'(ConceptD(?:\s+[0-9]+)*\s+[A-Z0-9]+-[A-Z0-9]+)',
            # Generic Aspire/Nitro/Predator model without hyphen
            rb'((?:Aspire|Nitro|Predator|Swift|TravelMate|Spin|Extensa)\s+[A-Z0-9]{3,10})',
        ]

        model_candidates = []
        for pat in model_patterns:
            for m in re.finditer(pat, data, re.IGNORECASE):
                s_off = m.start()
                raw_m = m.group(1).decode('ascii', errors='ignore').strip()
                if len(raw_m) >= 6:
                    sc = 100
                    if "-" in raw_m: sc += 150
                    if any(c.isdigit() for c in raw_m): sc += 100
                    model_candidates.append((raw_m, s_off, s_off + len(raw_m), len(raw_m), "ascii", sc))

        # UTF-16LE search
        for prefix_match in re.finditer(rb'(?:A\x00s\x00p\x00i\x00r\x00e\x00|N\x00i\x00t\x00r\x00o\x00|P\x00r\x00e\x00d\x00a\x00t\x00o\x00r\x00|S\x00w\x00i\x00f\x00t\x00|T\x00r\x00a\x00v\x00e\x00l\x00M\x00a\x00t\x00e\x00)', data):
            p_start = prefix_match.start()
            chunk = data[p_start : min(file_len, p_start + 120)]
            try:
                dec = chunk.decode('utf-16le', errors='ignore').split('\x00')[0].strip()
                if any(dec.startswith(k) for k in ["Aspire", "Nitro", "Predator", "Swift", "TravelMate"]):
                    clean_m = re.sub(r'[^a-zA-Z0-9\s\-]', '', dec).strip()
                    if len(clean_m) >= 6:
                        raw_u16_len = len(clean_m) * 2
                        sc = 100
                        if "-" in clean_m: sc += 150
                        if any(c.isdigit() for c in clean_m): sc += 100
                        model_candidates.append((clean_m, p_start, p_start + raw_u16_len, raw_u16_len, "utf-16le", sc))
            except Exception:
                pass

        if model_candidates:
            model_candidates.sort(key=lambda x: x[5], reverse=True)
            m_val, s_off, e_off, length, enc, _ = model_candidates[0]
            results["Details"]["System Model"] = m_val
            results["Offsets"]["System Model"] = f"0x{s_off:X}"
            results["EndOffsets"]["System Model"] = f"0x{e_off:X}"
            results["Lengths"]["System Model"] = length
            results["Encodings"]["System Model"] = enc
            _log(f"[Acer] Model: '{m_val}' @ 0x{s_off:X} ({enc})")

        # ── 3. ACER 22-CHAR SERIAL NUMBER DETECTION ────────────────────────
        # Acer serials are 22 alphanumeric chars, commonly starting with NX, NH, UN, DT, etc.
        serial_found = None

        # A. Priority 1: Prefix-based match (ASCII)
        for pref in AcerDMIExtractor.ACER_SERIAL_PREFIXES:
            pat = rb'\b' + re.escape(pref) + rb'[A-Z0-9]{20}\b'
            for m in re.finditer(pat, data):
                sn = m.group().decode('ascii', errors='ignore')
                if AcerDMIExtractor._is_valid_serial(sn):
                    serial_found = (sn, m.start(), m.end(), 22, "ascii")
                    break
            if serial_found:
                break

        # B. Priority 2: UTF-16LE Prefix-based match
        if not serial_found:
            for pref in AcerDMIExtractor.ACER_SERIAL_PREFIXES:
                u16_pref = pref.decode('ascii').encode('utf-16le')
                pat = re.escape(u16_pref) + rb'(?:[A-Z0-9]\x00){20}'
                m = re.search(pat, data)
                if m:
                    sn = m.group().decode('utf-16le', errors='ignore')
                    if AcerDMIExtractor._is_valid_serial(sn):
                        serial_found = (sn, m.start(), m.end(), len(m.group()), "utf-16le")
                        break

        # C. Priority 3: Search near 'Serial Number' or 'SerialNumber' or 'Acer'
        if not serial_found:
            for lbl in [b'Serial Number', b'SerialNumber', b'SystemSerialNumber', b'Acer']:
                for m_lbl in re.finditer(re.escape(lbl), data):
                    c_start = max(0, m_lbl.start() - 256)
                    c_end = min(file_len, m_lbl.end() + 256)
                    chunk = data[c_start:c_end]
                    for m_sn in re.finditer(rb'\b[A-Z0-9]{22}\b', chunk):
                        sn = m_sn.group().decode('ascii', errors='ignore')
                        if AcerDMIExtractor._is_valid_serial(sn):
                            abs_start = c_start + m_sn.start()
                            abs_end = c_start + m_sn.end()
                            serial_found = (sn, abs_start, abs_end, 22, "ascii")
                            break
                    if serial_found:
                        break
                if serial_found:
                    break

        if serial_found:
            sn_val, s_off, e_off, length, enc = serial_found
            results["Details"]["Serial Number"] = sn_val
            results["Offsets"]["Serial Number"] = f"0x{s_off:X}"
            results["EndOffsets"]["Serial Number"] = f"0x{e_off:X}"
            results["Lengths"]["Serial Number"] = length
            results["Encodings"]["Serial Number"] = enc
            _log(f"[Acer] Serial Number: '{sn_val}' @ 0x{s_off:X} ({enc})")

        # ── 4. ACER SNID DETECTION (11 OR 12 DIGITS) ───────────────────────
        snid_found = None

        # A. Search with explicit SNID labels (ASCII & UTF-16LE)
        # e.g. SNID: 12345678901, SNID = 12345678901, SNID\x0012345678901
        for lbl_pat in [rb'SNID[:\s=]*([0-9]{11,12})\b', rb'S\x00N\x00I\x00D\x00[:\x00\s\x00=]*((?:[0-9]\x00){11,12})']:
            m = re.search(lbl_pat, data, re.IGNORECASE)
            if m:
                raw_bytes = m.group(1)
                is_u16 = b'\x00' in raw_bytes
                val = raw_bytes.decode('utf-16le' if is_u16 else 'ascii', errors='ignore').strip()
                if AcerDMIExtractor._is_valid_snid(val):
                    val_start = m.start(1)
                    val_end = m.end(1)
                    snid_found = (val, val_start, val_end, len(raw_bytes), "utf-16le" if is_u16 else "ascii")
                    break

        # B. Search proximity near Serial Number if SNID not found yet
        if not snid_found and serial_found:
            sn_abs = serial_found[1]
            prox_start = max(0, sn_abs - 512)
            prox_end = min(file_len, sn_abs + 512)
            prox_chunk = data[prox_start:prox_end]
            for m_num in re.finditer(rb'\b([0-9]{11,12})\b', prox_chunk):
                cand = m_num.group(1).decode('ascii', errors='ignore')
                if AcerDMIExtractor._is_valid_snid(cand):
                    abs_s = prox_start + m_num.start(1)
                    abs_e = prox_start + m_num.end(1)
                    snid_found = (cand, abs_s, abs_e, len(cand), "ascii")
                    break

        if snid_found:
            snid_val, s_off, e_off, length, enc = snid_found
            results["Details"]["SNID"] = snid_val
            results["Offsets"]["SNID"] = f"0x{s_off:X}"
            results["EndOffsets"]["SNID"] = f"0x{e_off:X}"
            results["Lengths"]["SNID"] = length
            results["Encodings"]["SNID"] = enc
            _log(f"[Acer] SNID: '{snid_val}' @ 0x{s_off:X} ({enc})")

        # ── 5. BASEBOARD SERIAL / PRODUCT ──────────────────────────────────
        # Acer mainboards often start with NB... or have Compal/Quanta codes (e.g. LA-..., DA0...)
        board_found = None
        for b_pat in [rb'\b(NB[A-Z0-9]{12,22})\b', rb'\b(DA0[A-Z0-9]{8,12})\b', rb'\b(LA-[A-Z0-9]{4,8}P?)\b']:
            m = re.search(b_pat, data)
            if m:
                b_val = m.group(1).decode('ascii', errors='ignore')
                board_found = (b_val, m.start(), m.end(), len(b_val), "ascii")
                break

        if board_found:
            b_val, s_off, e_off, length, enc = board_found
            results["Details"]["Board Serial"] = b_val
            results["Offsets"]["Board Serial"] = f"0x{s_off:X}"
            results["EndOffsets"]["Board Serial"] = f"0x{e_off:X}"
            results["Lengths"]["Board Serial"] = length
            results["Encodings"]["Board Serial"] = enc
            _log(f"[Acer] Board Serial: '{b_val}' @ 0x{s_off:X}")

        # ── 6. UUID DETECTION ──────────────────────────────────────────────
        # Search UUID string or SMBIOS Type 1 UUID
        uuid_found = None
        for u_pat in [
            rb'UUID[:\s=]*([A-Fa-f0-9]{8}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{12})',
            rb'\b([A-Fa-f0-9]{8}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{12})\b'
        ]:
            m = re.search(u_pat, data)
            if m:
                u_str = m.group(1).decode('ascii', errors='ignore').upper()
                if not u_str.startswith("00000000") and not u_str.startswith("FFFFFFFF"):
                    uuid_found = (u_str, m.start(1), m.end(1), len(u_str), "ascii")
                    break

        if uuid_found:
            u_val, s_off, e_off, length, enc = uuid_found
            results["Details"]["UUID"] = u_val
            results["Offsets"]["UUID"] = f"0x{s_off:X}"
            results["EndOffsets"]["UUID"] = f"0x{e_off:X}"
            results["Lengths"]["UUID"] = length
            results["Encodings"]["UUID"] = enc
            _log(f"[Acer] UUID: '{u_val}' @ 0x{s_off:X}")

        # ── 7. WINDOWS OEM DIGITAL LICENSE KEY (MSDM) ──────────────────────
        msdm_sig = data.find(b'MSDM')
        if msdm_sig != -1:
            msdm_chunk = data[msdm_sig : min(file_len, msdm_sig + 256)]
            key_match = re.search(rb'([A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5})', msdm_chunk)
            if key_match:
                key = key_match.group(1).decode('ascii', errors='ignore')
                if key not in AcerDMIExtractor.BLACKLISTED_KEYS:
                    abs_k_start = msdm_sig + key_match.start()
                    results["Details"]["Windows OEM Key"] = key
                    results["Offsets"]["Windows OEM Key"] = f"0x{abs_k_start:X}"
                    results["EndOffsets"]["Windows OEM Key"] = f"0x{abs_k_start + 29:X}"
                    results["Lengths"]["Windows OEM Key"] = 29
                    results["Encodings"]["Windows OEM Key"] = "ascii"
                    _log(f"[Acer] Windows OEM License Key: '{key}' @ 0x{abs_k_start:X}")

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
        if "SNID" in results["Details"]:
            _record_all_instances("SNID", results["Details"]["SNID"], results["Offsets"].get("SNID", ""), "SNID")

        return results
