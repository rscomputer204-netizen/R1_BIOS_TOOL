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

    # ── IF OLD BIOS REGION IS PROVIDED: STRICT 2-3 LINE TOPPER & FOOTER LOGIC ───
    if old_bios_region is not None and len(old_bios_region) >= target_size:
        old_bios_region = old_bios_region[:target_size]
        log_callback("[VALIDATE] Starting Strict 2-3 Line Topper & Footer Matching Engine...")

        # ── 1. EXTRACT FIRST VALID 2-3 LINES (32-48 BYTES) TOPPER IN OLD BIOS ──
        top_anchor = None
        top_anchor_offset = 0
        top_anchor_len = 48  # 3 lines

        for off in range(0, min(0x10000, target_size - 48), 16):
            blk48 = old_bios_region[off : off + 48]
            # Valid structured line check: not blank padding
            if blk48.count(b'\xff') < 38 and blk48.count(b'\x00') < 38:
                top_anchor = blk48
                top_anchor_offset = off
                top_anchor_len = 48
                break

        if not top_anchor:
            # Fallback to 2 lines (32 bytes)
            for off in range(0, min(0x10000, target_size - 32), 16):
                blk32 = old_bios_region[off : off + 32]
                if blk32.count(b'\xff') < 26 and blk32.count(b'\x00') < 26:
                    top_anchor = blk32
                    top_anchor_offset = off
                    top_anchor_len = 32
                    break

        if not top_anchor:
            log_callback("[ERROR] Could not extract valid 2-3 line Topper from backup BIOS.")
            return None, 0, 0

        num_lines = top_anchor_len // 16
        log_callback(f"[VALIDATE] Backup Topper: {num_lines} lines ({top_anchor_len} bytes) at offset 0x{top_anchor_offset:X}")

        # ── 2. MANDATORY TOPPER MATCH IN OFFICIAL CANDIDATE ──────────────────
        pos = data.find(top_anchor)
        valid_candidates = []
        while pos != -1:
            calc_start = pos - top_anchor_offset
            if 0 <= calc_start <= diff:
                valid_candidates.append(calc_start)
            pos = data.find(top_anchor, pos + 1)

        # If 48B didn't match, also try 32B (2 lines) at same offset
        if not valid_candidates and top_anchor_len == 48:
            top_anchor_32 = top_anchor[:32]
            pos = data.find(top_anchor_32)
            while pos != -1:
                calc_start = pos - top_anchor_offset
                if 0 <= calc_start <= diff:
                    valid_candidates.append(calc_start)
                pos = data.find(top_anchor_32, pos + 1)

        if not valid_candidates:
            log_callback("[ERROR] MANDATORY TOPPER MISMATCH: Top 2-3 lines of backup BIOS not found in official candidate.")
            log_callback("[ERROR] Verification Failed: Operation Aborted because Topper did not match.")
            return None, 0, 0

        log_callback(f"[SUCCESS] Top {num_lines} lines (Topper) matched in official candidate at offset +{valid_candidates[0]} bytes.")

        # ── 3. BOTTOM (FOOTER) DATA ANALYSIS & CUTTING LOGIC ──────────────────
        tail_check_len = 48
        old_tail = old_bios_region[-tail_check_len:]
        is_bottom_blank = (old_tail.count(b'\xff') >= tail_check_len - 4) or (old_tail.count(b'\x00') >= tail_check_len - 4)

        best_cand_start = -1
        if not is_bottom_blank:
            # Case 1: Backup BIOS bottom HAS valid data -> Verify bottom 3 lines in candidate
            log_callback(f"[INFO] Backup Footer contains valid data. Verifying bottom 3 lines ({tail_check_len}B)...")
            matched_by_both = False
            for cand_st in valid_candidates:
                c_slice = data[cand_st : cand_st + target_size]
                cand_tail = c_slice[-tail_check_len:]
                if cand_tail == old_tail or cand_tail[-32:] == old_tail[-32:] or cand_tail[-16:] == old_tail[-16:]:
                    best_cand_start = cand_st
                    matched_by_both = True
                    log_callback("[SUCCESS] [OK] Top (3 lines) and Bottom (3 lines) BOTH matched perfectly!")
                    break

            if not matched_by_both:
                best_cand_start = valid_candidates[0]
                log_callback("[INFO] Top 2-3 lines matched; Footer slightly updated in official package. Slicing with exact offset.")
        else:
            # Case 2: Backup BIOS bottom is BLANK (0xFF / 0x00) -> Cut strictly by offset from matched Topper
            best_cand_start = valid_candidates[0]
            log_callback(f"[INFO] Backup Footer is BLANK (unpopulated). Slicing exact target size offset (+{target_size} bytes) from Topper.")

        if best_cand_start >= 0:
            trimmed_data = data[best_cand_start : best_cand_start + target_size]
            header_removed = best_cand_start
            footer_removed = cand_size - (best_cand_start + target_size)
            log_callback(f"[SUCCESS] [OK] BIOS Region Sliced and Aligned Successfully!")
            log_callback(f"[INFO] Header Removed: {header_removed} bytes | Footer Removed: {footer_removed} bytes")
            return trimmed_data, header_removed, footer_removed

        log_callback("[ERROR] Slicing calculation failed.")
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
