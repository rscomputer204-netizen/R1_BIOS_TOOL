import os
import re
import struct

class HPDMIExtractor:
    """
    HP BIOS DMI Extractor — Targeted, GUID-based extraction.

    Discovered from real HP BIOS firmware analysis:
    All HP DMI data is stored inside the BIOS Region's VSS/VSS2 NVRAM store
    as EFI variables identified by specific GUIDs.

    Variable Name (title bar)     GUID                                        Fields contained
    ──────────────────────────────────────────────────────────────────────────────────────────
    HP_MUD    20AB3EB1-3C8F-4A4C-B87E-372426066D97  Serial, Model, SKU, Feature Byte
    HP_CSN    C7DD7777-DE65-8A2F-6545-6642A65539EC  Serial Number (alternate)
    HP_SKU    C7331678-1F65-2A2F-6545-6642A65539EC  SKU / Product Number
    HP_MODEL  05299C28-3958-4C60-084B-A53675B6FF3B  Product Model name
    HP_TAGS   FB3B9ECE-4ABA-4933-B49D-B4D67D892351  Secondary tags
    HP_MAC    3F02B9F8-9810-4560-9738-2394020E6FD1  MAC Address
    BuildId   GfxFactoryConfigFlags (ASCII name)    Build ID string
    """

    # ──────────────────────────────────────────────────────────────────────────
    # GUID bytes in little-endian EFI binary format
    # Each GUID is stored as: DWORD(LE) WORD(LE) WORD(LE) 8-BYTES(BE)
    # ──────────────────────────────────────────────────────────────────────────
    HP_GUIDS = {
        "HP_MUD":   bytes.fromhex("B13EAB20 8F3C 4C4A B87E372426066D97".replace(" ", "")),
        "HP_CSN":   bytes.fromhex("7777DDC7 65DE 2F8A 65456642A65539EC".replace(" ", "")),
        "HP_SKU":   bytes.fromhex("783631C7 651F 2F2A 65456642A65539EC".replace(" ", "")),
        "HP_MODEL": bytes.fromhex("289C2905 5839 604C 084BA53675B6FF3B".replace(" ", "")),
        "HP_TAGS":  bytes.fromhex("CE9E3BFB BA4A 3349 B49DB4D67D892351".replace(" ", "")),
        "HP_MAC":   bytes.fromhex("F8B9023F 1098 6045 97382394020E6FD1".replace(" ", "")),
    }

    # HP_MUD data structure — fixed offsets observed from screenshots:
    # All screenshots showed the SAME internal layout for HP_MUD:
    #
    # Offset  Size  Field
    # 0x00    2     Header/flags (AA 55)
    # 0x02    2     Data length / version
    # 0x04    N     Padding (00 bytes)
    # ...
    # The actual text fields are UTF-16LE encoded, separated by 00 00
    # Observed field order in HP_MUD (from ASCII column analysis):
    #   1. #U? (control header)
    #   2. Padding
    #   3. ~7$& marker then H.P. (HP manufacturer string)
    #   4. _M.U.D... (MUD identifier)
    #   5. S.C.G. / C.N.D. etc. → Serial Number prefix
    #   6. Numbers → Serial Number digits
    #   7. Y.F. / K.5. / Q.1. etc → model sub-version
    #   8. Padding
    #   9. A.B. → Feature Byte / SKU portion
    #   10. _  → separator
    #   11. System block strings (Book model, ProBook, EliteBook etc.)
    #   12. P.G... → Product Number (e.g. P.G.S.M.A.0.0.W.)
    #   13. B... → another serial variant
    #   14. P . E l i t e B o o k → model name in UTF16

    # Serial Number known prefixes (HP factory codes)
    HP_SN_PREFIXES = [
        "5CD", "5CG", "CND", "CNU", "CNF", "CNX",
        "8CG", "CZC", "SGH", "MXL", "TRF", "G6S",
        "BRG", "JPH", "INI", "TW",  "6CM", "2UA",
        "3CR", "7CR", "G3C", "2VQ", "HNT", "NTB",
        "1WT", "4CE", "6CE", "3CE", "PQ", "JP",
    ]

    # Common HP MAC OUI prefixes (first 3 bytes)
    HP_MAC_OUIS = [
        "0c:96:e6", "98:fa:9b", "b4:b6:86", "a8:97:dc",
        "40:b0:34", "d8:9e:f3", "10:02:b5", "5c:b9:01",
        "3c:a6:f6", "e4:e7:49",
    ]

    @staticmethod
    def _guid_bytes(guid_str: str) -> bytes:
        """Convert GUID string (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx) to EFI LE binary."""
        parts = guid_str.replace("-", "")
        # EFI GUID: first 3 groups LE, last group big-endian
        d1 = int(parts[0:8], 16)
        d2 = int(parts[8:12], 16)
        d3 = int(parts[12:16], 16)
        d4 = bytes.fromhex(parts[16:32])
        return struct.pack("<IHH", d1, d2, d3) + d4

    @staticmethod
    def _find_guid_blocks(content: bytes, guid_bytes: bytes, window: int = 512) -> list:
        """Find all occurrences of a GUID and return (offset, data_chunk) pairs."""
        results = []
        start = 0
        while True:
            pos = content.find(guid_bytes, start)
            if pos == -1:
                break
            # Grab data before and after the GUID (NVRAM variables have name before GUID)
            block_start = max(0, pos - 64)
            block_end = min(len(content), pos + len(guid_bytes) + window)
            results.append((pos, content[block_start:block_end]))
            start = pos + 1
        return results

    @staticmethod
    def _decode_utf16le_strings(data: bytes, min_len: int = 3) -> list:
        """Extract all printable UTF-16LE strings from a binary block."""
        strings = []
        i = 0
        current = []
        while i < len(data) - 1:
            ch = data[i] | (data[i+1] << 8)
            if 0x20 <= ch <= 0x7E:
                current.append(chr(ch))
            else:
                if len(current) >= min_len:
                    s = ''.join(current).strip()
                    if s:
                        strings.append(s)
                current = []
            i += 2
        if len(current) >= min_len:
            s = ''.join(current).strip()
            if s:
                strings.append(s)
        return strings

    @staticmethod
    def _decode_ascii_strings(data: bytes, min_len: int = 3) -> list:
        """Extract all printable ASCII strings from a binary block."""
        strings = []
        current = []
        for b in data:
            if 0x20 <= b <= 0x7E:
                current.append(chr(b))
            else:
                if len(current) >= min_len:
                    s = ''.join(current).strip()
                    if s:
                        strings.append(s)
                current = []
        if len(current) >= min_len:
            s = ''.join(current).strip()
            if s:
                strings.append(s)
        return strings

    @staticmethod
    def _find_hp_serial(strings: list) -> str | None:
        """Identify HP serial number from a list of decoded strings."""
        prefixes = HPDMIExtractor.HP_SN_PREFIXES
        for s in strings:
            s_upper = s.upper().strip()
            for pref in prefixes:
                if s_upper.startswith(pref) and 8 <= len(s_upper) <= 15:
                    # Validate: serial should be alphanumeric only
                    if re.match(r'^[A-Z0-9]+$', s_upper):
                        return s_upper
        return None

    @staticmethod
    def _score_hp_model(s: str) -> float:
        """
        Calculates a confidence score for an HP model candidate.
        Higher score = genuine commercial product model (e.g. 'HP EliteBook 830 G6').
        Lower score = internal board/config ID (e.g. '103C_5336AN HP EliteBook').
        """
        score = 0.0
        s_clean = s.strip()
        s_lower = s_clean.lower()

        model_keywords = [
            "elitebook", "probook", "zbook", "spectre", "envy", "pavilion",
            "omen", "victus", "dragonfly", "folio", "elite", "stream",
            "chromebook", "mini", "tower", "desktop", "laptop"
        ]
        matched_kw = False
        for kw in model_keywords:
            if kw in s_lower:
                matched_kw = True
                score += 100.0
                break

        if not matched_kw:
            return 0.0

        # Commercial generation and model number bonus (e.g. '830 G6', '450 G8', 'G5', 'x360')
        if re.search(r'\b[0-9]{3,4}\s+G[0-9]{1,2}\b', s_clean, re.IGNORECASE):
            score += 250.0
        elif re.search(r'\bG[0-9]{1,2}\b', s_clean, re.IGNORECASE):
            score += 150.0
        elif re.search(r'\b[0-9]{3,4}\b', s_clean):
            score += 100.0
        elif re.search(r'\b(?:13|14|15|16|17)-[a-z0-9]+\b', s_lower):
            score += 180.0

        # Starts with 'HP ' or 'Hewlett-Packard'
        if s_clean.startswith("HP "):
            score += 50.0

        # PENALTY: starts with internal Board ID / SKU prefix like '101C_5J36AN ' or '103C_5336AN '
        if re.match(r'^[A-Z0-9]{4,6}_[A-Z0-9]{4,8}\b', s_clean, re.IGNORECASE):
            score -= 150.0

        # PENALTY: contains internal underscore notation
        if "_" in s_clean:
            score -= 40.0

        return score

    @staticmethod
    def _find_hp_models(strings: list) -> list:
        """
        Identify ALL HP model name candidates from decoded strings,
        sorted by quality score descending.
        Returns list of (candidate_string, score).
        """
        model_keywords = [
            "EliteBook", "ProBook", "ZBook", "Spectre", "Envy", "Pavilion",
            "Omen", "Victus", "Dragonfly", "Folio", "Elite", "Stream",
            "Chromebook", "Mini", "Tower", "Desktop", "Laptop",
        ]
        candidates = []
        seen = set()
        for s in strings:
            for kw in model_keywords:
                if kw.lower() in s.lower() and len(s) >= 6:
                    cleaned = re.sub(r'[^a-zA-Z0-9\s\-\(\)\/_]', '', s).strip()
                    if cleaned and cleaned not in seen:
                        seen.add(cleaned)
                        score = HPDMIExtractor._score_hp_model(cleaned)
                        candidates.append((cleaned, score))
                    break

        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates

    @staticmethod
    def _find_hp_model(strings: list) -> str | None:
        """Legacy compatibility helper: returns highest ranked model."""
        models = HPDMIExtractor._find_hp_models(strings)
        return models[0][0] if models else None

    @staticmethod
    def _locate_field_in_block(block: bytes, block_start: int, val: str):
        """Locates exact absolute byte offset, end offset, byte length, and encoding for a string value in a block."""
        if not val or not isinstance(val, str):
            return None
        val_clean = val.strip()
        for enc in ['utf-16-le', 'ascii']:
            candidates = [val_clean]
            if ' ' in val_clean:
                candidates.append(val_clean.replace(' ', '_'))
                parts = val_clean.split()
                if len(parts) >= 2:
                    candidates.append(parts[0] + '_' + ' '.join(parts[1:]))
            for cand in candidates:
                try:
                    b = cand.encode(enc)
                    rel = block.find(b)
                    if rel != -1:
                        abs_s = block_start + rel
                        abs_e = abs_s + len(b)
                        enc_name = "UTF-16LE" if enc == 'utf-16-le' else "ASCII"
                        return abs_s, abs_e, len(b), enc_name
                except Exception:
                    pass
        return None

    @staticmethod
    def _find_hp_sku(strings: list) -> str | None:
        """HP SKU/Product Number: format like XXXXXX#YYY or 7+ alphanumeric chars."""
        for s in strings:
            s = s.strip()
            # Format: e.g. "8BN35UA#ABA" or "Z4B44AV"
            if re.match(r'^[A-Z0-9]{6,8}#[A-Z]{3}$', s):
                return s
            # Alternative: pure alphanumeric 7-char (product number)
            if re.match(r'^[A-Z0-9]{7}$', s) and s.isupper():
                return s
        return None

    @staticmethod
    def _find_hp_mac(data: bytes) -> str | None:
        i = 0
        while i < len(data) - 6:
            mac = data[i:i+6]
            if (mac[0] not in (0x00, 0xFF) and mac != b'\xff\xff\xff\xff\xff\xff'
                    and mac != b'\x00\x00\x00\x00\x00\x00'):
                mac_str = ':'.join(f'{b:02x}' for b in mac)
                if mac[0] & 0x01 == 0:
                    return mac_str.upper()
            i += 1
        return None

    @staticmethod
    def _find_feature_byte(strings: list, data: bytes) -> str | None:
        for i, s in enumerate(strings):
            if 'BID' in s.upper() and i + 1 < len(strings):
                candidate = strings[i+1].strip()
                if len(candidate) >= 4:
                    return candidate
        bid_match = re.search(rb'BID\s{0,4}([A-Za-z0-9]{3,10})', data)
        if bid_match:
            return bid_match.group(1).decode('ascii', errors='ignore').strip()
        for s in strings:
            if re.match(r'^[A-Za-z0-9\+\/]{10,}={0,2}$', s) and len(s) >= 12:
                s_lower = s.lower()
                if any(x in s_lower for x in ["flags", "config", "muddata", "blob", "options", "setup", "peihp", "hpbios", "module"]):
                    continue
                return s
        return None

    @staticmethod
    def _extract_from_mud_block(data: bytes) -> dict:
        result = {}
        ascii_strings = HPDMIExtractor._decode_ascii_strings(data)
        utf16_strings = HPDMIExtractor._decode_utf16le_strings(data)
        all_strings = utf16_strings + ascii_strings

        sn = HPDMIExtractor._find_hp_serial(all_strings)
        if sn: result["Serial Number"] = sn
        models = HPDMIExtractor._find_hp_models(all_strings)
        if models:
            result["System Model"] = models[0][0]
            alt_list = [m[0] for m in models[1:]]
            if alt_list:
                result["Alt Models"] = alt_list
        sku = HPDMIExtractor._find_hp_sku(all_strings)
        if sku: result["Product Number"] = sku
        fb = HPDMIExtractor._find_feature_byte(all_strings, data)
        if fb: result["Feature Byte"] = fb
        return result

    @staticmethod
    def _extract_csn_block(data: bytes) -> dict:
        result = {}
        utf16_strings = HPDMIExtractor._decode_utf16le_strings(data, min_len=6)
        sn = HPDMIExtractor._find_hp_serial(utf16_strings)
        if sn: result["Serial Number (CSN)"] = sn
        return result

    @staticmethod
    def _extract_sku_block(data: bytes) -> dict:
        result = {}
        utf16_strings = HPDMIExtractor._decode_utf16le_strings(data, min_len=4)
        ascii_strings = HPDMIExtractor._decode_ascii_strings(data, min_len=4)
        sku = HPDMIExtractor._find_hp_sku(utf16_strings + ascii_strings)
        if sku: result["SKU Number"] = sku
        return result

    @staticmethod
    def _extract_model_block(data: bytes) -> dict:
        result = {}
        utf16_strings = HPDMIExtractor._decode_utf16le_strings(data, min_len=5)
        model = HPDMIExtractor._find_hp_model(utf16_strings)
        if model: result["System Model"] = model
        return result

    @staticmethod
    def _extract_mac_block(data: bytes) -> dict:
        result = {}
        ff_end = 0
        for i in range(len(data) - 1):
            if data[i] == 0xFF and data[i+1] == 0xFF:
                ff_end = i + 2
        search_data = data[ff_end:ff_end + 64]
        mac = HPDMIExtractor._find_hp_mac(search_data)
        if mac: result["MAC Address"] = mac
        if not mac:
            mac = HPDMIExtractor._find_hp_mac(data)
            if mac: result["MAC Address"] = mac
        return result

    @staticmethod
    def _extract_build_id(content: bytes) -> dict:
        result = {}
        for name in [b'BuildId', b'GfxFactoryConfigFlags', b'Build ID']:
            pos = content.find(name)
            if pos != -1:
                chunk = content[pos:pos + 256]
                utf16_strings = HPDMIExtractor._decode_utf16le_strings(chunk, min_len=4)
                ascii_strings = HPDMIExtractor._decode_ascii_strings(chunk, min_len=4)
                for s in utf16_strings + ascii_strings:
                    cleaned = s.replace('.', '').replace(' ', '').upper()
                    if len(cleaned) >= 8 and re.match(r'^[A-Z0-9#]+$', cleaned):
                        result["Build ID"] = s
                        for enc in ['utf-16-le', 'ascii']:
                            try:
                                b = s.encode(enc)
                                r = chunk.find(b)
                                if r != -1:
                                    result["Build ID Offset"] = f"0x{pos + r:X}"
                                    result["Build ID EndOffset"] = f"0x{pos + r + len(b):X}"
                                    result["Build ID Length"] = len(b)
                                    result["Build ID Encoding"] = "UTF-16LE" if enc == 'utf-16-le' else "ASCII"
                                    break
                            except: pass
                        return result
        return result

    @classmethod
    def extract(cls, bios_path: str, log_cb=None) -> dict:
        results = {
            "Brand": "HP",
            "Details": {},
            "Offsets": {},
            "EndOffsets": {},
            "Lengths": {},
            "Encodings": {},
            "Source": {},
            "RawBlocks": {}
        }

        if not os.path.exists(bios_path):
            if log_cb: log_cb("[HP_DMI] File not found.")
            return results

        try:
            with open(bios_path, 'rb') as f:
                content = f.read()
        except Exception as e:
            if log_cb: log_cb(f"[HP_DMI] Failed to read file: {e}")
            return results

        if log_cb: log_cb("[HP_DMI] Starting GUID-based targeted extraction...")

        mud_guid = cls.HP_GUIDS["HP_MUD"]
        mud_blocks = cls._find_guid_blocks(content, mud_guid, window=512)
        if mud_blocks:
            if log_cb: log_cb(f"[HP_DMI] Found HP_MUD GUID at {len(mud_blocks)} location(s).")
            def _rank(b_item):
                p, blk = b_item
                ext = cls._extract_from_mud_block(blk)
                sc = 0
                if "Serial Number" in ext: sc += 100
                if "Product Number" in ext: sc += 50
                if "System Model" in ext: sc += 25
                return sc
            mud_blocks.sort(key=_rank, reverse=True)
            for (off, block) in mud_blocks:
                b_start = max(0, off - 64)
                extracted = cls._extract_from_mud_block(block)

                # Capture active raw EFI variable block for full-structure migration
                if ("Serial Number" in extracted or "System Model" in extracted) and "HP_MUD" not in results["RawBlocks"]:
                    hdr_start = off - 32
                    if hdr_start >= 0 and hdr_start + 32 <= len(content):
                        name_sz = int.from_bytes(content[hdr_start+24:hdr_start+28], 'little')
                        data_sz = int.from_bytes(content[hdr_start+28:hdr_start+32], 'little')
                        if 4 <= name_sz <= 64 and 10 <= data_sz <= 4096:
                            total_len = 32 + 16 + name_sz + data_sz
                            if hdr_start + total_len <= len(content):
                                raw_bytes = content[hdr_start : hdr_start + total_len]
                                results["RawBlocks"]["HP_MUD"] = {
                                    "start_offset": f"0x{hdr_start:X}",
                                    "guid_offset": f"0x{off:X}",
                                    "length": total_len,
                                    "hex": raw_bytes.hex(),
                                    "guid": "HP_MUD"
                                }

                for key, val in extracted.items():
                    if "Offset" in key or not val: continue
                    if key == "Alt Models":
                        # Record alt/board model locations
                        if isinstance(val, list):
                            for alt_m in val:
                                loc = cls._locate_field_in_block(block, b_start, alt_m)
                                if loc and "Board Model" not in results["Details"]:
                                    s, e, l, enc = loc
                                    results["Details"]["Board Model"] = alt_m
                                    results["Offsets"]["Board Model"] = f"0x{s:X}"
                                    results["EndOffsets"]["Board Model"] = f"0x{e:X}"
                                    results["Lengths"]["Board Model"] = l
                                    results["Encodings"]["Board Model"] = enc
                                    results["Source"]["Board Model"] = "HP_MUD"
                        continue

                    if key not in results["Details"]:
                        loc = cls._locate_field_in_block(block, b_start, val)
                        if loc:
                            s, e, l, enc = loc
                            results["Details"][key] = val
                            results["Offsets"][key] = f"0x{s:X}"
                            results["EndOffsets"][key] = f"0x{e:X}"
                            results["Lengths"][key] = l
                            results["Encodings"][key] = enc
                            results["Source"][key] = "HP_MUD"
        else:
            if log_cb: log_cb("[HP_DMI] HP_MUD GUID not found. Falling back...")

        csn_guid = cls.HP_GUIDS["HP_CSN"]
        csn_blocks = cls._find_guid_blocks(content, csn_guid, window=256)
        for (off, block) in csn_blocks:
            b_start = max(0, off - 64)
            extracted = cls._extract_csn_block(block)
            for key, val in extracted.items():
                if not val: continue
                loc = cls._locate_field_in_block(block, b_start, val)
                if "Serial Number" not in results["Details"]:
                    if loc:
                        s, e, l, enc = loc
                        results["Details"]["Serial Number"] = val
                        results["Offsets"]["Serial Number"] = f"0x{s:X}"
                        results["EndOffsets"]["Serial Number"] = f"0x{e:X}"
                        results["Lengths"]["Serial Number"] = l
                        results["Encodings"]["Serial Number"] = enc
                        results["Source"]["Serial Number"] = "HP_CSN"
                if key not in results["Details"] and loc:
                    s, e, l, enc = loc
                    results["Details"][key] = val
                    results["Offsets"][key] = f"0x{s:X}"
                    results["EndOffsets"][key] = f"0x{e:X}"
                    results["Lengths"][key] = l
                    results["Encodings"][key] = enc
                    results["Source"][key] = "HP_CSN"

        sku_guid = cls.HP_GUIDS["HP_SKU"]
        sku_blocks = cls._find_guid_blocks(content, sku_guid, window=256)
        for (off, block) in sku_blocks:
            b_start = max(0, off - 64)
            extracted = cls._extract_sku_block(block)
            for key, val in extracted.items():
                if not val or key in results["Details"]: continue
                loc = cls._locate_field_in_block(block, b_start, val)
                if loc:
                    results["Details"][key] = val
                    results["Offsets"][key] = f"0x{s:X}"
                    results["EndOffsets"][key] = f"0x{e:X}"
                    results["Lengths"][key] = l
                    results["Encodings"][key] = enc
                    results["Source"][key] = "HP_SKU"

        model_guid = cls.HP_GUIDS["HP_MODEL"]
        model_blocks = cls._find_guid_blocks(content, model_guid, window=256)
        for (off, block) in model_blocks:
            b_start = max(0, off - 64)
            extracted = cls._extract_model_block(block)
            for key, val in extracted.items():
                if not val: continue
                loc = cls._locate_field_in_block(block, b_start, val)
                if loc:
                    s, e, l, enc = loc
                    # Only replace if higher quality or not present
                    if key not in results["Details"] or cls._score_hp_model(val) > cls._score_hp_model(results["Details"].get(key, "")):
                        results["Details"][key] = val
                        results["Offsets"][key] = f"0x{s:X}"
                        results["EndOffsets"][key] = f"0x{e:X}"
                        results["Lengths"][key] = l
                        results["Encodings"][key] = enc
                        results["Source"][key] = "HP_MODEL"

        mac_guid = cls.HP_GUIDS["HP_MAC"]
        mac_blocks = cls._find_guid_blocks(content, mac_guid, window=128)
        for (off, block) in mac_blocks:
            b_start = max(0, off - 64)
            extracted = cls._extract_mac_block(block)
            for key, val in extracted.items():
                if not val or key in results["Details"]: continue
                results["Details"][key] = val
                results["Offsets"][key] = f"0x{off:X}"
                results["Source"][key] = "HP_MAC_ADDRESS"

        build = cls._extract_build_id(content)
        for key, val in build.items():
            if "Offset" not in key and "Length" not in key and "Encoding" not in key and key not in results["Details"]:
                results["Details"][key] = val
                if f"{key} Offset" in build: results["Offsets"][key] = build[f"{key} Offset"]
                if f"{key} EndOffset" in build: results["EndOffsets"][key] = build[f"{key} EndOffset"]
                if f"{key} Length" in build: results["Lengths"][key] = build[f"{key} Length"]
                if f"{key} Encoding" in build: results["Encodings"][key] = build[f"{key} Encoding"]
                results["Source"][key] = "BuildId_Var"

        # ── 7. MULTI-OCCURRENCE DISCOVERY (Scan whole binary for all locations) ─
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
                        idx = content.find(b_target, pos)
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

        # Scan instances for main fields
        if "System Model" in results["Details"]:
            _record_all_instances(
                "System Model",
                results["Details"]["System Model"],
                results["Offsets"].get("System Model", ""),
                "Model"
            )

        if "Board Model" in results["Details"]:
            _record_all_instances(
                "System Model",
                results["Details"]["Board Model"],
                results["Offsets"].get("Board Model", ""),
                "Board / Config Model"
            )

        if "Serial Number" in results["Details"]:
            _record_all_instances(
                "Serial Number",
                results["Details"]["Serial Number"],
                results["Offsets"].get("Serial Number", ""),
                "Serial"
            )

        # ── 8. Summary log ─────────────────────────────────────────────────────
        if log_cb:
            found = len(results["Details"])
            if found > 0:
                log_cb(f"[HP_DMI] Extraction complete. {found} field(s) found:")
                for k, v in results["Details"].items():
                    src = results["Source"].get(k, "?")
                    off = results["Offsets"].get(k, "?")
                    log_cb(f"  [{src}] {k}: {v}  (@ {off})")
                if results["AllOccurrences"]:
                    for fk, occurrences in results["AllOccurrences"].items():
                        if len(occurrences) > 1:
                            log_cb(f"  [MULTI-LOCATION] {fk} exists at {len(occurrences)} location(s) in firmware:")
                            for occ in occurrences:
                                log_cb(f"    - {occ['value']} @ {occ['offset']} ({occ['encoding']} | {occ['role']})")
            else:
                log_cb("[HP_DMI] No HP DMI fields could be extracted from this file.")

        return results


# ─── Backward-compatible wrapper for dmi_extractor.py ────────────────────────

def extract_hp_targeted(bios_path: str, log_cb=None) -> dict:
    """Drop-in replacement for DMIExtractor._extract_hp()."""
    return HPDMIExtractor.extract(bios_path, log_cb=log_cb)


if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python hp_dmi_extractor.py <bios_file.bin>")
        sys.exit(1)

    def log(msg): print(msg)

    info = HPDMIExtractor.extract(sys.argv[1], log_cb=log)
    print("\n─── RESULT ───────────────────────────────────────────────────")
    print(json.dumps(info, indent=4))
