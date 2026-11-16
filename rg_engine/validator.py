"""
BIOS Region Validator & Smart Slicer
====================================
Matches candidate BIOS/donor file against Original (Old) BIOS Region:
- Case 1: Both Topper (Header) and Footer match -> Cut & replace cleanly.
- Case 2: Topper matches, but Footer is blank/unpopulated (0xFF/0x00) -> Cut by exact offset distance from Topper.
- Case 3: Neither matches -> Reject with error.
"""
import os

def validate_and_trim(candidate_path, target_size, old_bios_region=None, log_callback=print):
    """
    Validates a candidate/donor file and trims it to match target BIOS region size.
    
    Args:
        candidate_path (str | bytes): File path or raw bytes of the candidate file.
        target_size (int): Target BIOS region size in bytes.
        old_bios_region (bytes | None): Raw bytes of the original loaded BIOS region.
        log_callback (callable): Logging function for terminal output.
        
    Returns:
        tuple: (trimmed_data, header_removed, footer_removed) or (None, 0, 0) if rejected.
    """
    if isinstance(candidate_path, (bytes, bytearray)):
        data = bytes(candidate_path)
    else:
        with open(candidate_path, "rb") as f:
            data = f.read()

    cand_size = len(data)
    log_callback(f"[INFO] Candidate size: {cand_size} bytes | Target region size: {target_size} bytes")

    if cand_size < target_size:
        log_callback(f"[ERROR] Candidate file is too small. Expected at least {target_size} bytes, got {cand_size} bytes.")
        return None, 0, 0

    diff = cand_size - target_size

    # ── IF OLD BIOS REGION IS PROVIDED: STRICT UNIVERSAL 3-CASE VALIDATION ───
    if old_bios_region is not None and len(old_bios_region) >= target_size:
        old_bios_region = old_bios_region[:target_size]
        log_callback("[VALIDATE] Starting Smart Topper & Footer Comparison...")

        best_cand_start = -1
        match_method = ""
        top_matched = False
        footer_matched = False

        # ── STRATEGY 1: Footer (Reset Vector & Entry Stub) Alignment ──────────
        # In x86 PC architectures, BIOS Region always ends at 4GB / Reset Vector.
        # This is the single most accurate, universal anchor across all manufacturers.
        for tail_len in [64, 32, 16]:
            old_tail = old_bios_region[-tail_len:]
            if old_tail.count(b'\xff') < tail_len - 2 and old_tail.count(b'\x00') < tail_len - 2:
                pos = data.find(old_tail)
                while pos != -1:
                    calc_start = pos + tail_len - target_size
                    if 0 <= calc_start <= diff:
                        c_slice = data[calc_start : calc_start + target_size]
                        # Verify slice structure (contains UEFI Firmware Volumes or valid code)
                        if b'_FVH' in c_slice:
                            best_cand_start = calc_start
                            footer_matched = True
                            match_method = f"Footer Anchor (Reset Vector {tail_len}B) & UEFI Structure Alignment"
                            break
                    pos = data.find(old_tail, pos + 1)
                if best_cand_start >= 0:
                    break

        # ── STRATEGY 2: UEFI Firmware Volume (_FVH) Structure Alignment ───────
        if best_cand_start < 0:
            # Find all _FVH locations in old_bios_region
            fvh_offsets = []
            fpos = 0
            while True:
                fpos = old_bios_region.find(b'_FVH', fpos)
                if fpos == -1:
                    break
                fvh_offsets.append(fpos)
                fpos += 4

            for fvh_pos in fvh_offsets:
                anc_start = max(0, fvh_pos - 0x28)
                anc_len = min(72, len(old_bios_region) - anc_start)
                anchor = old_bios_region[anc_start : anc_start + anc_len]
                if anchor.count(b'\xff') < anc_len - 8:
                    pos = data.find(anchor)
                    while pos != -1:
                        calc_start = pos - anc_start
                        if 0 <= calc_start <= diff:
                            c_slice = data[calc_start : calc_start + target_size]
                            tail16 = c_slice[-16:]
                            # Check reset vector jmp opcode or identical footer
                            if tail16 == old_bios_region[-16:] or b'\xe9' in tail16 or b'\xea' in tail16 or tail16[-2:] == b'\xff\xff':
                                best_cand_start = calc_start
                                top_matched = True
                                match_method = f"UEFI Volume Anchor (_FVH at 0x{fvh_pos:X}) Alignment"
                                break
                        pos = data.find(anchor, pos + 1)
                    if best_cand_start >= 0:
                        break

        # ── STRATEGY 3: Top Anchor (Header) Alignment ─────────────────────────
        if best_cand_start < 0:
            for off in range(0, min(0x10000, target_size - 64), 16):
                blk = old_bios_region[off : off + 64]
                if blk.count(b'\xff') < 48 and blk.count(b'\x00') < 48:
                    pos = data.find(blk)
                    while pos != -1:
                        calc_start = pos - off
                        if 0 <= calc_start <= diff:
                            c_slice = data[calc_start : calc_start + target_size]
                            if c_slice[-16:] == old_bios_region[-16:] or b'_FVH' in c_slice:
                                best_cand_start = calc_start
                                top_matched = True
                                match_method = "Topper Header Anchor Alignment"
                                break
                        pos = data.find(blk, pos + 1)
                    if best_cand_start >= 0:
                        break

        # ── STRATEGY 4: Standard Offsets & Flash Descriptor Offsets ───────────
        if best_cand_start < 0:
            candidate_offsets = [0, 0x40, 0x100, 0x140, 0x200, 0x220, 2048, 0x1000, diff]
            # Check for candidate Flash Descriptor (e.g. encapsulated full SPI image)
            fd_pos = data.find(b'\x5A\xA5\xF0\x0F')
            if fd_pos != -1 and fd_pos >= 0x10:
                container_hdr = fd_pos - 0x10
                candidate_offsets.insert(0, container_hdr + (diff - container_hdr))
                candidate_offsets.insert(0, container_hdr)

            for std_off in candidate_offsets:
                if 0 <= std_off <= diff:
                    c_slice = data[std_off : std_off + target_size]
                    if c_slice[-16:] == old_bios_region[-16:] or (b'_FVH' in c_slice and (b'\xe9' in c_slice[-16:] or b'\xea' in c_slice[-16:])):
                        best_cand_start = std_off
                        match_method = f"Capsule / Container Standard Alignment (+{std_off} bytes)"
                        break

        # ── EVALUATION OF BEST SLICE ──────────────────────────────────────────
        if best_cand_start >= 0:
            c_slice = data[best_cand_start : best_cand_start + target_size]
            old_tail = old_bios_region[-64:]
            cand_tail = c_slice[-64:]

            old_blank = (old_tail.count(b'\xff') >= 56 or old_tail.count(b'\x00') >= 56)
            cand_blank = (cand_tail.count(b'\xff') >= 56 or cand_tail.count(b'\x00') >= 56)
            footer_is_blank = old_blank or cand_blank

            if cand_tail[-16:] == old_tail[-16:]:
                footer_matched = True
            elif (b'\xe9' in cand_tail[-16:] or b'\xea' in cand_tail[-16:]) and cand_tail.endswith(b'\x00\xe0\xff\xff'):
                footer_matched = True
            elif old_blank and cand_blank:
                footer_matched = True

            # Check top match
            if c_slice[:64] == old_bios_region[:64] or (b'_FVH' in c_slice and b'_FVH' in old_bios_region):
                top_matched = True

            # Decision
            if footer_matched or top_matched:
                log_callback(f"[SUCCESS] BIOS Region matched and aligned successfully! [OK]")
                log_callback(f"[INFO] Method: {match_method} | Offset: +{best_cand_start} bytes | Target Size: {target_size} bytes")
                trimmed_data = data[best_cand_start : best_cand_start + target_size]
                header_removed = best_cand_start
                footer_removed = cand_size - (best_cand_start + target_size)
                log_callback(f"[INFO] Header Removed: {header_removed} bytes | Footer Removed: {footer_removed} bytes")
                return trimmed_data, header_removed, footer_removed

        # If completely unaligned:
        log_callback("[ERROR] Validation Failed: Neither Topper nor Footer matched the loaded BIOS region! [FAIL]")
        log_callback("[REJECT] Incompatible file structure. Operation Cancelled.")
        return None, 0, 0

    # ── FALLBACK FOR CALLERS WITHOUT OLD BIOS REGION ─────────────────────────
    log_callback("Checking File Size...")
    if cand_size == target_size:
        log_callback("Validation Passed. (Size Matched Exactly)")
        return data, 0, 0

    log_callback(f"Size mismatch. Target: {target_size} | Candidate: {cand_size}")
    log_callback("Header Scan...")
    log_callback("Footer Scan...")

    # Check for AMI Capsule Header (2048 bytes)
    if diff == 2048:
        log_callback("Found standard 2048-byte Capsule Header. Trimming header...")
        return data[2048:], 2048, 0

    def _score_slice(s_off):
        if s_off < 0 or s_off + target_size > cand_size:
            return -1
        sl = data[s_off : s_off + target_size]
        tail = sl[-16:]
        score = 0
        if b'\xfe\x00\x00\x00\x00\xe0\xff\xff' in tail:
            score += 100
        elif (b'\xe9' in tail or b'\xea' in tail) and tail[-2:] == b'\xff\xff':
            score += 80
        elif b'\xe9' in tail or b'\xea' in tail:
            score += 50
        if tail.endswith(b'\x00\xe0\xff\xff'):
            score += 30
        if b'_FVH' in sl[:0x1000]:
            score += 20
        return score

    best_off = None
    best_score = -1

    for c in [0x220, 2048, 0x100, 0x200, 0, diff]:
        if 0 <= c <= diff:
            sc = _score_slice(c)
            if sc > best_score:
                best_score = sc
                best_off = c

    if best_score < 80:
        for p in range(target_size, cand_size + 1, 0x10):
            tail = data[p-16:p]
            if b'\xfe\x00\x00\x00\x00\xe0\xff\xff' in tail or (tail[-2:] == b'\xff\xff' and (b'\xe9' in tail or b'\xea' in tail)):
                s_off = p - target_size
                sc = _score_slice(s_off)
                if sc > best_score:
                    best_score = sc
                    best_off = s_off

    if best_off is not None and best_score > 0:
        header_removed = best_off
        footer_removed = diff - best_off
        trimmed_data = data[best_off : best_off + target_size]
        log_callback(f"Smart Alignment: Found BIOS image at offset +{header_removed} (Reset Vector verified, score {best_score}).")
        log_callback(f"Header Removed: {header_removed} bytes | Footer Removed: {footer_removed} bytes")
        return trimmed_data, header_removed, footer_removed
    else:
        log_callback("[ERROR] Validation Failed: Could not identify valid BIOS region.")
        return None, 0, 0
