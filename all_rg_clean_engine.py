"""
all_rg_clean_engine.py
======================
Multi-Region Matching & Surgical Factory Cleaning Engine.
Replaces all matching regions (BIOS, CSME, EC, GbE) from an official
manufacturer update package into the backup dump without DMI migration.
"""

import os
import struct
from pathlib import Path
from R1_CSME_Analyzer.r1_csme_parser import R1CSMEAnalyzer


def safe_path(p: str) -> str:
    """Returns extended-length path on Windows to avoid MAX_PATH (260) limitations."""
    if not p:
        return p
    p_abs = os.path.abspath(p)
    if os.name == 'nt' and not p_abs.startswith('\\\\?\\'):
        return '\\\\?\\' + p_abs
    return p_abs


def parse_dump_spi_regions(dump_bytes: bytearray) -> dict:
    """Parses SPI regions from Flash Descriptor table at 0x40."""
    regions = {}
    if len(dump_bytes) < 0x1000:
        return regions

    # Check FD signature at 0x10
    if dump_bytes[0x10:0x14] != b"\x5A\xA5\xF0\x0F":
        return regions

    reg_map = {
        0: "desc",
        1: "bios",
        2: "me",
        3: "gbe",
        8: "ec",
        9: "gbe2"
    }

    for i in range(16):
        entry_off = 0x40 + i * 4
        if entry_off + 4 > len(dump_bytes):
            break
        r_val = struct.unpack('<I', dump_bytes[entry_off:entry_off+4])[0]
        base = (r_val & 0x7FFF) << 12
        limit = ((r_val >> 16) & 0x7FFF) << 12 | 0xFFF
        if limit > base and (limit - base + 1) > 0x1000:
            name = reg_map.get(i, f"region_{i}")
            regions[name] = {
                "id": i,
                "name": name,
                "offset": base,
                "limit": limit,
                "size": limit - base + 1
            }

    return regions


def match_official_components(dump_path: str, extracted_files: list, log_cb=print) -> dict:
    """
    Scans and matches extracted components against the loaded backup dump.
    Returns a dictionary of matched items.
    """
    if not os.path.exists(safe_path(dump_path)) or not extracted_files:
        return {}

    with open(safe_path(dump_path), "rb") as f:
        dump_bytes = bytearray(f.read())

    regions = parse_dump_spi_regions(dump_bytes)
    
    # Run CSME Analyzer on dump
    dump_analyzer = R1CSMEAnalyzer(dump_path)
    dump_me = dump_analyzer.parse()
    dump_sku = (dump_me.get("sku") or "").upper()
    dump_ver = dump_me.get("version") or ""
    dump_cpu = (dump_me.get("cpu_gen") or "").upper()

    matches = {}

    bios_reg = regions.get("bios")
    me_reg = regions.get("me")
    ec_reg = regions.get("ec")
    gbe_reg = regions.get("gbe") or regions.get("gbe2")

    # 1. Match BIOS Region
    if bios_reg:
        target_size = bios_reg["size"]
        bios_candidates = []
        for f in extracted_files:
            try:
                sz = os.path.getsize(safe_path(f))
                fname = os.path.basename(f).lower()
                # Exact size match
                if sz == target_size:
                    score = 100
                    if "system bios" in fname:
                        score += 50
                    if "mtl" in fname and "METEOR" in dump_cpu:
                        score += 30
                    elif "rpl" in fname and ("RAPTOR" in dump_cpu or "ALDER" in dump_cpu):
                        score += 30
                    bios_candidates.append((score, f, sz))
                # Or trimmed match
                elif sz > target_size and (sz - target_size) <= 0x100000 and "system bios" in fname:
                    bios_candidates.append((50, f, sz))
            except Exception:
                continue

        if bios_candidates:
            bios_candidates.sort(key=lambda x: x[0], reverse=True)
            chosen_bios = bios_candidates[0][1]
            matches["bios"] = {
                "title": "System BIOS Region",
                "file": chosen_bios,
                "filename": os.path.basename(chosen_bios),
                "size": bios_reg["size"],
                "offset": bios_reg["offset"],
                "target_desc": f"{bios_reg['size'] // (1024 * 1024)} MB (Offset: 0x{bios_reg['offset']:X})"
            }

    # Detect package flavor from chosen BIOS (e.g. RPL vs MTL) for multi-flavor packages
    flavor = ""
    if "bios" in matches:
        bfn = matches["bios"]["filename"].lower()
        for candidate_flavor in ["mtl", "rpl", "adl", "tgl", "cfl", "kbl", "skl"]:
            if candidate_flavor in bfn:
                flavor = candidate_flavor
                break

    # 2. Match CSME / ME Region
    me_candidates = []
    for f in extracted_files:
        try:
            fname = os.path.basename(f).lower()
            if "management engine" in fname or "csme" in fname or "me_region" in fname:
                score = 50
                if "consumer" in fname and "CON" in dump_sku:
                    score += 100
                elif "corporate" in fname and "COR" in dump_sku:
                    score += 100
                if dump_ver and dump_ver in fname:
                    score += 50
                if flavor and flavor in fname:
                    score += 200
                me_candidates.append((score, f))
            else:
                # Check for $FPT in first 1MB
                with open(safe_path(f), "rb") as mf:
                    header = mf.read(0x4000)
                    if b"$FPT" in header or b"\x24\x46\x50\x54" in header:
                        me_candidates.append((30, f))
        except Exception:
            continue

    if me_candidates:
        me_candidates.sort(key=lambda x: x[0], reverse=True)
        chosen_me = me_candidates[0][1]
        sz = os.path.getsize(safe_path(chosen_me))
        matches["me"] = {
            "title": "CSME / ME Region",
            "file": chosen_me,
            "filename": os.path.basename(chosen_me),
            "size": sz,
            "version": dump_ver,
            "sku": dump_sku,
            "target_desc": f"Clean Factory ME (MFS -> Configured)"
        }

        # Physically parse FPT partition table from the official ME binary
        try:
            with open(safe_path(chosen_me), "rb") as mf:
                me_head = mf.read(0x8000)
            fpt_pos = me_head.find(b"\x24\x46\x50\x54")
            fpt_parts = set()
            if fpt_pos != -1:
                entries = int.from_bytes(me_head[fpt_pos + 4 : fpt_pos + 8], "little")
                for i in range(min(entries, 64)):
                    off = fpt_pos + 32 + i * 32
                    p_name = me_head[off : off + 4].rstrip(b"\x00").decode("ascii", errors="ignore").strip()
                    if p_name:
                        fpt_parts.add(p_name)

            if "PMCP" in fpt_parts or "PMC" in fpt_parts:
                matches["pmc"] = {
                    "title": "PMC Controller Firmware",
                    "file": chosen_me,
                    "filename": os.path.basename(chosen_me),
                    "size": sz,
                    "target_desc": "Intel Power Management Controller (Verified in CSME FPT)",
                    "op_desc": "Factory reset & configuration via CSME MFS injection"
                }
            if "PCHC" in fpt_parts:
                matches["pchc"] = {
                    "title": "PCHC Controller Firmware",
                    "file": chosen_me,
                    "filename": os.path.basename(chosen_me),
                    "size": sz,
                    "target_desc": "PCH Configuration Controller (Verified in CSME FPT)",
                    "op_desc": "Factory reset & configuration via CSME MFS injection"
                }
            if any(p in fpt_parts for p in ("IOMP", "IOM", "NPHY", "TBTP")):
                matches["iom_phy"] = {
                    "title": "Type-C IOM & PHY Controller",
                    "file": chosen_me,
                    "filename": os.path.basename(chosen_me),
                    "size": sz,
                    "target_desc": "Type-C I/O Manageability & PHY (Verified in CSME FPT)",
                    "op_desc": "Factory reset & configuration via CSME MFS injection"
                }
        except Exception:
            pass

    # 3. Match Standalone Type-C Retimer Controller (if present)
    retimer_candidates = []
    for f in extracted_files:
        fname = os.path.basename(f).lower()
        if "retimer" in fname or "tbt" in fname:
            score = 50
            if flavor and flavor in fname:
                score += 200
            retimer_candidates.append((score, f))
    if retimer_candidates:
        retimer_candidates.sort(key=lambda x: x[0], reverse=True)
        chosen_retimer = retimer_candidates[0][1]
        matches["tbt_retimer"] = {
            "title": "Type-C / Thunderbolt Retimer",
            "file": chosen_retimer,
            "filename": os.path.basename(chosen_retimer),
            "size": os.path.getsize(safe_path(chosen_retimer)),
            "target_desc": f"{os.path.getsize(safe_path(chosen_retimer)) // 1024} KB (Type-C Retimer FW)",
            "op_desc": "Official Type-C Thunderbolt Retimer controller update"
        }

    # 4. Match Embedded Controller (EC)
    if ec_reg:
        ec_candidates = []
        for f in extracted_files:
            fname = os.path.basename(f).lower()
            if "embedded controller" in fname or fname.startswith("ec_") or "_ec." in fname:
                # Prefer main over backup
                score = 100
                if "backup" in fname:
                    score = 40
                if flavor and flavor in fname:
                    score += 200
                elif "mtl" in fname and "METEOR" in dump_cpu:
                    score += 30
                elif "rpl" in fname and ("RAPTOR" in dump_cpu or "ALDER" in dump_cpu):
                    score += 30
                ec_candidates.append((score, f))
        if ec_candidates:
            ec_candidates.sort(key=lambda x: x[0], reverse=True)
            chosen_ec = ec_candidates[0][1]
            matches["ec"] = {
                "title": "Embedded Controller (EC)",
                "file": chosen_ec,
                "filename": os.path.basename(chosen_ec),
                "size": os.path.getsize(safe_path(chosen_ec)),
                "offset": ec_reg["offset"],
                "target_desc": f"{ec_reg['size'] // 1024} KB (Offset: 0x{ec_reg['offset']:X})"
            }

    # 4. Match Gigabit Ethernet (GbE)
    if gbe_reg:
        gbe_candidates = []
        for f in extracted_files:
            fname = os.path.basename(f).lower()
            if "gigabit ethernet" in fname or "gbe" in fname:
                score = 50
                if "consumer" in fname and "CON" in dump_sku:
                    score += 50
                elif "corporate" in fname and "COR" in dump_sku:
                    score += 50
                if flavor and flavor in fname:
                    score += 200
                elif "mtl" in fname and "METEOR" in dump_cpu:
                    score += 20
                elif "rpl" in fname and ("RAPTOR" in dump_cpu or "ALDER" in dump_cpu):
                    score += 20
                gbe_candidates.append((score, f))
        if gbe_candidates:
            gbe_candidates.sort(key=lambda x: x[0], reverse=True)
            chosen_gbe = gbe_candidates[0][1]
            matches["gbe"] = {
                "title": "Gigabit Ethernet (GbE)",
                "file": chosen_gbe,
                "filename": os.path.basename(chosen_gbe),
                "size": os.path.getsize(safe_path(chosen_gbe)),
                "offset": gbe_reg["offset"],
                "target_desc": f"{gbe_reg['size'] // 1024} KB (Offset: 0x{gbe_reg['offset']:X})"
            }

    return matches


def perform_all_rg_clean(dump_path: str, matches: dict, output_path: str, log_cb=print) -> dict:
    """
    Executes surgical multi-region clean and replacement from matched components.
    """
    if not os.path.exists(safe_path(dump_path)):
        raise FileNotFoundError(f"Dump file not found: {dump_path}")

    with open(safe_path(dump_path), "rb") as f:
        data = bytearray(f.read())

    report = []
    log_cb("[ACTION] Starting ALL RG CLEAN Engine...")

    # 1. Replace BIOS Region
    bios_match = matches.get("bios")
    if bios_match:
        bios_file = bios_match["file"]
        offset = bios_match["offset"]
        target_size = bios_match["size"]
        with open(safe_path(bios_file), "rb") as bf:
            b_data = bf.read()

        # Handle trimming if needed
        if len(b_data) > target_size:
            # Check for standard headers or trailer
            diff = len(b_data) - target_size
            b_data = b_data[:target_size]

        if len(b_data) == target_size:
            data[offset : offset + target_size] = b_data
            msg = f"Replaced System BIOS Region at 0x{offset:X} (Size: {target_size // (1024 * 1024)} MB)"
            log_cb(f"[SUCCESS] {msg}")
            report.append(msg)
        else:
            log_cb(f"[WARNING] BIOS candidate size ({len(b_data)}) != target ({target_size}). Skipped.")

    # 2. Clean & Replace CSME Region (MFS Factory Reset)
    me_match = matches.get("me")
    if me_match:
        me_file = me_match["file"]
        with open(safe_path(me_file), "rb") as mf:
            clean_me_bytes = mf.read()

        # Find $FPT in dump to locate MFS
        fpt_sig = b"\x24\x46\x50\x54"
        fpt_offsets = []
        pos = 0
        while True:
            p = data.find(fpt_sig, pos)
            if p == -1: break
            fpt_offsets.append(p)
            pos = p + 4

        mfs_cleaned = False
        for fpt_pos in fpt_offsets:
            entries = int.from_bytes(data[fpt_pos+4 : fpt_pos+8], "little")
            if entries > 64: continue
            for i in range(entries):
                entry_offset = fpt_pos + 32 + i * 32
                entry = data[entry_offset : entry_offset + 32]
                p_name = entry[:4].rstrip(b"\x00").decode("ascii", errors="ignore")
                poff = int.from_bytes(entry[8:12], "little")
                psize = int.from_bytes(entry[12:16], "little")
                abs_part_offset = fpt_pos + poff

                if p_name == "MFS" and psize > 0:
                    # Check if clean_me_bytes has MFS partition
                    clean_mfs_chunk = None
                    clean_fpt = clean_me_bytes.find(fpt_sig)
                    if clean_fpt != -1:
                        c_entries = int.from_bytes(clean_me_bytes[clean_fpt+4 : clean_fpt+8], "little")
                        for ci in range(min(c_entries, 64)):
                            c_entry_off = clean_fpt + 32 + ci * 32
                            c_entry = clean_me_bytes[c_entry_off : c_entry_off + 32]
                            if c_entry[:4].rstrip(b"\x00").decode("ascii", errors="ignore") == "MFS":
                                c_poff = int.from_bytes(c_entry[8:12], "little")
                                c_psize = int.from_bytes(c_entry[12:16], "little")
                                if c_psize == psize:
                                    clean_mfs_chunk = clean_me_bytes[clean_fpt + c_poff : clean_fpt + c_poff + c_psize]
                                    break

                    if clean_mfs_chunk:
                        data[abs_part_offset : abs_part_offset + psize] = clean_mfs_chunk
                        log_cb(f"[INFO] Injected clean factory MFS partition at 0x{abs_part_offset:X} (0x{psize:X} bytes).")
                    else:
                        data[abs_part_offset : abs_part_offset + psize] = b"\xFF" * psize
                        log_cb(f"[INFO] Wiped runtime MFS partition at 0x{abs_part_offset:X} to 0xFF.")

                    mfs_cleaned = True

                elif p_name in ("FLOG", "ELOG", "EFS", "MFSB", "MDMV") and psize > 0:
                    data[abs_part_offset : abs_part_offset + psize] = b"\xFF" * psize
                    log_cb(f"[INFO] Reset runtime partition '{p_name}' at 0x{abs_part_offset:X} to 0xFF.")

        if mfs_cleaned:
            msg = "CSME runtime partitions cleaned and transitioned to Configured"
            log_cb(f"[SUCCESS] {msg}")
            report.append(msg)

    # 3. Replace EC Region
    ec_match = matches.get("ec")
    if ec_match:
        ec_file = ec_match["file"]
        offset = ec_match["offset"]
        target_size = ec_match.get("size", 0)
        with open(safe_path(ec_file), "rb") as ef:
            ec_data = ef.read()

        # If EC file is smaller than region size, pad with 0xFF or write as-is
        if len(ec_data) <= target_size:
            data[offset : offset + len(ec_data)] = ec_data
            if len(ec_data) < target_size:
                data[offset + len(ec_data) : offset + target_size] = b"\xFF" * (target_size - len(ec_data))
            msg = f"Injected clean Embedded Controller (EC) at 0x{offset:X}"
            log_cb(f"[SUCCESS] {msg}")
            report.append(msg)

    # 4. Replace GbE Region
    gbe_match = matches.get("gbe")
    if gbe_match:
        gbe_file = gbe_match["file"]
        offset = gbe_match["offset"]
        target_size = gbe_match.get("size", 0)
        with open(safe_path(gbe_file), "rb") as gf:
            gbe_data = gf.read()

        if len(gbe_data) <= target_size:
            data[offset : offset + len(gbe_data)] = gbe_data
            msg = f"Injected clean Gigabit Ethernet (GbE) at 0x{offset:X}"
            log_cb(f"[SUCCESS] {msg}")
            report.append(msg)

    # Save output file
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(safe_path(output_path), "wb") as out_f:
        out_f.write(data)

    # Verification
    try:
        analyzer = R1CSMEAnalyzer(output_path)
        ver_res = analyzer.parse()
        fs_state = ver_res.get("fs_stage") or ver_res.get("fs_state") or "Unknown"
        log_cb(f"[VERIFY] Final CSME File System State: {fs_state}")
    except Exception as ve:
        log_cb(f"[WARNING] Verification pass notice: {ve}")

    log_cb(f"[SUCCESS] ALL RG CLEAN complete! Saved: {os.path.basename(output_path)}")
    return {
        "success": True,
        "output_path": output_path,
        "report": report
    }
