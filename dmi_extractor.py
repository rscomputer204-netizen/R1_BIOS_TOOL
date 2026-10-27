import os
import re
import struct

try:
    from hp_dmi_extractor import HPDMIExtractor as _HPDMIExtractor
    _HP_TARGETED_AVAILABLE = True
except ImportError:
    _HP_TARGETED_AVAILABLE = False

try:
    from dell_dmi_extractor import DellDMIExtractor as _DellDMIExtractor
    _DELL_TARGETED_AVAILABLE = True
except ImportError:
    _DELL_TARGETED_AVAILABLE = False

try:
    from lenovo_dmi_extractor import LenovoDMIExtractor as _LenovoDMIExtractor
    _LENOVO_TARGETED_AVAILABLE = True
except ImportError:
    _LENOVO_TARGETED_AVAILABLE = False

try:
    from acer_dmi_extractor import AcerDMIExtractor as _AcerDMIExtractor
    _ACER_TARGETED_AVAILABLE = True
except ImportError:
    _ACER_TARGETED_AVAILABLE = False

try:
    from asus_dmi_extractor import AsusDMIExtractor as _AsusDMIExtractor
    _ASUS_TARGETED_AVAILABLE = True
except ImportError:
    _ASUS_TARGETED_AVAILABLE = False

class DMIExtractor:
    # Expert-guided labels
    BRAND_SIGNATURES = {
        "Dell": [b"Service Tag", b"Dell Inc.", b"OptiPlex", b"Latitude", b"Precision", b"Alienware", b"Vostro", b"XPS"],
        # HP GUID signature: 20AB3EB1-3C8F-4A4C-B87E-372426066D97 (HP_MUD) in LE binary
        "HP": [b"Feature Byte", b"Build Number", b"Hewlett-Packard", b"HP ", b"BID", b"EliteBook", b"ProBook", b"ZBook",
               b"\xB1\x3E\xAB\x20\x8F\x3C\x4C\x4A\xB8\x7E",   # HP_MUD GUID prefix
               b"\x77\x77\xDD\xC7\x65\xDE\x2F\x8A",            # HP_CSN GUID prefix
               b"\xF8\xB9\x02\x3F\x10\x98\x60\x45"],            # HP_MAC GUID prefix
        "Lenovo": [b"LENOVO", b"VPD", b"ThinkPad", b"LENV", b"IdeaPad"],
        "ASUS": [b"ASUSTeK", b"ASUS", b"ROG", b"TUF", b"ZenBook", b"Vivobook"],
        "Acer": [b"Acer", b"Aspire", b"TravelMate", b"Predator", b"Swift", b"Nitro", b"Packard Bell", b"Gateway", b"ConceptD", b"Extensa"],
        "MSI": [b"MSI", b"Micro-Star", b"Stealth", b"Raider", b"Katana"]
    }

    GENERIC_LABELS = [
        b"Serial Number", b"Product Name", b"Product Number", 
        b"System Serial Number", b"Service Tag", b"SKU Number",
        b"UUID", b"Board ID", b"Feature Byte", b"Build Number",
        b"System Model", b"Asset Tag", b"Enclosure Serial", b"BaseBoard Serial"
    ]

    @staticmethod
    def clean_string(data):
        if not data: return None
        try:
            # Try plain ASCII first
            decoded = data.decode('ascii', errors='ignore').split('\x00')[0].strip()
            # Basic validation: length > 3 and printable
            if len(decoded) > 3 and all(32 <= ord(c) <= 126 for c in decoded):
                # Clean common garbage
                cleaned = re.sub(r'[^a-zA-Z0-9\-\#\s]', '', decoded).strip()
                if len(cleaned) > 3:
                    return cleaned
        except:
            pass
        
        # Fallback to UTF-16LE
        try:
            decoded = data.decode('utf-16le', errors='ignore').split('\x00')[0].strip()
            if len(decoded) > 3 and all(32 <= ord(c) <= 126 for c in decoded):
                cleaned = re.sub(r'[^a-zA-Z0-9\-\#\s]', '', decoded).strip()
                if len(cleaned) > 3:
                    return cleaned
        except:
            pass
        return None

    @staticmethod
    def _parse_smbios_tables(content, results, brand=None):
        """
        Scans for _SM_ or _DMI_ anchors and attempts to parse Type 1 and Type 2 tables.
        This provides a universal, structure-aware extraction method.
        """
        smbios_anchor = b'_SM_'
        dmi_anchor = b'_DMI_'
        
        for anchor in [smbios_anchor, dmi_anchor]:
            for match in re.finditer(re.escape(anchor), content):
                start = match.start()
                chunk = content[start:min(len(content), start + 4096)]
                
                strings = re.split(rb'[\x00\xff]+', chunk)
                for s in strings:
                    decoded = DMIExtractor.clean_string(s)
                    if decoded and len(decoded) > 4:
                        if decoded.startswith('_SM_') or decoded.startswith('_DMI_'): continue
                        
                        # UUID Pattern (universal across all brands)
                        if re.match(r'^[A-F0-9]{32}$', decoded, re.IGNORECASE) or re.match(r'^[A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12}$', decoded, re.IGNORECASE):
                            if "UUID" not in results["Details"]:
                                results["Details"]["UUID"] = decoded
                                off = content.find(s, start)
                                if off != -1: results["Offsets"]["UUID"] = f"0x{off:X}"
                        
                        # Dell Service Tag Pattern (7 uppercase alphanumeric) - ONLY FOR DELL
                        elif (brand == "Dell" or brand is None) and re.match(r'^[A-Z0-9]{7}$', decoded) and decoded not in ["PQRSTUV", "1234567", "ABCDEFG"]:
                            if "Service Tag" not in results["Details"]:
                                results["Details"]["Service Tag"] = decoded
                                off = content.find(s, start)
                                if off != -1: results["Offsets"]["Service Tag"] = f"0x{off:X}"
                                
                        # Lenovo SN Pattern (Starts with 1S) - ONLY FOR LENOVO
                        elif (brand == "Lenovo" or brand is None) and re.match(r'^1S[A-Z0-9]{10,15}$', decoded):
                            if "Serial Number" not in results["Details"]:
                                results["Details"]["Serial Number"] = decoded
                                off = content.find(s, start)
                                if off != -1: results["Offsets"]["Serial Number"] = f"0x{off:X}"

                        # Acer SNID (11 or 12 digits) - ONLY FOR ACER
                        elif (brand == "Acer" or brand is None) and re.match(r'^[0-9]{11,12}$', decoded):
                            if "SNID" not in results["Details"]:
                                results["Details"]["SNID"] = decoded
                                off = content.find(s, start)
                                if off != -1: results["Offsets"]["SNID"] = f"0x{off:X}"

    @staticmethod
    def _parse_uefi_nvram(content, results, brand=None):
        """
        Scans for UEFI NVRAM stores (NVAR, VSS, Apple NVRAM).
        Extracts typical Apple, Dell, and HP variables directly from Hex structure.
        """
        signatures = [b'NVAR', b'$VSS', b'VSS$']
        for sig in signatures:
            for match in re.finditer(re.escape(sig), content):
                start = match.start()
                chunk = content[start:min(len(content), start + 1024)]
                
                strings = re.split(rb'[\x00\xff]+', chunk)
                for s in strings:
                    decoded = DMIExtractor.clean_string(s)
                    if decoded and len(decoded) >= 4:
                        # HP Feature Byte - STRICTLY ONLY FOR HP
                        if brand == "HP" and re.match(r'^[A-Za-z0-9\+\/]{10,}={0,2}$', decoded) and len(decoded) > 20:
                            if "Feature Byte" not in results["Details"]:
                                results["Details"]["Feature Byte"] = decoded
                                off = content.find(s, start)
                                if off != -1: results["Offsets"]["Feature Byte"] = f"0x{off:X}"
                        
                        # Dell Service Tag fallback inside NVRAM - STRICTLY ONLY FOR DELL
                        elif brand == "Dell" and _DellDMIExtractor.is_valid_service_tag(decoded):
                            if not re.match(r'^[A-F0-9]+$', decoded) and any(c.isdigit() for c in decoded):
                                if "Service Tag" not in results["Details"]:
                                    results["Details"]["Service Tag"] = decoded
                                    off = content.find(s, start)
                                    if off != -1: results["Offsets"]["Service Tag"] = f"0x{off:X}"

    @staticmethod
    def detect_brand(content, file_path=None):
        """
        Multi-signal brand detection with tiered scoring.
        Higher scores = stronger evidence. Ties broken by specificity.
        """
        brands_all = list(DMIExtractor.BRAND_SIGNATURES.keys())
        scores = {b: 0 for b in brands_all}

        # ── TIER 1: Definitive manufacturer strings (O(N) Boyer-Moore direct checks) ──────────────
        # ASUS Definitive Signatures
        if (b"ASUSTeK COMPUTER INC." in content or b"ASUSTeK" in content or b"ASUSTEK" in content
                or b"_ASUS_" in content or b"$ASUS$" in content or b"_ASUS_Notebook" in content
                or b"ASUS_BKLB_NB" in content or b"AsusSetup" in content or b"AsusSmbios" in content
                or b"$FID\x04\x78\x00" in content):
            scores["ASUS"] += 100
        elif b"ASUS" in content:
            scores["ASUS"] += 35

        # HP Definitive Signatures
        if (b"Hewlett-Packard" in content or b"HP Inc." in content
                or b"HP_MUD" in content or b"Hewlett Packard" in content):
            scores["HP"] += 100
        hp_mud_guid = bytes.fromhex("B13EAB208F3C4C4AB87E372426066D97")
        if hp_mud_guid in content:
            scores["HP"] += 100
        if b"HP System Board" in content or b"HP BIOS" in content:
            scores["HP"] += 60

        # Dell Definitive Signatures
        if (b"Dell Inc." in content or b"Dell Computer" in content or b"Dell System" in content
                or b"Dell Computer Corporation" in content or b"www.dell.com" in content
                or b"Alienware" in content or b"DELL INC" in content or b"DELL SYSTEM" in content
                or b"DELL COMPUTER" in content or b"DVAR\xff\x0f" in content
                or b"DELL BIO" in content or b"Dell Configuration" in content
                or b"DellSystemIdConfigPei" in content or b"DellVariableService" in content):
            scores["Dell"] += 100
        elif b"Dell" in content or b"DELL" in content:
            scores["Dell"] += 40

        # Lenovo Definitive Signatures
        if b"LENOVO" in content or b"Lenovo Group" in content:
            scores["Lenovo"] += 100
        elif b"ThinkPad" in content or b"IdeaPad" in content:
            scores["Lenovo"] += 60
        elif b"Lenovo" in content:
            scores["Lenovo"] += 40

        # Acer Definitive Signatures
        if (b"Acer Inc." in content or b"Acer Incorporated" in content or b"Acer Corp" in content
                or b"ACER INC" in content or b"ACER CORP" in content):
            scores["Acer"] += 100
        elif b"Acer" in content or b"ACER" in content:
            scores["Acer"] += 50

        # MSI Definitive Signatures
        if b"Micro-Star International" in content or b"MSI Notebook" in content:
            scores["MSI"] += 100

        # Apple Definitive Signatures
        if b"Apple Inc." in content or b"Apple ROM" in content:
            scores["Apple"] += 100

        # ── Fast Short-Circuit Check 1 ──────────────────────────────────────
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_brand, top_score = sorted_scores[0]
        second_brand, second_score = sorted_scores[1]

        if top_score >= 100 and second_score < 60:
            return top_brand
        if top_score >= 50 and (top_score - second_score >= 25):
            return top_brand

        # ── Fast File Path Hint (prior to running heavy regexes) ─────────────
        if file_path:
            fp_lower = str(file_path).lower()
            path_scores = {}
            for kw in ["dell", "latitude", "inspiron", "optiplex", "vostro", "precision", "alienware", "xps"]:
                if kw in fp_lower: path_scores["Dell"] = 60; break
            for kw in ["asus", "zenbook", "vivobook", "rog", "tuf"]:
                if kw in fp_lower: path_scores["ASUS"] = 60; break
            for kw in ["hp", "hewlett", "elitebook", "probook", "zbook", "pavilion", "omen"]:
                if kw in fp_lower: path_scores["HP"] = 60; break
            for kw in ["lenovo", "thinkpad", "ideapad", "thinkcentre", "thinkbook", "legion", "yoga"]:
                if kw in fp_lower: path_scores["Lenovo"] = 60; break
            for kw in ["acer", "aspire", "predator", "travelmate", "nitro", "swift", "extensa"]:
                if kw in fp_lower: path_scores["Acer"] = 60; break

            if path_scores:
                for b, s in path_scores.items():
                    scores[b] += s
                sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
                top_brand, top_score = sorted_scores[0]
                second_brand, second_score = sorted_scores[1]
                if top_score >= 60 and (top_score - second_score >= 20):
                    return top_brand

        # ── TIER 2: Specific serial / model prefixes ───────────────────────────
        # Dell PPID (Motherboard Serial: CN0...)
        if re.search(rb'\bCN0[A-Z0-9]{20,23}\b', content):
            scores["Dell"] += 50

        # Dell Service Tag with validation
        st_matches = re.findall(rb'Service\s*Tag\s*[:=\s]*([A-Z0-9]{7})\b', content, re.IGNORECASE)
        for tag in st_matches:
            if _DellDMIExtractor.is_valid_service_tag(tag.decode(errors='ignore')):
                scores["Dell"] += 50
                break

        # Acer 22-char serial prefix
        if re.search(rb'\b(?:NX|NH|UN|DT|NC|MR|MF|LU|LX|ZL|PO|MM|SK|SV|BL|PF)[A-Z0-9]{20}\b', content):
            scores["Acer"] += 40

        # ASUS 15-char serial regex (e.g. H5N0CV14544621A, FAN0CV11708141H, etc.)
        if re.search(rb'\b[A-Z0-9]{2}[NMK]0[A-Z0-9]{2}[0-9]{6}[0-9A-Z]{2,3}\b', content):
            scores["ASUS"] += 35

        # ASUS ROM ID pattern (e.g. X555LAB.503, X441UA.306, E203MA.008, UX410UQK.301)
        if re.search(rb'\b[A-Z]{1,2}[0-9]{3}[A-Z]{0,4}\.[0-9]{3}\b', content):
            scores["ASUS"] += 25

        # ── TIER 3: Model family signatures (weight: 15 per match) ────────────
        model_sigs = {
            "Acer":   [b"Aspire", b"TravelMate", b"Predator", b"Swift", b"Nitro",
                       b"Extensa", b"ConceptD", b"Packard Bell", b"Gateway", b"Enduro",
                       b"Spin"],
            "Dell":   [b"OptiPlex", b"Latitude", b"Precision", b"Alienware", b"Vostro", b"Inspiron", b"XPS"],
            "HP":     [b"EliteBook", b"ProBook", b"ZBook", b"OMEN by HP", b"Pavilion"],
            "Lenovo": [b"ThinkPad", b"IdeaPad", b"ThinkCentre", b"ThinkBook", b"Legion", b"Yoga"],
            "ASUS":   [b"ZenBook", b"Zenbook", b"Vivobook", b"VivoBook", b"TUF Gaming", b"ROG Strix",
                       b"Zephyrus", b"ROG ", b"ExpertBook", b"ProArt", b"StudioBook"],
            "MSI":    [b"Stealth ", b"Raider ", b"Katana "],
        }
        for brand_key, sigs in model_sigs.items():
            for sig in sigs:
                if sig in content:
                    scores[brand_key] += 15
                else:
                    sig_u16 = sig.decode('ascii', errors='ignore').encode('utf-16le')
                    if sig_u16 in content:
                        scores[brand_key] += 15

        # ── TIER 4: HP GUID bytes (weight: 20) ────────────────────────────────
        hp_guid_bytes = [
            b"\xB1\x3E\xAB\x20\x8F\x3C\x4C\x4A\xB8\x7E",  # HP_MUD
            b"\x77\x77\xDD\xC7\x65\xDE\x2F\x8A",            # HP_CSN
        ]
        for gb in hp_guid_bytes:
            if gb in content:
                scores["HP"] += 20
                break

        # ── TIER 5: Generic Dell Service Tag regex (weight: 25) ───────────────
        if re.search(rb'Service\s+Tag\s*[:\s]+[A-Z0-9]{7}\b', content, re.IGNORECASE):
            scores["Dell"] += 25

        # ── TIER 6: HP BID pattern — only if not already confirmed ASUS/Dell ───
        if scores["ASUS"] < 50 and scores["Dell"] < 50:
            if re.search(rb'(?<![A-Za-z])BID\s*[:=]\s*[0-9A-Z]{4,6}(?![A-Za-z])', content):
                scores["HP"] += 25
            elif scores["HP"] > 0 and re.search(rb'(?<![A-Za-z])BID[A-Z0-9]{4,6}(?![A-Za-z])', content):
                scores["HP"] += 20

        # ── TIER 7: Lenovo VPD block (weight: 20) ─────────────────────────────
        if b"$VPD$" in content or b"VPD DATA" in content:
            scores["Lenovo"] += 20

        # ── TIER 8: File path / name fallback for partial dumps ────────────────
        if file_path and max(scores.values()) == 0:
            fp_lower = str(file_path).lower()
            for kw in ["dell", "latitude", "inspiron", "optiplex", "vostro", "precision", "alienware"]:
                if kw in fp_lower:
                    scores["Dell"] += 40
                    break
            for kw in ["asus", "zenbook", "vivobook", "rog"]:
                if kw in fp_lower:
                    scores["ASUS"] += 40
                    break
            for kw in ["hp", "hewlett", "elitebook", "probook", "pavilion", "omen"]:
                if kw in fp_lower:
                    scores["HP"] += 40
                    break
            for kw in ["acer", "aspire", "predator", "travelmate", "nitro"]:
                if kw in fp_lower:
                    scores["Acer"] += 40
                    break
            for kw in ["lenovo", "thinkpad", "ideapad", "thinkcentre"]:
                if kw in fp_lower:
                    scores["Lenovo"] += 40
                    break

        # ── Pick winner ────────────────────────────────────────────────────────
        best_brand = max(scores, key=scores.get)
        if scores[best_brand] > 0:
            return best_brand
        return "Unknown"

    @staticmethod
    def detect_platform(content: bytes, regions: dict = None) -> str:
        """
        Determines firmware CPU / Chipset Platform: 'Intel' or 'AMD'.
        """
        # 1. Intel Detection Signals
        if b"\x5A\xA5\xF0\x0F" in content[:0x1000]:
            return "Intel"
        if b"$FPT" in content or b"$CPD" in content or b"ME_REGION" in content or b"CSME" in content:
            return "Intel"
        if b"GenuineIntel" in content:
            return "Intel"
        if b"$BPM" in content or b"$KM" in content:
            return "Intel"

        # 2. AMD Detection Signals
        if b"$PSP" in content or b"$BHD" in content or b"$APCB" in content or b"$BLD" in content:
            return "AMD"
        if b"AMD AGESA" in content or b"AuthenticAMD" in content or b"ComboAM4" in content or b"ComboV2" in content:
            return "AMD"

        # Default fallback: check regions
        if regions:
            for r_k in regions:
                r_l = str(r_k).lower()
                if "me" in r_l or "csme" in r_l or "gbe" in r_l:
                    return "Intel"

        return "N/A"

    @staticmethod
    def extract_mac_address(content: bytes, regions: dict = None, brand: str = None) -> list:
        """
        Locates hardware LAN MAC address across GbE region, EFI variables, and brand NVRAM structures.
        Returns list of dicts: [{'mac': str, 'offset': str, 'location': str, 'type': 'primary'|'secondary', 'encoding': 'HEX'|'ASCII'}]
        """
        results = []
        seen_offsets = set()

        def is_valid_mac(b: bytes) -> bool:
            if len(b) != 6: return False
            if b in (b'\x00'*6, b'\xff'*6): return False
            if b[0] & 1 != 0: return False  # Multicast bit must be 0 (unicast only)
            if b[:3] in (b'\x00\x00\x00', b'\xff\xff\xff'): return False
            if b[-3:] in (b'\x00\x00\x00', b'\xff\xff\xff'): return False
            if len(set(b)) <= 2: return False
            return True

        # 1. GbE Region Check (Primary for Intel platforms across ALL brands)
        gbe_off = None
        if regions:
            for r_k, r_v in regions.items():
                if str(r_k).lower() in ("gbe", "gbe_region"):
                    gbe_off = r_v.get("offset")
                    break

        if gbe_off is None:
            # Check Intel Flash Descriptor Region 3 (GbE)
            fd_idx = content.find(b"\x5A\xA5\xF0\x0F")
            if fd_idx != -1 and fd_idx >= 0x10:
                try:
                    desc_base = fd_idx - 0x10
                    flmap0 = struct.unpack_from("<I", content, desc_base + 0x14)[0]
                    frba = desc_base + (((flmap0 >> 16) & 0xFF) << 4)
                    if frba + 16 <= len(content):
                        reg_val = struct.unpack_from("<I", content, frba + 12)[0]
                        base_raw = reg_val & 0x7FFF
                        limit_raw = (reg_val >> 16) & 0x7FFF
                        if limit_raw >= base_raw and limit_raw > 0:
                            gbe_off = base_raw << 12
                except Exception:
                    pass

        if gbe_off is None:
            # Heuristic standard GbE offsets
            for cand in [0x1000, 0x2000, 0x3000]:
                if cand + 6 <= len(content) and is_valid_mac(content[cand:cand+6]):
                    gbe_off = cand
                    break

        if gbe_off is not None and gbe_off + 6 <= len(content):
            cand = content[gbe_off : gbe_off + 6]
            if is_valid_mac(cand):
                mac_str = ':'.join(f"{b:02X}" for b in cand)
                results.append({
                    "mac": mac_str,
                    "offset": f"0x{gbe_off:X}",
                    "location": "GbE",
                    "type": "primary",
                    "encoding": "HEX"
                })
                seen_offsets.add(gbe_off)

        # 2. HP Specific: EmbeddedLanConfig & HP_MAC GUID
        hp_elan = b"E\x00m\x00b\x00e\x00d\x00d\x00e\x00d\x00L\x00a\x00n\x00C\x00o\x00n\x00f\x00i\x00g"
        idx = 0
        while True:
            idx = content.find(hp_elan, idx)
            if idx == -1: break
            w_start = idx + len(hp_elan)
            window = content[w_start : w_start + 64]
            w_i = 0
            while w_i < len(window) and window[w_i] == 0:
                w_i += 1
            if w_i + 6 <= len(window):
                c_b = window[w_i : w_i + 6]
                if is_valid_mac(c_b):
                    actual_off = w_start + w_i
                    if actual_off not in seen_offsets:
                        mac_str = ':'.join(f"{b:02X}" for b in c_b)
                        m_type = "primary" if not results else "secondary"
                        results.append({
                            "mac": mac_str,
                            "offset": f"0x{actual_off:X}",
                            "location": "BIOS",
                            "type": m_type,
                            "encoding": "HEX"
                        })
                        seen_offsets.add(actual_off)
            idx += len(hp_elan)

        # 3. Dell Specific: LOM MAC in DVAR
        for lom_sig in [b"LOM_MAC", b"PassthroughMAC", b"LOM MAC"]:
            l_idx = 0
            while True:
                l_idx = content.find(lom_sig, l_idx)
                if l_idx == -1: break
                w_start = l_idx + len(lom_sig)
                window = content[w_start : w_start + 32]
                w_i = 0
                while w_i < len(window) and window[w_i] in (0x00, 0x20, 0x3A, 0x3D): # null, space, colon, equals
                    w_i += 1
                if w_i + 6 <= len(window):
                    c_b = window[w_i : w_i + 6]
                    if is_valid_mac(c_b):
                        actual_off = w_start + w_i
                        if actual_off not in seen_offsets:
                            mac_str = ':'.join(f"{b:02X}" for b in c_b)
                            m_type = "primary" if not results else "secondary"
                            results.append({
                                "mac": mac_str,
                                "offset": f"0x{actual_off:X}",
                                "location": "BIOS",
                                "type": m_type,
                                "encoding": "HEX"
                            })
                            seen_offsets.add(actual_off)
                l_idx += len(lom_sig)

        # 4. Text-Formatted MAC Address Scanner (ASCII & UTF-16LE)
        mac_regex = re.compile(rb'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})')
        for match in mac_regex.finditer(content):
            matched_bytes = match.group(0)
            m_str = matched_bytes.decode('ascii', errors='ignore').replace('-', ':').upper()
            if m_str not in ("00:00:00:00:00:00", "FF:FF:FF:FF:FF:FF"):
                m_off = match.start()
                if m_off not in seen_offsets:
                    m_type = "primary" if not results else "secondary"
                    results.append({
                        "mac": m_str,
                        "offset": f"0x{m_off:X}",
                        "location": "BIOS",
                        "type": m_type,
                        "encoding": "ASCII"
                    })
                    seen_offsets.add(m_off)

        return results

    @staticmethod
    def _extract_hp(content, results, bios_path=None, log_cb=None):
        """
        HP DMI extraction — Uses the new targeted GUID-based HPDMIExtractor.
        Falls back to legacy regex approach if GUID-based extraction finds nothing.
        """
        # ── PRIORITY: GUID-based targeted extraction ───────────────────────────
        if _HP_TARGETED_AVAILABLE and bios_path:
            if log_cb: log_cb("[HP] Using GUID-based targeted extractor (hp_dmi_extractor)...")
            hp_result = _HPDMIExtractor.extract(bios_path, log_cb=log_cb)
            details = hp_result.get("Details", {})
            offsets = hp_result.get("Offsets", {})
            end_offsets = hp_result.get("EndOffsets", {})
            lengths = hp_result.get("Lengths", {})
            encodings = hp_result.get("Encodings", {})
            if details:
                for key, val in details.items():
                    if val and key not in results["Details"]:
                        results["Details"][key] = val
                        if key in offsets:
                            results["Offsets"][key] = offsets[key]
                        if key in end_offsets:
                            results["EndOffsets"][key] = end_offsets[key]
                        if key in lengths:
                            results["Lengths"][key] = lengths[key]
                        if key in encodings:
                            results["Encodings"][key] = encodings[key]
                # Map CSN to Serial Number if needed
                if "Serial Number (CSN)" in results["Details"] and "Serial Number" not in results["Details"]:
                    results["Details"]["Serial Number"] = results["Details"]["Serial Number (CSN)"]
                    results["Offsets"]["Serial Number"] = results["Offsets"].get("Serial Number (CSN)", "")
                    results["EndOffsets"]["Serial Number"] = results["EndOffsets"].get("Serial Number (CSN)", "")
                    results["Lengths"]["Serial Number"] = results["Lengths"].get("Serial Number (CSN)", 0)
                if "RawBlocks" in hp_result:
                    results["RawBlocks"] = hp_result["RawBlocks"]
                if "AllOccurrences" in hp_result:
                    if "AllOccurrences" not in results: results["AllOccurrences"] = {}
                    results["AllOccurrences"].update(hp_result["AllOccurrences"])
                if log_cb: log_cb(f"[HP] GUID-based extraction complete: {len(details)} field(s) found.")
                return  # Success — no need for legacy fallback
            else:
                if log_cb: log_cb("[HP] GUID extraction found nothing. Falling back to legacy scan...")

        # ── LEGACY FALLBACK: regex / prefix scan ───────────────────────────────
        hp_prefixes = [
            b'5CD', b'5CG', b'CND', b'CNU', b'SGH', b'8CG', 
            b'CZC', b'JP', b'JPH', b'BRG', b'CNF', b'6CM', b'INI', b'TW'
        ]
        
        # Extract Serial Number
        for pref in hp_prefixes:
            # ASCII search
            match = re.search(re.escape(pref) + rb'[A-Z0-9]{7,10}', content)
            if match:
                results["Details"]["Serial Number"] = match.group(0).decode('ascii')
                results["Offsets"]["Serial Number"] = f"0x{match.start():X}"
                break
            # UTF-16 search
            u16_pref = pref.decode('ascii').encode('utf-16le')
            match = re.search(re.escape(u16_pref) + rb'(?:[A-Z0-9\x00]{14,20})', content)
            if match:
                decoded = match.group(0).decode('utf-16le', errors='ignore').split('\x00')[0].strip()
                if len(decoded) >= 10:
                    results["Details"]["Serial Number"] = decoded
                    results["Offsets"]["Serial Number"] = f"0x{match.start():X}"
                    break

        # HP Metadata
        patterns = {
            "Board ID": rb'BID\s*([A-Z0-9]{4,6})',
            "Feature Byte": rb'Feature Byte:?\s*([A-Za-z0-9\+\/]{10,})',
            "Product Number": rb'([A-Z0-9]{7}#[A-Z0-9]{3})'
        }
        for key, pattern in patterns.items():
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                results["Details"][key] = match.group(1).decode('ascii', errors='ignore').strip()
                results["Offsets"][key] = f"0x{match.start():X}"
                
        # HP System Model
        model_match = re.search(rb'(HP\s+(?:EliteBook|ProBook|ZBook|Spectre|Envy|Pavilion|Omen|Victus|Dragonfly|Folio)[^\x00\r\n]+)', content, re.IGNORECASE)
        if model_match:
            model_name = re.sub(r'[^a-zA-Z0-9\-\s]', '', model_match.group(1).decode('ascii', errors='ignore')).strip()
            results["Details"]["System Model"] = model_name
            results["Offsets"]["System Model"] = f"0x{model_match.start():X}"

    @staticmethod
    def _extract_dell(content, results, bios_path=None, log_cb=None):
        """
        Dell DMI extraction — Uses the dedicated DellDMIExtractor for DVAR,
        PPID, MAC, Service Tag, and Windows OEM License Key.
        """
        if _DELL_TARGETED_AVAILABLE and bios_path:
            if log_cb: log_cb("[Dell] Using dedicated Dell targeted extractor (dell_dmi_extractor)...")
            dell_res = _DellDMIExtractor.extract(bios_path, log_cb=log_cb)
            details = dell_res.get("Details", {})
            offsets = dell_res.get("Offsets", {})
            end_offsets = dell_res.get("EndOffsets", {})
            lengths = dell_res.get("Lengths", {})
            encodings = dell_res.get("Encodings", {})
            if details:
                for k, v in details.items():
                    if v and k not in results["Details"]:
                        results["Details"][k] = v
                        if k in offsets: results["Offsets"][k] = offsets[k]
                        if k in end_offsets: results["EndOffsets"][k] = end_offsets[k]
                        if k in lengths: results["Lengths"][k] = lengths[k]
                        if k in encodings: results["Encodings"][k] = encodings[k]
                if "RawBlocks" in dell_res:
                    results["RawBlocks"].update(dell_res["RawBlocks"])
                if "AllOccurrences" in dell_res:
                    if "AllOccurrences" not in results: results["AllOccurrences"] = {}
                    results["AllOccurrences"].update(dell_res["AllOccurrences"])
                if log_cb: log_cb(f"[Dell] Extraction complete: {len(details)} field(s) found.")
                return

        # ── LEGACY FALLBACK with enhanced blacklist ──────────────────────────
        candidates = []
        BLACKLISTED_TAGS = {
            "0123456", "1234567", "2345678", "3456789", "4567890",
            "0000000", "1111111", "9999999", "ABCDEFG", "PQRSTUV",
            "QQRSTUV", "XYZ1234", "ASDFGHJ", "AABBCDD", "BBBBBBB",
            "FFFFFFF", "NNNNNNN", "UNKNOWN", "DEFAULT", "AFTPASS",
            "PCBAPASS", "RUNNING", "NVDIAG", "WTDM", "DisableGPU", "TearDown"
        }

        def _is_valid_tag(t):
            if not t or len(t) != 7 or t in BLACKLISTED_TAGS: return False
            if not re.match(r'^[A-Z0-9]{7}$', t): return False
            # Sequential check
            if all(ord(t[i+1]) == ord(t[i]) + 1 for i in range(len(t)-1)): return False
            if len(set(t)) <= 2: return False
            return True
        
        # 0. Dell DMI Slash Pattern /<TAG>/ (Standard Dell DMI Table syntax)
        for match in re.finditer(rb'/([A-Z0-9]{7})/', content):
            tag = match.group(1).decode('ascii', errors='ignore')
            if _is_valid_tag(tag):
                candidates.append((tag, match.start(1), 180))

        # 1. Search ASCII with direct label match
        for match in re.finditer(rb'Service Tag[:\s]*([A-Z0-9]{7})\b', content, re.IGNORECASE):
            tag = match.group(1).decode('ascii', errors='ignore')
            if _is_valid_tag(tag):
                candidates.append((tag, match.start(), 150))

        # 2. Search UTF-16 with proximity search
        labels = [b'S\x00e\x00r\x00v\x00i\x00c\x00e\x00T\x00a\x00g\x00', b'ServiceTag']
        for label in labels:
            for l_match in re.finditer(re.escape(label), content):
                start = max(0, l_match.start() - 512)
                end = min(len(content), l_match.end() + 512)
                nearby_data = content[start:end]
                for t_match in re.finditer(rb'(?:[A-Z0-9]\x00){7}', nearby_data):
                    tag = t_match.group(0).decode('utf-16le', errors='ignore')
                    if _is_valid_tag(tag):
                        abs_off = start + t_match.start()
                        candidates.append((tag, abs_off, 120))

        # 3. SMBIOS Type 1 String Pool proximity near Dell manufacturer headers
        for smb_hdr in [b'Dell Inc.', b'Dell Computer Corporation', b'Dell System']:
            pos = 0
            while True:
                p = content.find(smb_hdr, pos)
                if p == -1: break
                w_start = max(0, p - 2048)
                w_end = min(len(content), p + 2048)
                window = content[w_start:w_end]
                for m in re.finditer(rb'\x00([A-Z0-9]{7})\x00', window):
                    tag = m.group(1).decode('ascii', errors='ignore')
                    if _is_valid_tag(tag):
                        candidates.append((tag, w_start + m.start(1), 130))
                pos = p + 1

        if candidates:
            tag_scores = {}
            tag_offsets = {}
            for tag, off, score in [(c[0], c[1], c[2]) for c in candidates]:
                tag_scores[tag] = tag_scores.get(tag, 0) + score
                if tag not in tag_offsets: tag_offsets[tag] = off
            
            best_tag = max(tag_scores, key=tag_scores.get)
            results["Details"]["Service Tag"] = best_tag
            results["Offsets"]["Service Tag"] = f"0x{tag_offsets[best_tag]:X}"
            
        # Dell Model
        model_match = re.search(rb'(Latitude|OptiPlex|Precision|XPS|Vostro|Alienware|G3|G5|G7)\s*([0-9]{4})', content, re.IGNORECASE)
        if model_match:
            results["Details"]["System Model"] = f"{model_match.group(1).decode('ascii')} {model_match.group(2).decode('ascii')}"
            results["Offsets"]["System Model"] = f"0x{model_match.start():X}"

    @staticmethod
    def _extract_lenovo(content, results, bios_path=None, log_cb=None):
        """
        Lenovo DMI extraction — Uses the dedicated LenovoDMIExtractor for VPD blocks,
        MTM / Product Number, ThinkPad/IdeaPad models, Serial Numbers, and Windows OEM Keys.
        """
        if _LENOVO_TARGETED_AVAILABLE and bios_path:
            if log_cb: log_cb("[Lenovo] Using dedicated Lenovo targeted extractor (lenovo_dmi_extractor)...")
            lenovo_res = _LenovoDMIExtractor.extract(bios_path, log_cb=log_cb)
            details = lenovo_res.get("Details", {})
            offsets = lenovo_res.get("Offsets", {})
            end_offsets = lenovo_res.get("EndOffsets", {})
            lengths = lenovo_res.get("Lengths", {})
            encodings = lenovo_res.get("Encodings", {})
            if details:
                for k, v in details.items():
                    if v and k not in results["Details"]:
                        results["Details"][k] = v
                        if k in offsets: results["Offsets"][k] = offsets[k]
                        if k in end_offsets: results["EndOffsets"][k] = end_offsets[k]
                        if k in lengths: results["Lengths"][k] = lengths[k]
                        if k in encodings: results["Encodings"][k] = encodings[k]
                if "RawBlocks" in lenovo_res:
                    results["RawBlocks"].update(lenovo_res["RawBlocks"])
                if "AllOccurrences" in lenovo_res:
                    if "AllOccurrences" not in results: results["AllOccurrences"] = {}
                    results["AllOccurrences"].update(lenovo_res["AllOccurrences"])
                if log_cb: log_cb(f"[Lenovo] Extraction complete: {len(details)} field(s) found.")
                return

        # Legacy fallback
        sn_match = re.search(rb'1S[A-Z0-9]{10,}', content)
        if sn_match:
            results["Details"]["Serial Number"] = sn_match.group().decode('ascii')
            results["Offsets"]["Serial Number"] = f"0x{sn_match.start():X}"
        
        uuid_match = re.search(rb'[A-F0-9]{32}', content)
        if uuid_match:
            results["Details"]["UUID"] = uuid_match.group().decode('ascii')
            results["Offsets"]["UUID"] = f"0x{uuid_match.start():X}"

    @staticmethod
    def _extract_acer(content, results, bios_path=None, log_cb=None):
        """
        Acer DMI extraction — Uses dedicated AcerDMIExtractor for InsydeH2O $BVD$
        and DMI stores, 22-char serial numbers, SNID, models, board serials, and Windows OEM key.
        """
        if _ACER_TARGETED_AVAILABLE and bios_path:
            if log_cb: log_cb("[Acer] Using dedicated Acer targeted extractor (acer_dmi_extractor)...")
            acer_res = _AcerDMIExtractor.extract(bios_path, log_cb=log_cb)
            details = acer_res.get("Details", {})
            offsets = acer_res.get("Offsets", {})
            end_offsets = acer_res.get("EndOffsets", {})
            lengths = acer_res.get("Lengths", {})
            encodings = acer_res.get("Encodings", {})
            if details:
                for k, v in details.items():
                    if v and k not in results["Details"]:
                        results["Details"][k] = v
                        if k in offsets: results["Offsets"][k] = offsets[k]
                        if k in end_offsets: results["EndOffsets"][k] = end_offsets[k]
                        if k in lengths: results["Lengths"][k] = lengths[k]
                        if k in encodings: results["Encodings"][k] = encodings[k]
                if "RawBlocks" in acer_res:
                    results["RawBlocks"].update(acer_res["RawBlocks"])
                if "AllOccurrences" in acer_res:
                    if "AllOccurrences" not in results: results["AllOccurrences"] = {}
                    results["AllOccurrences"].update(acer_res["AllOccurrences"])
                if log_cb: log_cb(f"[Acer] Extraction complete: {len(details)} field(s) found.")
                return

        # Legacy fallback
        snid_match = re.search(rb'SNID[:\s]*([0-9]{11,12})\b', content)
        if snid_match:
            results["Details"]["SNID"] = snid_match.group(1).decode('ascii')
            results["Offsets"]["SNID"] = f"0x{snid_match.start():X}"

    @staticmethod
    def _extract_asus(content, results, bios_path=None, log_cb=None):
        """
        ASUS DMI extraction — Uses the dedicated AsusDMIExtractor for EFI variable blocks
        ($ASUS$, ASUS OEM GUID, AsusSmbios), model detection (ROG/TUF/ZenBook/VivoBook),
        serial numbers, UUID, board serial, Windows OEM Key, and Product Number.
        """
        if _ASUS_TARGETED_AVAILABLE and bios_path:
            if log_cb: log_cb("[ASUS] Using dedicated ASUS targeted extractor (asus_dmi_extractor)...")
            asus_res = _AsusDMIExtractor.extract(bios_path, log_cb=log_cb)
            details = asus_res.get("Details", {})
            offsets = asus_res.get("Offsets", {})
            end_offsets = asus_res.get("EndOffsets", {})
            lengths = asus_res.get("Lengths", {})
            encodings = asus_res.get("Encodings", {})
            if details:
                for k, v in details.items():
                    if v and k not in results["Details"]:
                        results["Details"][k] = v
                        if k in offsets: results["Offsets"][k] = offsets[k]
                        if k in end_offsets: results["EndOffsets"][k] = end_offsets[k]
                        if k in lengths: results["Lengths"][k] = lengths[k]
                        if k in encodings: results["Encodings"][k] = encodings[k]
                if "RawBlocks" in asus_res:
                    results["RawBlocks"].update(asus_res["RawBlocks"])
                if "AllOccurrences" in asus_res:
                    if "AllOccurrences" not in results: results["AllOccurrences"] = {}
                    results["AllOccurrences"].update(asus_res["AllOccurrences"])
                if log_cb: log_cb(f"[ASUS] Extraction complete: {len(details)} field(s) found.")
                return

        # Legacy fallback: simple proximity search near ASUSTeK string
        sn_match = re.search(rb'ASUSTeK.*?\b([A-Z0-9]{12,15})\b', content, re.DOTALL | re.IGNORECASE)
        if sn_match:
            results["Details"]["Serial Number"] = sn_match.group(1).decode('ascii')
            results["Offsets"]["Serial Number"] = f"0x{sn_match.start():X}"

    @staticmethod
    def _extract_asus_msi_legacy(content, results):
        """Legacy MSI/ASUS fallback scanner for when no dedicated extractor is available."""
        sn_match = re.search(rb'(?:MSI|Micro-Star).*?\b([A-Z0-9]{10,15})\b', content, re.DOTALL | re.IGNORECASE)
        if sn_match:
            results["Details"]["Serial Number"] = sn_match.group(1).decode('ascii')
            results["Offsets"]["Serial Number"] = f"0x{sn_match.start():X}"

    @staticmethod
    def _extract_generic(content, results):
        # Search for all generic labels
        for label in DMIExtractor.GENERIC_LABELS:
            label_str = label.decode()
            if label_str in results["Details"]: continue

            # Multi-encoding search
            for enc in ['ascii', 'utf-16le']:
                try:
                    pattern = label if enc == 'ascii' else label.decode().encode('utf-16le')
                    
                    # Performance Optimization: Use .find() before regex
                    curr_off = 0
                    while True:
                        off = content.find(pattern, curr_off)
                        if off == -1: break
                        
                        # Look ahead for value
                        search_area = content[off + len(pattern): off + len(pattern) + 128]
                        
                        # Split by common null/garbage delimiters
                        parts = re.split(rb'[\x00\xff\x01-\x1f\x2c\x3b]', search_area)
                        for p in parts:
                            cleaned = DMIExtractor.clean_string(p)
                            if cleaned and len(cleaned) > 4:
                                # Strict validation to prevent garbage UUIDs like 'hwinvcmpSysD'
                                if label_str == "UUID":
                                    if not re.match(r'^[A-F0-9]{32}$', cleaned, re.IGNORECASE) and not re.match(r'^[A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12}$', cleaned, re.IGNORECASE):
                                        continue
                                
                                # Avoid matching the label itself or generic "None/N/A"
                                if cleaned.lower() not in label_str.lower() and cleaned.lower() not in ["none", "n/a", "unknown"]:
                                    results["Details"][label_str] = cleaned
                                    results["Offsets"][label_str] = f"0x{off:X}"
                                    break
                        if label_str in results["Details"]: break
                        curr_off = off + 1
                        if curr_off >= len(content): break
                except:
                    continue
                
                # Performance: Yield CPU to keep UI responsive
                import time
                time.sleep(0.001)

    @staticmethod
    def extract_info(bios_path, regions=None, log_cb=None):
        results = {
            "Brand": "Unknown",
            "Details": {},
            "Offsets": {},
            "EndOffsets": {},
            "Lengths": {},
            "Encodings": {},
            "Regions": {},
            "RelativeOffsets": {},
            "RawBlocks": {},
            "AllOccurrences": {}
        }
        if not os.path.exists(bios_path): return results

        try:
            import time
            with open(bios_path, 'rb') as f:
                content = f.read()

            if log_cb: log_cb("[INFO] Analyzing Brand...")
            brand = DMIExtractor.detect_brand(content, file_path=bios_path)
            results["Brand"] = brand
            
            time.sleep(0.01) # UI Breathe

            # Brand-specific extraction
            if log_cb: log_cb(f"[INFO] Scanning {brand} specific patterns...")
            if brand == "HP":
                DMIExtractor._extract_hp(content, results, bios_path=bios_path, log_cb=log_cb)
            elif brand == "Dell":
                DMIExtractor._extract_dell(content, results, bios_path=bios_path, log_cb=log_cb)
            elif brand == "Lenovo":
                DMIExtractor._extract_lenovo(content, results, bios_path=bios_path, log_cb=log_cb)
            elif brand == "Acer":
                DMIExtractor._extract_acer(content, results, bios_path=bios_path, log_cb=log_cb)
            elif brand == "ASUS":
                DMIExtractor._extract_asus(content, results, bios_path=bios_path, log_cb=log_cb)
            elif brand == "MSI":
                DMIExtractor._extract_asus_msi_legacy(content, results)
            
            time.sleep(0.01) # UI Breathe

            # Run Advanced Structured Parsing (SMBIOS & NVRAM)
            if log_cb: log_cb("[INFO] Parsing SMBIOS tables and UEFI NVRAM structures...")
            DMIExtractor._parse_smbios_tables(content, results, brand=brand)
            DMIExtractor._parse_uefi_nvram(content, results, brand=brand)

            # Run generic extraction for gaps
            if log_cb: log_cb("[INFO] Performing deep scan for DMI labels...")
            
            # Optimization: Only scan for labels we don't have yet
            for i, label in enumerate(DMIExtractor.GENERIC_LABELS):
                label_str = label.decode()
                if label_str not in results["Details"]:
                    pass
            
            DMIExtractor._extract_generic(content, results)

            # Post-processing: Clean up cross-brand false positives
            if brand == "ASUS":
                results["Details"].pop("Feature Byte", None)
                results["Details"].pop("Service Tag", None)
                results["Details"].pop("SNID", None)
                results["Offsets"].pop("Feature Byte", None)
                results["Offsets"].pop("Service Tag", None)
                results["Offsets"].pop("SNID", None)

            # Post-processing: Normalize Serial Number
            sn_keys = ["Serial Number", "System Serial Number"]
            if brand == "Dell":
                sn_keys.append("Service Tag")
            elif brand == "Acer":
                sn_keys.append("SNID")

            for k in sn_keys:
                if k in results["Details"] and "Serial Number" not in results["Details"]:
                    results["Details"]["Serial Number"] = results["Details"][k]
                    results["Offsets"]["Serial Number"] = results["Offsets"].get(k, "")
                    if k in results["EndOffsets"]: results["EndOffsets"]["Serial Number"] = results["EndOffsets"][k]
                    if k in results["Lengths"]: results["Lengths"]["Serial Number"] = results["Lengths"][k]
                    if k in results["Encodings"]: results["Encodings"]["Serial Number"] = results["Encodings"][k]
                    break

            # ── Platform Detection (Intel / AMD) ──────────────────────────────────
            plat_val = DMIExtractor.detect_platform(content, regions=regions)
            if plat_val and plat_val != "N/A":
                results["Details"]["Platform"] = plat_val
                results["Offsets"]["Platform"] = "0x0"
                results["Regions"]["Platform"] = "SYSTEM"

            # ── Universal Hardware MAC Address Discovery ─────────────────────────
            mac_entries = DMIExtractor.extract_mac_address(content, regions=regions, brand=brand)
            if mac_entries:
                primary_mac = mac_entries[0]
                results["Details"]["MAC Address"] = primary_mac["mac"]
                results["Offsets"]["MAC Address"] = primary_mac["offset"]
                results["Regions"]["MAC Address"] = primary_mac.get("location", "GbE")
                results["Encodings"]["MAC Address"] = primary_mac.get("encoding", "HEX")

                if "AllOccurrences" not in results:
                    results["AllOccurrences"] = {}
                if "MAC Address" not in results["AllOccurrences"]:
                    results["AllOccurrences"]["MAC Address"] = []
                for me in mac_entries:
                    results["AllOccurrences"]["MAC Address"].append({
                        "value": me["mac"],
                        "offset": me["offset"],
                        "location": me.get("location", "GbE"),
                        "type": me.get("type", "primary"),
                        "encoding": me.get("encoding", "HEX")
                    })

            # Universal occurrence builder: ensure AllOccurrences is filled for all core fields
            if "AllOccurrences" not in results:
                results["AllOccurrences"] = {}

            for field_name in ["System Model", "Serial Number", "UUID", "Product Number", "Board Model"]:
                val = results["Details"].get(field_name)
                if val and isinstance(val, str) and len(val.strip()) >= 4:
                    if field_name not in results["AllOccurrences"]:
                        results["AllOccurrences"][field_name] = []
                    
                    seen_offs = set()
                    for o in results["AllOccurrences"][field_name]:
                        try:
                            seen_offs.add(int(str(o.get("offset", "0")), 16) if str(o.get("offset", "")).startswith("0x") else int(o.get("offset", 0)))
                        except: pass

                    p_off_str = results["Offsets"].get(field_name, "")
                    p_off = int(p_off_str, 16) if p_off_str and p_off_str.startswith("0x") else None
                    
                    val_clean = val.strip()
                    for enc in ['utf-16-le', 'ascii']:
                        try:
                            b_target = val_clean.encode(enc)
                            enc_label = "UTF-16LE" if enc == 'utf-16-le' else "ASCII"
                            pos = 0
                            while True:
                                idx = content.find(b_target, pos)
                                if idx == -1: break
                                if idx not in seen_offs:
                                    seen_offs.add(idx)
                                    is_primary = (p_off is not None and idx == p_off)
                                    role = f"Primary {field_name}" if is_primary else f"Secondary {field_name} (Mirror)"
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

            # Identify Regions and Relative Offsets for each Offset and AllOccurrences
            if regions:
                for key, off_str in results["Offsets"].items():
                    try:
                        off = int(off_str, 16)
                        found_region = "Unknown"
                        rel_off_str = ""
                        for r_name, r_info in regions.items():
                            if r_info['offset'] <= off < r_info['offset'] + r_info['size']:
                                found_region = r_name.upper()
                                rel_off_str = f"0x{off - r_info['offset']:X}"
                                break
                        results["Regions"][key] = found_region
                        results["RelativeOffsets"][key] = rel_off_str
                    except:
                        results["Regions"][key] = "Error"
                        results["RelativeOffsets"][key] = ""
                    time.sleep(0.001)

                if "AllOccurrences" in results:
                    for fk, occs in results["AllOccurrences"].items():
                        for occ in occs:
                            try:
                                off_int = int(str(occ["offset"]), 16) if str(occ["offset"]).startswith("0x") else int(occ["offset"])
                                found_r = "BIOS"
                                rel_o = ""
                                for r_name, r_info in regions.items():
                                    if r_info['offset'] <= off_int < r_info['offset'] + r_info['size']:
                                        found_r = r_name.upper()
                                        rel_o = f"0x{off_int - r_info['offset']:X}"
                                        break
                                occ["region"] = found_r
                                occ["location"] = found_r
                                occ["relative_offset"] = rel_o
                            except:
                                pass

                if "RawBlocks" in results:
                    for b_name, b_info in results["RawBlocks"].items():
                        try:
                            off = int(b_info["start_offset"], 16)
                            for r_name, r_info in regions.items():
                                if r_info['offset'] <= off < r_info['offset'] + r_info['size']:
                                    b_info["region"] = r_name.upper()
                                    b_info["relative_offset"] = f"0x{off - r_info['offset']:X}"
                                    break
                        except:
                            pass
            else:
                # Heuristic region assignment when regions map is not available
                for key, off_str in results["Offsets"].items():
                    if key not in results["Regions"] or results["Regions"][key] in ("Unknown", "UNKNOWN", ""):
                        try:
                            off = int(off_str, 16) if str(off_str).startswith("0x") else int(off_str)
                            if off < 0x10000:
                                results["Regions"][key] = "DESCRIPTOR"
                            elif off < 0x800000 and len(content) >= 0x1000000:
                                results["Regions"][key] = "ME"
                            else:
                                results["Regions"][key] = "BIOS"
                        except:
                            results["Regions"][key] = "BIOS"

                if "AllOccurrences" in results:
                    for fk, occs in results["AllOccurrences"].items():
                        for occ in occs:
                            try:
                                off_int = int(str(occ["offset"]), 16) if str(occ["offset"]).startswith("0x") else int(occ["offset"])
                                if off_int < 0x10000:
                                    loc_g = "DESCRIPTOR"
                                elif off_int < 0x800000 and len(content) >= 0x1000000:
                                    loc_g = "ME"
                                else:
                                    loc_g = "BIOS"
                                occ["region"] = loc_g
                                occ["location"] = loc_g
                            except:
                                occ["region"] = "BIOS"
                                occ["location"] = "BIOS"

            # Ensure type field is cleanly populated for all occurrences
            if "AllOccurrences" in results:
                for fk, occs in results["AllOccurrences"].items():
                    for occ in occs:
                        if "type" not in occ or not occ["type"]:
                            is_p = occ.get("is_primary", False)
                            role_s = str(occ.get("role", "")).lower()
                            if is_p:
                                occ["type"] = "primary"
                            elif "board" in role_s or "config" in role_s:
                                occ["type"] = "board"
                            else:
                                occ["type"] = "secondary"

        except Exception as e:
            if log_cb: log_cb(f"[ERROR] DMI Extraction failed: {str(e)}")
            print(f"[ERROR] DMI Extraction failed: {str(e)}")

        return results

if __name__ == "__main__":
    import sys
    import json
    if len(sys.argv) > 1:
        info = DMIExtractor.extract_info(sys.argv[1])
        print(json.dumps(info, indent=4))
