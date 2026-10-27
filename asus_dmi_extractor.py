"""
asus_dmi_extractor.py - R1 BIOS Tool
Dedicated DMI and Variable Extractor for ASUS BIOS Firmware (AMI APTIO / InsydeH2O).

Supports:
  1. ASUS Series: ROG (Republic of Gamers), TUF Gaming, ZenBook, VivoBook, ProArt,
                  ExpertBook, StudioBook, ASUS Gaming (G/GL/GX series), Prime, X-series
  2. System Model Extraction:
     - Priority A: MFG0 / MFG NVAR/GPNV variable (e.g. X507MA, X507UBR, P2451FA, X410UQK)
     - Priority B: $MODIFYSIG$ structure (e.g. GL503GE, FX504GD)
     - Priority C: Global ROM ID pattern (e.g. X441UA.306, E203MA.008, X556UQK.007, X441NC.003, X555LAB.503, S451LN.306, X450LCP.205, X555LDB.303, X411UN.006, X407UB.006, S551LB.207)
     - Priority D: $FID firmware table (e.g. X441UA, X200MA, X540LJ, S451LN, X450LCP, S551LB, X441SA)
     - Priority E: Marketing Model Patterns (ROG Strix, TUF Gaming, ZenBook, VivoBook, ExpertBook)
  3. Serial Number Extraction:
     - 64KB Aligned Factory DMI Block (+0x00 offset, 15-char serial)
     - MFG0 / MFG variable (+0x05 offset, 15-char serial)
     - Validated 15-char ASUS serial regex with strict manufacturer markers
  4. Product Number / Part Number / SKU (90N... format)
  5. Motherboard / Board Serial Number (QCC..., ...MB, etc.)
  6. UUID (Mixed-endian binary SMBIOS GUID from 64KB DMI block @ +0x1ba or SMBIOS Type 1)
  7. MAC Address (NVRAM hex variable)
  8. Windows OEM Digital License Key (ACPI MSDM table)
  9. Raw DMI Block Registration (for safe DMI migration, backup, and injection)
"""

import os
import re
import struct


class AsusDMIExtractor:

    # Known blacklisted Windows keys (trial, generic, or placeholder)
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

    # ASUS OEM GUID: {7B59104A-C00D-4158-87FF-F04D6396A915} in LE bytes
    ASUS_OEM_GUID = b'\x4A\x10\x59\x7B\x0D\xC0\x58\x41\x87\xFF\xF0\x4D\x63\x96\xA9\x15'

    # AsusSmbiosVar GUID: {C2BD6458-4B3B-4900-877A-D46A4DBEAACC}
    ASUS_SMBIOS_GUID = b'\x58\x64\xBD\xC2\x3B\x4B\x00\x49\x87\x7A\xD4\x6A\x4D\xBE\xAA\xCC'

    # ASUS Serial validation markers
    ASUS_SN_MARKERS = [
        'N0', 'M0', 'K0', 'CV', 'CX', 'WU', 'GR', 'C0',
        'NX', 'NR', 'RCX', 'R7', 'R9', 'J7', 'J9', 'H5',
        'F3', 'FA', 'E3', 'E8', 'DC', 'DB', 'G5', 'G8'
    ]

    @staticmethod
    def _is_valid_asus_sn(sn: str) -> bool:
        if not sn or len(sn) != 15:
            return False
        if not re.match(r'^[A-Z0-9]{15}$', sn):
            return False
        # Disallow RAM part numbers
        if sn.startswith(('M471', 'M378', 'HMA8', 'HMT3', 'NT4G')):
            return False
        # Disallow timestamps and dates
        if sn.endswith('Z') or re.match(r'^[0-9]{10,14}$', sn):
            return False
        # Disallow CPU codenames
        if any(c in sn for c in ['LAKE', 'BRIDGE', 'WELL', 'VALLEY']):
            return False
        # Disallow repetitive/garbage strings
        if len(set(sn)) <= 3:
            return False
        # Disallow alternating repeating patterns (e.g. 0B0F0J0N... or 7B7F7J7N...)
        if len(set(sn[0::2])) <= 2 or len(set(sn[1::2])) <= 2:
            return False
        if sn.startswith(('000', 'FFF')):
            return False
        # Must contain at least one recognized ASUS serial marker
        return any(m in sn for m in AsusDMIExtractor.ASUS_SN_MARKERS)

    @staticmethod
    def _is_valid_uuid(u: str) -> bool:
        if not u or len(u) < 32:
            return False
        u_up = u.upper()
        if u_up.startswith(("00000000-0000-0000", "FFFFFFFF-FFFF-FFFF")):
            return False
        clean = u_up.replace("-", "").replace("0", "").replace("F", "")
        return len(clean) > 4

    @staticmethod
    def extract(bios_path: str, log_cb=None) -> dict:
        results = {
            "Brand": "ASUS",
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
            _log(f"[ASUS] Failed to read BIOS file: {e}")
            return results

        file_len = len(data)
        mfg_matches = list(re.finditer(rb'MFG[0-9]?\x00', data))

        # ── 1. SYSTEM MODEL DETECTION (Cascading 5-Tier Strategy) ─────────────
        model = None
        model_off = None
        model_src = None

        # Priority A: Global ROM ID pattern (e.g. X411UN.006, X441UA.306, E203MA.008, X556UQK.007)
        rom_candidates = []
        for m in re.finditer(rb'\b([A-Z][0-9]{3}[A-Z0-9]{1,4})\.([0-9]{3})\b', data):
            rom_name = m.group(1).decode('ascii')
            rom_ver = m.group(2).decode('ascii')
            if not rom_name.startswith(("INTEL", "AMIDE")):
                rom_candidates.append((rom_name, rom_ver, m.start()))
        if rom_candidates:
            c_name, c_ver, c_pos = rom_candidates[0]
            model = c_name
            model_off = c_pos
            model_src = f"ROM ID ({c_name}.{c_ver})"

        # Priority B: Check $MODIFYSIG$ structure (e.g. GL503GE, FX504GD, etc.)
        if not model:
            mod_sig = data.find(b'$MODIFYSIG$')
            if mod_sig != -1:
                chunk = data[mod_sig:mod_sig + 150]
                m = re.search(rb'\$MODIFYSIG\$[^A-Z]*([A-Z]{2}[0-9]{3}[A-Z0-9]{0,4})', chunk)
                if not m:
                    m = re.search(rb'\$MODIFYSIG\$[^A-Z0-9]*([A-Z0-9]{5,10})', chunk)
                if m:
                    cand = m.group(1).decode('ascii').rstrip('.')
                    if len(cand) >= 5:
                        model = cand
                        model_off = mod_sig + m.start(1)
                        model_src = f"$MODIFYSIG$ ({model})"

        # Priority C: Check $FID structure (e.g. X441UA, X200MA, X555LAB, S451LN, X450LCP, X540LJ)
        if not model:
            fid_m = re.search(rb'\$FID\x04\x78\x00([A-Za-z0-9_]+)', data)
            if fid_m:
                fid_str = fid_m.group(1).decode('ascii', errors='ignore')
                clean_m = re.sub(r'[^A-Za-z0-9]', '', fid_str)
                if len(clean_m) >= 4 and not clean_m.startswith(('1A', '1B')):
                    model = clean_m
                    model_off = fid_m.start(1)
                    model_src = f"$FID Structure ({model})"

        # Priority D: Check MFG0 / MFG NVAR/GPNV variable
        if not model:
            mfg_matches = list(re.finditer(rb'MFG[0-9]?\x00', data))
            for m in mfg_matches:
                pos = m.start()
                chunk = data[pos:pos + 400]
                rom_m = re.search(rb'([A-Z][0-9]{3}[A-Z0-9]{1,4})\.[0-9]{3}', chunk)
                if rom_m:
                    cand = rom_m.group(1).decode('ascii')
                    if cand not in ["NVAR", "GPNV"]:
                        model = cand
                        model_off = pos + rom_m.start(1)
                        model_src = f"MFG ROM ID ({model})"
                        break
                # Only recognize valid notebook series names (X, S, P, FX, GL, GX, UX, E, K, A)
                mod_m = re.search(rb'\b((?:X|S|P|E|K|A|F|UX|FX|GL|GX)[0-9]{3,4}[A-Z0-9]{1,4})\xff', chunk)
                if mod_m:
                    cand = mod_m.group(1).decode('ascii')
                    if cand not in ["NVAR", "GPNV", "MFG0", "MFG"]:
                        model = cand
                        model_off = pos + mod_m.start(1)
                        model_src = f"MFG Variable ({model})"
                        break

        # Priority D2: Fallback to $FID project code if still no model
        if not model:
            fid_m = re.search(rb'\$FID\x04\x78\x00([A-Za-z0-9_]+)', data)
            if fid_m:
                fid_str = fid_m.group(1).decode('ascii', errors='ignore')
                clean_m = re.sub(r'[^A-Za-z0-9]', '', fid_str)
                if len(clean_m) >= 4:
                    model = clean_m
                    model_off = fid_m.start(1)
                    model_src = f"$FID Code ({model})"

        # Priority E: Marketing Model Patterns (Check even if short ROM ID was found)
        mkt_model = None
        mkt_off = None
        mkt_pats = [
            rb'(ROG\s+Strix\s+[A-Za-z0-9\s\-]+)',
            rb'(ROG\s+Zephyrus\s+[A-Za-z0-9\s\-]+)',
            rb'(TUF\s+Gaming\s+[A-Za-z0-9\s\-]+)',
            rb'(ZenBook\s+[A-Za-z0-9\s\-]+)',
            rb'(VivoBook\s+[A-Za-z0-9\s\-]+)',
            rb'(ExpertBook\s+[A-Za-z0-9\s\-]+)',
            rb'(ASUS\s+(?:FX|GL|GX)[0-9]{3}[A-Za-z0-9\-]+)',
        ]
        for p in mkt_pats:
            m = re.search(p, data, re.IGNORECASE)
            if m:
                s = re.sub(r'[^a-zA-Z0-9\s\-]', '', m.group(1).decode('ascii', errors='ignore')).strip()
                if len(s) >= 6:
                    mkt_model = s
                    mkt_off = m.start(1)
                    break

        if mkt_model:
            # Full commercial marketing model wins as System Model
            results["Details"]["System Model"] = mkt_model
            results["Details"]["Model"] = mkt_model
            results["Offsets"]["System Model"] = f"0x{mkt_off:X}"
            results["Offsets"]["Model"] = f"0x{mkt_off:X}"
            results["Lengths"]["System Model"] = len(mkt_model)
            results["Encodings"]["System Model"] = "ascii"
            _log(f"[ASUS] Commercial Model: '{mkt_model}' @ 0x{mkt_off:X}")

            # Save the shorter ROM ID / Project Code as Board Model
            if model and model != mkt_model:
                results["Details"]["Board Model"] = model
                results["Offsets"]["Board Model"] = f"0x{model_off:X}" if model_off else ""
                results["Lengths"]["Board Model"] = len(model)
                results["Encodings"]["Board Model"] = "ascii"
                _log(f"[ASUS] Board / ROM ID: '{model}' via {model_src}")
        elif model:
            results["Details"]["System Model"] = model
            results["Details"]["Model"] = model
            results["Offsets"]["System Model"] = f"0x{model_off:X}" if model_off else ""
            results["Offsets"]["Model"] = f"0x{model_off:X}" if model_off else ""
            results["Lengths"]["System Model"] = len(model)
            results["Encodings"]["System Model"] = "ascii"
            _log(f"[ASUS] Model: '{model}' via {model_src}")

        # ── 2. SERIAL NUMBER & DMI BLOCK EXTRACTION ────────────────────────
        sn = None
        sn_off = None
        part_number = None
        board_sn = None
        uuid_str = None
        mac_addr = None
        dmi_block_registered = False

        # Source 1: 64KB Aligned Factory DMI Block
        for block_base in range(0, file_len, 0x10000):
            header = data[block_base:block_base + 64]
            m = re.match(rb'^([A-Z0-9]{15})\xff', header)
            if m:
                cand = m.group(1).decode('ascii')
                if AsusDMIExtractor._is_valid_asus_sn(cand):
                    sn = cand
                    sn_off = block_base

                    # Extract Part Number: 90N...
                    pn_chunk = data[block_base + 0x14:block_base + 0x40]
                    pn_m = re.search(rb'(90N[A-Z0-9\-]{8,20})', pn_chunk)
                    if pn_m:
                        part_number = pn_m.group(1).decode('ascii').rstrip('-')

                    # Extract Board Serial: QCC... or 15-18 chars
                    bsn_chunk = data[block_base + 0x28:block_base + 0x60]
                    bsn_m = re.search(rb'([A-Z0-9]{15,18})\xff', bsn_chunk)
                    if bsn_m:
                        board_sn = bsn_m.group(1).decode('ascii')

                    # Extract UUID at block_base + 0x1ba
                    if block_base + 0x1ba + 16 <= file_len:
                        uuid_raw = data[block_base + 0x1ba:block_base + 0x1ba + 16]
                        if uuid_raw != b'\xff' * 16 and uuid_raw != b'\x00' * 16:
                            try:
                                d1, d2, d3 = struct.unpack('<IHH', uuid_raw[:8])
                                d4 = uuid_raw[8:].hex().upper()
                                cand_uuid = f"{d1:08X}-{d2:04X}-{d3:04X}-{d4[:4]}-{d4[4:]}"
                                if AsusDMIExtractor._is_valid_uuid(cand_uuid):
                                    uuid_str = cand_uuid
                            except Exception:
                                pass

                    # Register Raw DMI Block
                    results["RawBlocks"]["ASUS_DMI_BLOCK"] = {
                        "start_offset": f"0x{block_base:X}",
                        "length": 0x1000,
                        "hex": data[block_base:block_base + 0x1000].hex(),
                        "region": "BIOS",
                        "relative_offset": f"0x{block_base:X}"
                    }
                    dmi_block_registered = True
                    _log(f"[ASUS] Found Factory 64KB DMI Block @ 0x{block_base:X} (SN: {sn})")
                    break

        # Source 2: MFG0 / MFG variable block
        if not sn:
            for m in mfg_matches:
                pos = m.start()
                chunk = data[pos:pos + 400]
                sn_m = re.search(rb'MFG[0-9]?\x00([A-Z0-9]{15})\xff', chunk)
                if sn_m:
                    cand = sn_m.group(1).decode('ascii')
                    if AsusDMIExtractor._is_valid_asus_sn(cand):
                        sn = cand
                        sn_off = pos + sn_m.start(1)

                        # Part number in chunk
                        if not part_number:
                            pn_m = re.search(rb'(90N[A-Z0-9\-]{8,20})', chunk)
                            if pn_m:
                                part_number = pn_m.group(1).decode('ascii').rstrip('-')

                        # Board Serial in chunk
                        if not board_sn:
                            bsn_m = re.search(rb'([A-Z0-9]{14,20}(?:MB|Q0)[0-9A-Z]*)', chunk)
                            if bsn_m:
                                board_sn = bsn_m.group(1).decode('ascii')

                        # Register Raw Block around MFG
                        mfg_block_start = max(0, (pos // 0x1000) * 0x1000)
                        if not dmi_block_registered and mfg_block_start + 0x1000 <= file_len:
                            results["RawBlocks"]["ASUS_MFG_BLOCK"] = {
                                "start_offset": f"0x{mfg_block_start:X}",
                                "length": 0x1000,
                                "hex": data[mfg_block_start:mfg_block_start + 0x1000].hex(),
                                "region": "BIOS",
                                "relative_offset": f"0x{mfg_block_start:X}"
                            }
                            dmi_block_registered = True
                        _log(f"[ASUS] Found MFG DMI Block @ 0x{pos:X} (SN: {sn})")
                        break

        # Source 3: Deep Scan for 15-char ASUS serial
        if not sn:
            for m in re.finditer(rb'\b([A-Z0-9]{15})\b', data):
                cand = m.group(1).decode('ascii', errors='ignore')
                if AsusDMIExtractor._is_valid_asus_sn(cand):
                    sn = cand
                    sn_off = m.start()
                    _log(f"[ASUS] Found Serial via Deep Scan @ 0x{sn_off:X} (SN: {sn})")
                    break

        if sn:
            results["Details"]["Serial Number"] = sn
            results["Offsets"]["Serial Number"] = f"0x{sn_off:X}" if sn_off else ""
            results["EndOffsets"]["Serial Number"] = f"0x{sn_off + 15:X}" if sn_off else ""
            results["Lengths"]["Serial Number"] = 15
            results["Encodings"]["Serial Number"] = "ascii"

        # Part Number
        if not part_number:
            pn_m = re.search(rb'\b(90N[A-Z0-9\-]{8,20})\b', data)
            if pn_m:
                part_number = pn_m.group(1).decode('ascii').rstrip('-')

        if part_number:
            results["Details"]["Part Number"] = part_number
            results["Details"]["Product Number"] = part_number
            _log(f"[ASUS] Part Number / SKU: {part_number}")

        # Board Serial
        if board_sn:
            results["Details"]["Board Serial"] = board_sn
            _log(f"[ASUS] Board Serial: {board_sn}")

        # ── 3. UUID DETECTION ──────────────────────────────────────────────
        if not uuid_str:
            # Check SMBIOS Type 1 anchors
            for anchor in [b'_SM_', b'_DMI_']:
                a_off = data.find(anchor)
                if a_off != -1:
                    chunk = data[a_off: min(file_len, a_off + 0x1000)]
                    for rel in range(0, len(chunk) - 24):
                        if chunk[rel] == 0x01 and 0x1B <= chunk[rel + 1] <= 0x80:
                            u_off = rel + 0x08
                            if u_off + 16 <= len(chunk):
                                raw_uuid = chunk[u_off: u_off + 16]
                                try:
                                    d1, d2, d3 = struct.unpack('<IHH', raw_uuid[:8])
                                    d4 = raw_uuid[8:].hex().upper()
                                    cand = f"{d1:08X}-{d2:04X}-{d3:04X}-{d4[:4]}-{d4[4:]}"
                                    if AsusDMIExtractor._is_valid_uuid(cand):
                                        uuid_str = cand
                                        break
                                except Exception:
                                    pass
                    if uuid_str:
                        break

        # Check formatted UUID string
        if not uuid_str:
            u_m = re.search(rb'\b([A-Fa-f0-9]{8}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{12})\b', data)
            if u_m:
                cand = u_m.group(1).decode('ascii').upper()
                if AsusDMIExtractor._is_valid_uuid(cand):
                    uuid_str = cand

        if uuid_str:
            results["Details"]["UUID"] = uuid_str
            _log(f"[ASUS] UUID: {uuid_str}")

        # ── 4. MAC ADDRESS EXTRACTION ──────────────────────────────────────
        mac_m = re.search(rb'[!"]([0-9A-F]{12})[\x00\xff]', data)
        if mac_m:
            raw_mac = mac_m.group(1).decode('ascii')
            mac_addr = ":".join(raw_mac[i:i + 2] for i in range(0, 12, 2))
            results["Details"]["MAC Address"] = mac_addr
            results["Offsets"]["MAC Address"] = f"0x{mac_m.start(1):X}"
            _log(f"[ASUS] MAC Address: {mac_addr}")

        # ── 6. MULTI-OCCURRENCE SCANNER ──────────────────────────────────────
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
        if "Board Model" in results["Details"]:
            _record_all_instances("System Model", results["Details"]["Board Model"], results["Offsets"].get("Board Model", ""), "Board Model")
        if "Serial Number" in results["Details"]:
            _record_all_instances("Serial Number", results["Details"]["Serial Number"], results["Offsets"].get("Serial Number", ""), "Serial")

        return results
