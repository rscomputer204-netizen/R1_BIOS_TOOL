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

    # ── IF OLD BIOS REGION IS PROVIDED: STRICT 3-CASE VALIDATION ──────────────
    if old_bios_region is not None and len(old_bios_region) >= target_size:
        old_bios_region = old_bios_region[:target_size]
        log_callback("[VALIDATE] Starting Smart Topper & Footer Comparison...")

        # 1. Identify Top Anchor in old_bios_region
        anchor = None
        anchor_old_off = -1
        
        # Check for UEFI Firmware Volume Header (_FVH at offset 0x28)
        fvh_pos = old_bios_region.find(b'_FVH')
        if fvh_pos != -1 and fvh_pos < 0x4000:
            start_anc = max(0, fvh_pos - 0x28)
            anchor = old_bios_region[start_anc : fvh_pos + 0x20]
            anchor_old_off = start_anc
        else:
            # Fallback anchor: first 64 non-trivial bytes
            for off in range(0, min(0x4000, target_size - 64), 16):
                blk = old_bios_region[off : off + 64]
                if blk.count(b'\xff') < 48 and blk.count(b'\x00') < 48:
                    anchor = blk
                    anchor_old_off = off
                    break

        top_matched = False
        best_cand_start = -1

        # Search for anchor in candidate data
        if anchor and anchor_old_off >= 0:
            pos = data.find(anchor)
            while pos != -1:
                calc_start = pos - anchor_old_off
                if 0 <= calc_start <= diff:
                    c_slice = data[calc_start : calc_start + target_size]
                    # Verify top prefix similarity
                    chk_len = min(anchor_old_off + len(anchor) + 32, len(c_slice))
                    if c_slice[:chk_len] == old_bios_region[:chk_len]:
                        top_matched = True
                        best_cand_start = calc_start
                        break
                    elif c_slice[anchor_old_off : anchor_old_off + len(anchor)] == anchor:
                        top_matched = True
                        best_cand_start = calc_start
                        break
                pos = data.find(anchor, pos + 1)

        # Also check standard offsets if anchor search didn't hit
        if not top_matched:
            for std_off in [0, 2048, 0x100, 0x200, 0x220, 0x800, diff]:
                if 0 <= std_off <= diff:
                    c_slice = data[std_off : std_off + target_size]
                    # Compare initial 64 bytes or FVH
                    if c_slice[:64] == old_bios_region[:64] or (b'_FVH' in c_slice[:0x1000] and b'_FVH' in old_bios_region[:0x1000]):
                        top_matched = True
                        best_cand_start = std_off
                        break

        # 2. Check Footer (Tail)
        footer_matched = False
        footer_is_blank = False

        if top_matched and best_cand_start >= 0:
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

        # 3. Decision based on User's 3 Rules
        if top_matched and footer_matched:
            # ── CASE 1: Both Topper and Footer matched ──
            log_callback("[SUCCESS] Topper and Footer matched original BIOS Region! [OK]")
            log_callback(f"[INFO] Slice aligned at +{best_cand_start} bytes | Target Size: {target_size} bytes")
            trimmed_data = data[best_cand_start : best_cand_start + target_size]
            header_removed = best_cand_start
            footer_removed = cand_size - (best_cand_start + target_size)
            return trimmed_data, header_removed, footer_removed

        elif top_matched and (footer_is_blank or not footer_matched):
            # ── CASE 2: Topper matched, Footer blank / unpopulated -> Offset-based cut ──
            log_callback("[INFO] Topper matched successfully! [OK]")
            log_callback("[INFO] Footer area is blank/unpopulated (0xFF/0x00 padding).")
            log_callback(f"[ACTION] Slicing by exact offset distance: Start +{best_cand_start}, Length {target_size} bytes.")
            trimmed_data = data[best_cand_start : best_cand_start + target_size]
            header_removed = best_cand_start
            footer_removed = cand_size - (best_cand_start + target_size)
            return trimmed_data, header_removed, footer_removed

        else:
            # ── CASE 3: Neither Topper nor Footer matched -> REJECT ──
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
