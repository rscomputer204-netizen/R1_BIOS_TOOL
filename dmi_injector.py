"""
dmi_injector.py  -  R1 BIOS Tool
Smart Selective DMI/SMBIOS Injection Engine.

Features:
  - Smart Differential Pre-Check: Checks target BIOS before writing.
    * If field/block is already present and intact -> PRESERVES it untouched!
    * If field/block is missing, blank (0x00/0xFF), or default placeholder -> INJECTS it!
  - Supports three progressively aggressive injection strategies:
    1. PROFILE OFFSET  -- use the exact byte offset saved in the .dmi profile
    2. STRING SEARCH   -- find the original slot/placeholder in the target binary
    3. SMBIOS ANCHOR   -- locate the SMBIOS structure and write into string slots
                          (works on factory-clean / FF-wiped BIOS images)
"""

import re

# SMBIOS field name -> (table_type, byte_offset_of_string_index_in_struct)
FIELD_TO_SMBIOS = {
    "System Manufacturer": (1, 0x04),
    "Manufacturer":        (1, 0x04),
    "System Model":        (1, 0x05),
    "Product Name":        (1, 0x05),
    "Model":               (1, 0x05),
    "System Version":      (1, 0x06),
    "Serial Number":       (1, 0x07),
    "System Serial Number":(1, 0x07),
    "Service Tag":         (1, 0x07),
    "SKU Number":          (1, 0x19),
    "SNID":                (1, 0x19),
    "Family":              (1, 0x1A),
    "Board Manufacturer":  (2, 0x04),
    "Board Product":       (2, 0x05),
    "Board Version":       (2, 0x06),
    "Board Serial":        (2, 0x07),
    "PPID":                (2, 0x07),
    "Board Asset Tag":     (2, 0x08),
    "Asset Tag":           (3, 0x08),
}

# Generic dummy / placeholder strings used by OEMs or factory unconfigured boards
PLACEHOLDER_STRINGS = {
    "default string", "to be filled by o.e.m.", "to be filled by oem",
    "none", "system serial number", "system product name", "system version",
    "product name", "all series", "chassis serial number", "base board serial number",
    "0123456789", "1234567890", "invalid", "n/a", "not applicable", "unknown",
    "00000000-0000-0000-0000-000000000000", "ffffffff-ffff-ffff-ffff-ffffffffffff",
    "00:00:00:00:00:00", "ff:ff:ff:ff:ff:ff"
}


class DMIInjector:

    @staticmethod
    def _is_slot_blank_or_dummy(data: bytearray, off: int, length: int = 16) -> bool:
        """
        Checks if a target byte region is unprogrammed (all 0xFF),
        zero-filled (all 0x00), or contains a generic OEM placeholder string.
        """
        if off < 0 or off >= len(data):
            return False
        chk_len = max(length, 16)
        chunk = data[off : min(len(data), off + chk_len)]
        if not chunk:
            return False

        # All 0x00 or all 0xFF
        if all(b == 0x00 for b in chunk) or all(b == 0xFF for b in chunk):
            return True

        # High density of 0x00 or 0xFF (>= 85%)
        null_or_ff = sum(1 for b in chunk if b in (0x00, 0xFF))
        if (null_or_ff / len(chunk)) >= 0.85:
            return True

        # Check for known OEM placeholder strings
        for enc in ("utf-16le", "latin1", "utf-8"):
            try:
                txt = chunk.decode(enc, errors="ignore").split("\x00")[0].strip().lower()
                if txt in PLACEHOLDER_STRINGS:
                    return True
            except Exception:
                pass

        return False

    @staticmethod
    def check_field_presence(data: bytearray, field_name: str, val_str: str,
                             target_off: int = None, explicit_enc: str = None,
                             end_off: int = None) -> tuple:
        """
        Smart Pre-Injection Differential Check:
        Examines if the field value is already present and intact in the target BIOS.

        Returns:
            (status: str, msg: str, found_off: int)
            status can be:
              - 'ALREADY_PRESENT_OFFSET': Value is already at target_off.
              - 'ALREADY_PRESENT_GLOBAL': Value is found elsewhere in target firmware.
              - 'TARGET_BLANK': Target slot is blank (0x00/0xFF) or dummy placeholder.
              - 'TARGET_DIFFERENT': Target has a different value (needs injection/restore).
              - 'NOT_FOUND': Value is not present in target.
        """
        if not val_str or str(val_str).strip() in ("", "N/A", "None", "Unknown"):
            return ("INVALID_VALUE", "Value is empty or unknown", None)

        val_str = str(val_str).strip()
        is_hex = bool(explicit_enc and explicit_enc.upper() in ("HEX", "BYTE", "RAW"))

        ascii_b = val_str.encode("latin1", errors="replace")
        utf16_b = val_str.encode("utf-16le")
        hex_b = None

        if is_hex or field_name == "MAC Address":
            try:
                clean_hex = re.sub(r'[^0-9a-fA-F]', '', val_str)
                if len(clean_hex) % 2 == 0 and len(clean_hex) >= 4:
                    hex_b = bytes.fromhex(clean_hex)
            except Exception:
                pass
        elif field_name == "UUID" or re.match(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$', val_str):
            try:
                clean_hex = re.sub(r'[^0-9a-fA-F]', '', val_str)
                if len(clean_hex) == 32:
                    hex_b = bytes.fromhex(clean_hex)
            except Exception:
                pass

        # 1. Check exact expected target_off first
        if target_off is not None and 0 <= target_off < len(data):
            # Check ASCII
            v_len = len(ascii_b)
            if target_off + v_len <= len(data) and data[target_off : target_off + v_len] == ascii_b:
                return ("ALREADY_PRESENT_OFFSET", f"Matched ASCII at 0x{target_off:X}", target_off)

            # Check UTF-16LE
            u_len = len(utf16_b)
            if target_off + u_len <= len(data) and data[target_off : target_off + u_len] == utf16_b:
                return ("ALREADY_PRESENT_OFFSET", f"Matched UTF-16LE at 0x{target_off:X}", target_off)

            # Check HEX
            if hex_b and target_off + len(hex_b) <= len(data) and data[target_off : target_off + len(hex_b)] == hex_b:
                return ("ALREADY_PRESENT_OFFSET", f"Matched HEX at 0x{target_off:X}", target_off)

            # Check if target slot is blank / placeholder
            slot_len = max(v_len, (end_off - target_off) if end_off and end_off > target_off else 16)
            if DMIInjector._is_slot_blank_or_dummy(data, target_off, slot_len):
                # Slot is blank, but verify if value exists elsewhere globally
                p_asc = data.find(ascii_b) if len(ascii_b) >= 4 else -1
                if p_asc != -1:
                    return ("ALREADY_PRESENT_GLOBAL", f"Value already exists at 0x{p_asc:X}", p_asc)
                p_utf = data.find(utf16_b) if len(utf16_b) >= 8 else -1
                if p_utf != -1:
                    return ("ALREADY_PRESENT_GLOBAL", f"Value already exists at 0x{p_utf:X}", p_utf)
                if hex_b and len(hex_b) >= 6:
                    p_hex = data.find(hex_b)
                    if p_hex != -1:
                        return ("ALREADY_PRESENT_GLOBAL", f"Value already exists at 0x{p_hex:X}", p_hex)
                return ("TARGET_BLANK", f"Target slot at 0x{target_off:X} is blank/erased", target_off)
            else:
                # Target slot has different data
                p_asc = data.find(ascii_b) if len(ascii_b) >= 4 else -1
                if p_asc != -1:
                    return ("ALREADY_PRESENT_GLOBAL", f"Value already exists at 0x{p_asc:X}", p_asc)
                p_utf = data.find(utf16_b) if len(utf16_b) >= 8 else -1
                if p_utf != -1:
                    return ("ALREADY_PRESENT_GLOBAL", f"Value already exists at 0x{p_utf:X}", p_utf)
                return ("TARGET_DIFFERENT", f"Target has different data at 0x{target_off:X}", target_off)

        # 2. If target_off is None, check globally
        p_asc = data.find(ascii_b) if len(ascii_b) >= 4 else -1
        if p_asc != -1:
            return ("ALREADY_PRESENT_GLOBAL", f"Value already exists at 0x{p_asc:X}", p_asc)
        p_utf = data.find(utf16_b) if len(utf16_b) >= 8 else -1
        if p_utf != -1:
            return ("ALREADY_PRESENT_GLOBAL", f"Value already exists at 0x{p_utf:X}", p_utf)
        if hex_b and len(hex_b) >= 6:
            p_hex = data.find(hex_b)
            if p_hex != -1:
                return ("ALREADY_PRESENT_GLOBAL", f"Value already exists at 0x{p_hex:X}", p_hex)

        return ("NOT_FOUND", "Value not found in target binary", None)

    @staticmethod
    def inject_fields(data: bytearray, fields: dict, regions_map: dict = None,
                      raw_blocks: dict = None, all_occurrences: dict = None,
                      log_cb=None) -> int:
        """
        Smart Selective DMI Injection:
        - Evaluates each field against target BIOS before writing.
        - Preserves already-present, intact DMI data (skips overwriting).
        - Injects only genuinely missing, blank, or different fields.
        """
        def _log(m):
            if log_cb:
                log_cb(m)

        _log("<font color='#00f3ff'><b>[SMART DMI INJECTION]</b> Pre-checking target BIOS data...</font>")
        _log("  - Only missing or blank fields will be injected; existing intact DMI will be preserved.")

        preserved_count = 0
        injected_count = 0
        skipped_count = 0
        block_preserved = 0
        block_injected = 0
        written_offsets = set()

        # ─── STRATEGY 0: RAW EFI VARIABLE BLOCKS (e.g. HP_MUD, DELL_DVAR, LENOVO_VPD) ───
        if raw_blocks:
            for b_name, b_info in raw_blocks.items():
                hex_data = b_info.get("hex", "")
                if not hex_data:
                    continue
                block_bytes = bytes.fromhex(hex_data)

                target_b_off = None
                rel_str = b_info.get("relative_offset", "")
                reg_name = b_info.get("region", "")

                if rel_str and reg_name and regions_map:
                    for r_n, r_i in regions_map.items():
                        if r_n.upper() == reg_name.upper():
                            try:
                                rel_int = int(rel_str, 16) if str(rel_str).lower().startswith("0x") else int(rel_str)
                                target_b_off = r_i['offset'] + rel_int
                                break
                            except Exception:
                                pass

                if target_b_off is None:
                    off_s = b_info.get("start_offset", "")
                    if off_s and str(off_s).strip() not in ("N/A", "None", ""):
                        try:
                            target_b_off = int(off_s, 16) if str(off_s).lower().startswith("0x") else int(off_s)
                        except Exception:
                            pass

                # Dell DVAR auto-alignment
                if b_name == "DELL_DVAR":
                    t_dvar = data.find(b"DVAR")
                    if t_dvar != -1 and (t_dvar % 0x1000 == 0 or data[t_dvar:t_dvar+8].startswith(b"DVAR\xff\x0f")):
                        if 0 <= t_dvar + len(block_bytes) <= len(data):
                            target_b_off = t_dvar

                # Lenovo VPD auto-alignment
                if b_name == "LENOVO_VPD":
                    t_vpd = data.find(b"\xaa\x55VPD\x00")
                    if t_vpd == -1:
                        t_vpd = data.find(b"VPD\x00")
                    if t_vpd != -1 and 0 <= t_vpd + len(block_bytes) <= len(data):
                        target_b_off = t_vpd

                # Acer BVD auto-alignment
                if b_name == "ACER_BVD":
                    t_bvd = data.find(b"$BVD$")
                    if t_bvd != -1 and 0 <= t_bvd + len(block_bytes) <= len(data):
                        target_b_off = t_bvd

                # Acer DMI variable store auto-alignment
                if b_name == "ACER_DMI":
                    for s in [b"CustomDmiVar", b"DmiVar", b'\x2F\x83\x90\x2F\x0B\x65\x13\x48\x8E\x5A\xA6\x1F\x03\x35\x80\x04']:
                        t_dmi = data.find(s)
                        if t_dmi != -1:
                            start_align = max(0, (t_dmi // 0x100) * 0x100)
                            if 0 <= start_align + len(block_bytes) <= len(data):
                                target_b_off = start_align
                                break

                # ASUS EFI variable block auto-alignment
                if b_name == "ASUS_OEM_DATA":
                    asus_guid = b'\x4A\x10\x59\x7B\x0D\xC0\x58\x41\x87\xFF\xF0\x4D\x63\x96\xA9\x15'
                    t_g = data.find(asus_guid)
                    if t_g != -1:
                        start_align = max(0, (t_g // 0x100) * 0x100)
                        if 0 <= start_align + len(block_bytes) <= len(data):
                            target_b_off = start_align

                if b_name == "ASUS_SMBIOS_VAR":
                    asus_sg = b'\x58\x64\xBD\xC2\x3B\x4B\x00\x49\x87\x7A\xD4\x6A\x4D\xBE\xAA\xCC'
                    t_sg = data.find(asus_sg)
                    if t_sg != -1:
                        start_align = max(0, (t_sg // 0x100) * 0x100)
                        if 0 <= start_align + len(block_bytes) <= len(data):
                            target_b_off = start_align

                if b_name == "ASUS_TAG":
                    t_tag = data.find(b"$ASUS$")
                    if t_tag != -1 and 0 <= t_tag + len(block_bytes) <= len(data):
                        target_b_off = t_tag

                if target_b_off is not None and 0 <= target_b_off + len(block_bytes) <= len(data):
                    hx = f"<a href='hexjump:///0x{target_b_off:X}' style='color:#00f3ff;text-decoration:underline;'>0x{target_b_off:X}</a>"
                    target_chunk = data[target_b_off : target_b_off + len(block_bytes)]

                    # SMART CHECK: If target already has the exact identical block
                    if target_chunk == block_bytes:
                        _log(f"  - <font color='#00ff41'><b>[BLOCK PRESERVED]</b></font> {b_name} structure ({len(block_bytes)}B) already 100% identical @ {hx} (Untouched)")
                        block_preserved += 1
                        continue

                    # SMART CHECK: If target block is NOT wiped and already populated
                    is_wiped = all(b in (0x00, 0xFF) for b in target_chunk)
                    null_or_ff_count = sum(1 for b in target_chunk if b in (0x00, 0xFF))
                    if not is_wiped and (null_or_ff_count / len(target_chunk)) < 0.70:
                        # Target already has active EFI data in this block!
                        # Check if any key field value (like Serial Number) from fields is already inside target block
                        field_found_in_target = False
                        for fn, fv in fields.items():
                            val_check = str(fv.get("value", "")).strip()
                            if len(val_check) >= 6:
                                if val_check.encode("utf-16le") in target_chunk or val_check.encode("latin1") in target_chunk:
                                    field_found_in_target = True
                                    break
                        if field_found_in_target:
                            _log(f"  - <font color='#00ff41'><b>[BLOCK PRESERVED]</b></font> {b_name} is already valid and populated in target @ {hx} (Untouched)")
                            block_preserved += 1
                            continue

                    # Target block is wiped or missing -> Restore it!
                    data[target_b_off : target_b_off + len(block_bytes)] = block_bytes
                    _log(f"  - <font color='#ffd600'><b>[BLOCK RESTORED]</b></font> {b_name} structure ({len(block_bytes)}B) restored @ {hx}")
                    block_injected += 1

        # ─── STRATEGY 1, 2, 3: INDIVIDUAL DMI FIELDS ───
        for field_name, finfo in fields.items():
            val = finfo.get("value")
            if not val or str(val).strip() in ("", "N/A", "None", "Unknown"):
                continue
            val_str = str(val).strip()

            off_str = finfo.get("offset", "")
            end_str = finfo.get("end_offset", "")
            rel_str = finfo.get("relative_offset", "")
            reg_name = finfo.get("region", "")
            explicit_enc = finfo.get("encoding", None)

            # Resolve expected target offset
            target_off = None
            target_end = None

            if rel_str and reg_name and regions_map:
                for r_n, r_i in regions_map.items():
                    if r_n.upper() == reg_name.upper():
                        try:
                            rel_int = int(rel_str, 16) if str(rel_str).lower().startswith("0x") else int(rel_str)
                            target_off = r_i['offset'] + rel_int
                            if end_str and off_str:
                                s_orig = int(off_str, 16) if str(off_str).lower().startswith("0x") else int(off_str)
                                e_orig = int(end_str, 16) if str(end_str).lower().startswith("0x") else int(end_str)
                                target_end = target_off + (e_orig - s_orig)
                            break
                        except Exception:
                            pass

            if target_off is None and off_str and str(off_str).strip() not in ("N/A", "UNKNOWN", "None", ""):
                try:
                    s = str(off_str).strip()
                    target_off = int(s, 16) if s.lower().startswith("0x") else int(s)
                    if end_str and str(end_str).strip() not in ("N/A", "UNKNOWN", "None", ""):
                        es = str(end_str).strip()
                        target_end = int(es, 16) if es.lower().startswith("0x") else int(es)
                except Exception:
                    pass

            # ─── SMART DIFFERENTIAL PRE-CHECK ───
            status, detail_msg, found_off = DMIInjector.check_field_presence(
                data, field_name, val_str, target_off=target_off,
                explicit_enc=explicit_enc, end_off=target_end
            )

            # If field is already present in target BIOS -> PRESERVE IT UNTOUCHED!
            if status in ("ALREADY_PRESENT_OFFSET", "ALREADY_PRESENT_GLOBAL"):
                hx = f"<a href='hexjump:///0x{found_off:X}' style='color:#00ff41;text-decoration:underline;'>0x{found_off:X}</a>"
                _log(
                    f"  - <font color='#00ff41'><b>[EXISTS - PRESERVED]</b></font> "
                    f"{field_name} = '{val_str}' already intact @ {hx} (Untouched)"
                )
                preserved_count += 1
                if found_off is not None:
                    written_offsets.add(found_off)
                continue

            # Field is MISSING or TARGET IS BLANK/DIFFERENT -> Selectively inject it!
            ok = False

            # Strategy 1: Profile offset (with region-relative recalculation)
            if target_off is not None:
                lbl = f"profile relative({reg_name})" if rel_str and regions_map else "profile offset"
                ok = DMIInjector._write_at(
                    data, target_off, val_str, field_name,
                    end_off=target_end, explicit_enc=explicit_enc,
                    label=lbl, log_cb=log_cb
                )
                if ok:
                    written_offsets.add(target_off)

            # Strategy 2: search binary for slot / placeholder / MSDM / PPID
            if not ok:
                ok = DMIInjector._search_and_write(data, val_str, field_name, log_cb)

            # Strategy 3: SMBIOS anchor
            if not ok:
                ok = DMIInjector._smbios_inject(data, field_name, val_str, log_cb)

            if ok:
                injected_count += 1
            else:
                _log(
                    f"  - <font color='#ff4444'><b>[SKIPPED]</b></font> "
                    f"{field_name} = '{val_str}': could not locate slot in target binary."
                )
                skipped_count += 1

            # ─── Synchronize secondary / mirror occurrences ───
            if all_occurrences and field_name in all_occurrences:
                for occ in all_occurrences[field_name]:
                    occ_off_str = occ.get("offset", "")
                    occ_type = occ.get("type", "secondary")
                    occ_val = occ.get("value", val_str)
                    occ_enc = occ.get("encoding", None)
                    occ_reg = occ.get("location", "")
                    occ_rel = occ.get("relative_offset", "")

                    write_val = occ_val if occ_type == "board" else val_str
                    if not write_val or str(write_val).strip() in ("", "N/A", "None", "Unknown"):
                        continue

                    target_occ_off = None
                    if occ_rel and occ_reg and regions_map:
                        for r_n, r_i in regions_map.items():
                            if r_n.upper() == occ_reg.upper():
                                try:
                                    r_int = int(occ_rel, 16) if str(occ_rel).lower().startswith("0x") else int(occ_rel)
                                    target_occ_off = r_i['offset'] + r_int
                                    break
                                except Exception:
                                    pass

                    if target_occ_off is None and occ_off_str and str(occ_off_str).strip() not in ("N/A", "UNKNOWN", "None", ""):
                        try:
                            s = str(occ_off_str).strip()
                            target_occ_off = int(s, 16) if s.lower().startswith("0x") else int(s)
                        except Exception:
                            pass

                    if target_occ_off is not None and target_occ_off not in written_offsets:
                        lbl_occ = f"mirror occurrence ({occ_reg})" if occ_type != "board" else f"board SKU ({occ_reg})"
                        # Pre-check mirror slot
                        m_status, _, m_found = DMIInjector.check_field_presence(
                            data, f"{field_name} ({occ_type})", write_val,
                            target_off=target_occ_off, explicit_enc=occ_enc
                        )
                        if m_status in ("ALREADY_PRESENT_OFFSET", "ALREADY_PRESENT_GLOBAL"):
                            preserved_count += 1
                            written_offsets.add(target_occ_off)
                            continue

                        occ_ok = DMIInjector._write_at(
                            data, target_occ_off, write_val, f"{field_name} ({occ_type})",
                            explicit_enc=occ_enc, label=lbl_occ, log_cb=log_cb
                        )
                        if occ_ok:
                            written_offsets.add(target_occ_off)
                            injected_count += 1

        # ─── Synchronize extra fields in all_occurrences ───
        if all_occurrences:
            for extra_key, occ_list in all_occurrences.items():
                if extra_key in fields:
                    continue
                for occ in occ_list:
                    occ_off_str = occ.get("offset", "")
                    occ_type = occ.get("type", "secondary")
                    occ_val = occ.get("value", "")
                    occ_enc = occ.get("encoding", None)
                    occ_reg = occ.get("location", "")
                    occ_rel = occ.get("relative_offset", "")

                    if not occ_val or str(occ_val).strip() in ("", "N/A", "None", "Unknown"):
                        continue

                    target_occ_off = None
                    if occ_rel and occ_reg and regions_map:
                        for r_n, r_i in regions_map.items():
                            if r_n.upper() == occ_reg.upper():
                                try:
                                    r_int = int(occ_rel, 16) if str(occ_rel).lower().startswith("0x") else int(occ_rel)
                                    target_occ_off = r_i['offset'] + r_int
                                    break
                                except Exception:
                                    pass

                    if target_occ_off is None and occ_off_str and str(occ_off_str).strip() not in ("N/A", "UNKNOWN", "None", ""):
                        try:
                            s = str(occ_off_str).strip()
                            target_occ_off = int(s, 16) if s.lower().startswith("0x") else int(s)
                        except Exception:
                            pass

                    if target_occ_off is not None and target_occ_off not in written_offsets:
                        lbl_occ = f"extra DMI ({occ_reg})"
                        m_status, _, _ = DMIInjector.check_field_presence(
                            data, extra_key, occ_val,
                            target_off=target_occ_off, explicit_enc=occ_enc
                        )
                        if m_status in ("ALREADY_PRESENT_OFFSET", "ALREADY_PRESENT_GLOBAL"):
                            preserved_count += 1
                            written_offsets.add(target_occ_off)
                            continue

                        occ_ok = DMIInjector._write_at(
                            data, target_occ_off, occ_val, extra_key,
                            explicit_enc=occ_enc, label=lbl_occ, log_cb=log_cb
                        )
                        if occ_ok:
                            written_offsets.add(target_occ_off)
                            injected_count += 1

        # ─── SUMMARY REPORT ───
        _log("<font color='#00c8ff'><b>" + "━" * 52 + "</b></font>")
        _log("<b>📊 SMART DMI INJECTION REPORT</b>")
        _log(f"  • Already Present (Preserved): <font color='#00ff41'><b>{preserved_count} field(s)</b></font> (Untouched)")
        _log(f"  • Missing / Blank (Injected):   <font color='#ffd600'><b>{injected_count} field(s)</b></font> (Injected)")
        if block_preserved or block_injected:
            _log(f"  • Raw Blocks Preserved:         <font color='#00ff41'><b>{block_preserved} block(s)</b></font>")
            _log(f"  • Raw Blocks Restored:          <font color='#ffd600'><b>{block_injected} block(s)</b></font>")
        if skipped_count:
            _log(f"  • Skipped / Unlocated:          <font color='#ff4444'><b>{skipped_count} field(s)</b></font>")
        _log("<font color='#00c8ff'><b>" + "━" * 52 + "</b></font>")

        return injected_count

    @staticmethod
    def _write_at(data, off, val_str, field_name, end_off=None, explicit_enc=None, label="offset", log_cb=None):
        def _log(m):
            if log_cb:
                log_cb(m)
        if off < 0 or off >= len(data):
            return False

        is_hex = bool(explicit_enc and explicit_enc.upper() in ("HEX", "BYTE", "RAW"))
        use_utf16le = False

        if is_hex:
            try:
                clean_hex = re.sub(r'[^0-9a-fA-F]', '', val_str)
                val_bytes = bytes.fromhex(clean_hex)
            except Exception:
                val_bytes = val_str.encode("latin1", errors="replace")
        elif explicit_enc:
            use_utf16le = (explicit_enc.upper() == "UTF-16LE")
            val_bytes = val_str.encode("utf-16le") if use_utf16le else val_str.encode("latin1", errors="replace")
        else:
            probe_len = min(len(val_str) * 2 + 4, 64, len(data) - off)
            probe = data[off:off + probe_len]
            even_b = probe[0::2][:len(val_str)]
            odd_b  = probe[1::2][:len(val_str)]
            printable_even = sum(0x20 <= b <= 0x7E for b in even_b)
            use_utf16le = (
                probe_len >= 4
                and all(b == 0 for b in odd_b)
                and printable_even >= max(2, len(val_str) // 2)
            )
            val_bytes = val_str.encode("utf-16le") if use_utf16le else val_str.encode("latin1", errors="replace")

        val_byte_len = len(val_bytes)
        if off + val_byte_len > len(data):
            return False

        if end_off and end_off > off:
            slot_len = end_off - off
            write_len = max(val_byte_len, slot_len)
        else:
            orig_alloc = DMIInjector._find_alloc(data, off, use_utf16le, val_byte_len) if not is_hex else val_byte_len
            write_len = max(val_byte_len, orig_alloc)

        if off + write_len > len(data):
            write_len = len(data) - off

        write_buf = val_bytes + b"\x00" * (write_len - val_byte_len)
        data[off:off + write_len] = write_buf

        if is_hex:
            rb_bytes = data[off:off + val_byte_len]
            ok = (rb_bytes == val_bytes)
            rb = ':'.join(f"{b:02X}" for b in rb_bytes)
            enc = "HEX"
        else:
            rb = (data[off:off + val_byte_len].decode("utf-16le", errors="replace")
                  if use_utf16le
                  else data[off:off + val_byte_len].decode("latin1", errors="replace"))
            ok = rb.rstrip("\x00") == val_str
            enc = "UTF-16LE" if use_utf16le else "ASCII"
        hx = f"<a href='hexjump:///0x{off:X}' style='color:#00f3ff;text-decoration:underline;'>0x{off:X}</a>"

        if ok:
            bounds_str = f" [0x{off:X} - 0x{off+write_len:X}] ({write_len}B)"
            _log(
                f"  - <font color='#ffd600'><b>[INJECTED {enc}]</b></font> "
                f"via {label}: {field_name} = '{val_str}' @ {hx}{bounds_str}"
            )
        else:
            _log(
                f"  - <font color='#ff8c00'><b>[VERIFY FAIL]</b></font> "
                f"{field_name} @ {hx}: wrote '{val_str}', readback '{rb}'"
            )
        return ok

    @staticmethod
    def _search_and_write(data, val_str, field_name, log_cb=None):
        def _log(m):
            if log_cb:
                log_cb(m)

        # 1. Direct exact string search (ASCII or UTF-16LE)
        for enc_bytes, enc_name in [
            (val_str.encode("latin1", errors="replace"), "ASCII"),
            (val_str.encode("utf-16le"),                 "UTF-16LE"),
        ]:
            found = data.find(enc_bytes)
            if found != -1:
                _log(
                    f"  - <font color='#ffd600'>[SEARCH]</font> "
                    f"'{val_str}' found @ 0x{found:X} ({enc_name}) - writing..."
                )
                return DMIInjector._write_at(data, found, val_str, field_name,
                                             label=f"search({enc_name})", log_cb=log_cb)

        # 2. Targeted replacement for Windows OEM Key (MSDM pattern)
        if field_name == "Windows OEM Key" or re.match(r'^[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}$', val_str):
            m = re.search(rb'[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}', bytes(data))
            if m:
                found = m.start()
                _log(f"  - <font color='#ffd600'>[MSDM KEY REPLACE]</font> Found existing Windows Key @ 0x{found:X} - replacing with original...")
                return DMIInjector._write_at(data, found, val_str, field_name, end_off=found + len(val_str),
                                             label="MSDM key slot", log_cb=log_cb)

        # 3. Targeted replacement for PPID / Board Serial (CN0 pattern)
        if field_name in ["PPID", "Board Serial"] or val_str.startswith("CN0"):
            m = re.search(rb'CN0[A-Z0-9]{20,23}', bytes(data))
            if m:
                found = m.start()
                _log(f"  - <font color='#ffd600'>[PPID REPLACE]</font> Found motherboard PPID @ 0x{found:X} - replacing with original...")
                return DMIInjector._write_at(data, found, val_str, field_name, end_off=found + len(val_str),
                                             label="PPID slot", log_cb=log_cb)

        # 4. Targeted search for Service Tag labels (Service Tag: or ServiceTag)
        if field_name in ["Service Tag", "Serial Number"] and len(val_str) == 7:
            for lbl in [b'Service Tag:', b'Service Tag', b'ServiceTag:', b'ServiceTag']:
                p = data.find(lbl)
                if p != -1:
                    slot_off = p + len(lbl)
                    while slot_off < len(data) and data[slot_off] in (0x20, 0x3A, 0x00, 0xFF):
                        slot_off += 1
                    if slot_off + 7 <= len(data):
                        _log(f"  - <font color='#ffd600'>[SERVICE TAG LABEL]</font> Found '{lbl.decode()}' @ 0x{p:X} -> writing to 0x{slot_off:X}...")
                        return DMIInjector._write_at(data, slot_off, val_str, field_name, end_off=slot_off + 7,
                                                     label="Service Tag label slot", log_cb=log_cb)

        # 5. Targeted replacement for Lenovo MTM / Product Number
        if field_name in ["MTM", "Product Number"] and re.match(r'^(?:20[A-Z0-9]{8}|21[A-Z0-9]{8}|8[0-3][A-Z0-9]{8})$', val_str):
            m = re.search(rb'\b(?:20[A-Z0-9]{8}|21[A-Z0-9]{8}|8[0-3][A-Z0-9]{8})\b', bytes(data))
            if m:
                found = m.start()
                _log(f"  - <font color='#ffd600'>[LENOVO MTM REPLACE]</font> Found MTM slot @ 0x{found:X} - replacing with original...")
                return DMIInjector._write_at(data, found, val_str, field_name, end_off=found + len(val_str),
                                             label="Lenovo MTM slot", log_cb=log_cb)

        # 6. Targeted replacement for Lenovo Barcode (1S... pattern)
        if field_name == "Barcode" and val_str.startswith("1S"):
            m = re.search(rb'1S[A-Z0-9]{18,25}', bytes(data))
            if m:
                found = m.start()
                _log(f"  - <font color='#ffd600'>[LENOVO BARCODE REPLACE]</font> Found barcode slot @ 0x{found:X} - replacing with original...")
                return DMIInjector._write_at(data, found, val_str, field_name, end_off=found + len(val_str),
                                             label="Lenovo Barcode slot", log_cb=log_cb)

        # 7. Targeted replacement for Lenovo Board Product (SDK... WIN pattern)
        if field_name == "Board Product" or val_str.startswith("SDK"):
            m = re.search(rb'SDK[A-Z0-9]{6,12}\s+WIN', bytes(data))
            if m:
                found = m.start()
                _log(f"  - <font color='#ffd600'>[LENOVO BOARD PRODUCT]</font> Found board slot @ 0x{found:X} - replacing with original...")
                return DMIInjector._write_at(data, found, val_str, field_name, end_off=found + len(val_str),
                                             label="Lenovo Board Product slot", log_cb=log_cb)

        # 8. Targeted replacement for Acer 22-character Serial Number
        if field_name in ["Serial Number", "System Serial Number"] and len(val_str) == 22:
            for pref in [b'NX', b'NH', b'UN', b'DT', b'NC', b'LU', b'LX']:
                m = re.search(rb'\b' + re.escape(pref) + rb'[A-Z0-9]{20}\b', bytes(data))
                if m:
                    found = m.start()
                    _log(f"  - <font color='#ffd600'>[ACER SERIAL REPLACE]</font> Found serial slot @ 0x{found:X} - replacing with original...")
                    return DMIInjector._write_at(data, found, val_str, field_name, end_off=found + 22,
                                                 label="Acer Serial Number slot", log_cb=log_cb)

        # 9. Targeted replacement for Acer SNID (11 or 12 digits)
        if field_name == "SNID" or (re.match(r'^[0-9]{11,12}$', val_str) and field_name != "UUID"):
            for lbl in [b'SNID:', b'SNID =', b'SNID ']:
                p = data.find(lbl)
                if p != -1:
                    slot_off = p + len(lbl)
                    while slot_off < len(data) and data[slot_off] in (0x20, 0x3A, 0x00):
                        slot_off += 1
                    if slot_off + len(val_str) <= len(data):
                        _log(f"  - <font color='#ffd600'>[ACER SNID LABEL]</font> Found '{lbl.decode()}' @ 0x{p:X} -> writing to 0x{slot_off:X}...")
                        return DMIInjector._write_at(data, slot_off, val_str, field_name, end_off=slot_off + len(val_str),
                                                     label="Acer SNID label slot", log_cb=log_cb)
            m = re.search(rb'\b[0-9]{11,12}\b', bytes(data))
            if m:
                found = m.start()
                _log(f"  - <font color='#ffd600'>[ACER SNID REPLACE]</font> Found SNID slot @ 0x{found:X} - replacing with original...")
                return DMIInjector._write_at(data, found, val_str, field_name, end_off=found + len(val_str),
                                             label="Acer SNID slot", log_cb=log_cb)

        # 10. Targeted replacement for ASUS Serial Number
        if field_name in ["Serial Number", "System Serial Number"] and len(val_str) >= 10:
            for lbl in [b'S/N:', b'S/N =', b'S/N ', b'Serial Number:', b'Serial Number =']:
                p = data.find(lbl)
                if p != -1:
                    slot_off = p + len(lbl)
                    while slot_off < len(data) and data[slot_off] in (0x20, 0x3A, 0x00):
                        slot_off += 1
                    if slot_off + len(val_str) <= len(data):
                        _log(f"  - <font color='#ffd600'>[ASUS S/N LABEL]</font> Found '{lbl.decode()}' @ 0x{p:X} -> writing to 0x{slot_off:X}...")
                        return DMIInjector._write_at(data, slot_off, val_str, field_name, end_off=slot_off + len(val_str),
                                                     label="ASUS S/N label slot", log_cb=log_cb)

            for anchor in [b'ASUSTeK COMPUTER INC.', b'ASUSTeK']:
                pos = 0
                while True:
                    p = data.find(anchor, pos)
                    if p == -1:
                        break
                    pos = p + len(anchor)
                    window = bytes(data[p : min(len(data), p + 0x2000)])
                    m = re.search(rb'\b[A-Za-z0-9]{10,16}\b', window)
                    if m:
                        rel_off = m.start()
                        abs_off = p + rel_off
                        _log(f"  - <font color='#ffd600'>[ASUS SN PROXIMITY]</font> Found serial near ASUSTeK @ 0x{abs_off:X} - replacing...")
                        return DMIInjector._write_at(data, abs_off, val_str, field_name, end_off=abs_off + len(val_str),
                                                     label="ASUS Serial proximity slot", log_cb=log_cb)

        return False

    @staticmethod
    def _smbios_inject(data, field_name, val_str, log_cb=None):
        def _log(m):
            if log_cb:
                log_cb(m)

        if field_name not in FIELD_TO_SMBIOS:
            return False

        smbios_type, str_idx_off = FIELD_TO_SMBIOS[field_name]
        content = bytes(data)

        for anchor in [b"_SM_", b"_SM3_", b"_DMI_"]:
            for m in re.finditer(re.escape(anchor), content):
                anchor_off  = m.start()
                search_reg  = content[anchor_off: anchor_off + 0x2000]

                for rel in range(0, len(search_reg) - 32):
                    if search_reg[rel] != smbios_type:
                        continue
                    struct_len = search_reg[rel + 1]
                    if not (8 <= struct_len <= 0x80):
                        continue

                    struct_off = anchor_off + rel

                    if rel + str_idx_off >= len(search_reg):
                        continue
                    str_slot_idx = search_reg[rel + str_idx_off]
                    if str_slot_idx == 0:
                        data[struct_off + str_idx_off] = 1
                        str_slot_idx = 1

                    str_area_off = anchor_off + rel + struct_len
                    if str_area_off >= len(data):
                        continue

                    target_str_off = DMIInjector._walk_string_area(
                        content, str_area_off, str_slot_idx
                    )
                    if target_str_off is None:
                        target_str_off = str_area_off

                    _log(
                        f"  - <font color='#00bfff'>[SMBIOS T{smbios_type}]</font> "
                        f"{field_name}: slot {str_slot_idx} @ 0x{target_str_off:X}"
                    )
                    return DMIInjector._write_at(
                        data, target_str_off, val_str, field_name,
                        label=f"SMBIOS Type{smbios_type} slot{str_slot_idx}",
                        log_cb=log_cb,
                    )

        _log(
            f"  - <font color='#888'>[SMBIOS]</font> "
            f"No SMBIOS anchor found for '{field_name}' in this binary."
        )
        return False

    @staticmethod
    def _find_alloc(data, off, utf16le, min_len):
        if utf16le:
            pos, limit = off, min(off + 512, len(data) - 1)
            alloc = min_len
            while pos + 1 < limit:
                if data[pos] == 0 and data[pos + 1] == 0:
                    alloc = pos - off
                    break
                pos += 2
            else:
                alloc = max(min_len, pos - off)
        else:
            pos, limit = off, min(off + 256, len(data))
            alloc = min_len
            while pos < limit:
                if data[pos] == 0:
                    alloc = pos - off
                    break
                pos += 1
            else:
                alloc = max(min_len, pos - off)
        return max(alloc, min_len)

    @staticmethod
    def _walk_string_area(content, str_area_off, target_idx):
        pos   = str_area_off
        limit = min(str_area_off + 0x400, len(content))
        cur   = 1

        while pos < limit:
            b = content[pos]
            if b in (0x00, 0xFF):
                nxt = content[pos + 1] if pos + 1 < limit else 0x00
                if b == 0xFF or nxt == 0x00:
                    return pos if cur <= target_idx else None
                if cur == target_idx:
                    return pos
                cur += 1
                pos += 1
            else:
                start = pos
                while pos < limit and content[pos] not in (0x00, 0xFF):
                    pos += 1
                if cur == target_idx:
                    return start
                cur += 1
                pos += 1

        return None
