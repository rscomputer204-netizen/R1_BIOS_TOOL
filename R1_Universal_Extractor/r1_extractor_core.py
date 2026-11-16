"""
R1_Universal_Extractor: r1_extractor_core.py
=============================================
Core Universal BIOS & Firmware Extractor Engine for R1 BIOS TOOL.
100% Native, Multi-Tiered, Standalone Extraction Engine.

Tiers:
1. BIOS Vendor Decoders (Dell PFS, Insyde IFD, AMI PFAT/UCP, Phoenix TDK, Apple EFI, etc.)
2. Capsule Unpackers (ASUS/AMI/ASRock Aptio Capsule header stripping)
3. Advanced Installer & Container Decoders (Inno Setup via innounp, 7-Zip Multi-Archive, CAB, MSI)
4. Deep Firmware Carver (Flash Descriptor & UEFI FV Carving for packed/encrypted exes)
5. Smart Output Classifier (Detects Main BIOS, EC, ME, and generates audit report)
"""

import os
import sys
import io
import re
import shutil
import struct
import subprocess
import contextlib
import time
from pathlib import Path
from typing import Callable, Optional, Dict, List, Tuple

try:
    import psutil
except ImportError:
    psutil = None

# Ensure project root is in sys.path so biosutilities can be imported
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from biosutilities.ami_pfat_extract import AmiPfatExtract
    from biosutilities.ami_ucp_extract import AmiUcpExtract
    from biosutilities.apple_efi_id import AppleEfiIdentify
    from biosutilities.apple_efi_im4p import AppleEfiIm4pSplit
    from biosutilities.apple_efi_pbzx import AppleEfiPbzxExtract
    from biosutilities.apple_efi_pkg import AppleEfiPkgExtract
    from biosutilities.award_bios_extract import AwardBiosExtract
    from biosutilities.dell_pfs_extract import DellPfsExtract
    from biosutilities.fujitsu_sfx_extract import FujitsuSfxExtract
    from biosutilities.fujitsu_upc_extract import FujitsuUpcExtract
    from biosutilities.insyde_ifd_extract import InsydeIfdExtract
    from biosutilities.panasonic_bios_extract import PanasonicBiosExtract
    from biosutilities.phoenix_tdk_extract import PhoenixTdkExtract
    from biosutilities.portwell_efi_extract import PortwellEfiExtract
    from biosutilities.toshiba_com_extract import ToshibaComExtract
    from biosutilities.vaio_package_extract import VaioPackageExtract
    HAS_BIOSUTILITIES = True
except ImportError:
    HAS_BIOSUTILITIES = False


class R1ExtractorCore:
    """Multi-tiered universal extractor for BIOS updates, installers, and firmware images."""

    # Native CLI helpers bundled directly with R1 Universal Extractor
    _NATIVE_BIN_DIR = os.path.join(os.path.dirname(__file__), "bin")
    _7Z_PATH = os.path.join(_NATIVE_BIN_DIR, "7z.exe")
    _INNOUNP_PATH = os.path.join(_NATIVE_BIN_DIR, "innounp.exe")
    _INNOEXTRACT_PATH = os.path.join(_NATIVE_BIN_DIR, "innoextract.exe")

    FD_MAGIC = b"\x5A\xA5\xF0\x0F"
    UEFI_FVH_MAGIC = b"_FVH"

    @classmethod
    def get_7z_path(cls) -> Optional[str]:
        if os.path.isfile(cls._7Z_PATH):
            return cls._7Z_PATH
        # Check system PATH
        which_7z = shutil.which("7z") or shutil.which("7za")
        return which_7z

    @classmethod
    def get_innounp_path(cls) -> Optional[str]:
        if os.path.isfile(cls._INNOUNP_PATH):
            return cls._INNOUNP_PATH
        return shutil.which("innounp")

    @classmethod
    def get_innoextract_path(cls) -> Optional[str]:
        if os.path.isfile(cls._INNOEXTRACT_PATH):
            return cls._INNOEXTRACT_PATH
        ext_lenovo = os.path.join(PROJECT_ROOT, "external", "LENOVO BIOS EXTRACTOR", "LENOVO BIOS EXTRACTOR.exe")
        if os.path.isfile(ext_lenovo):
            return ext_lenovo
        return shutil.which("innoextract")

    @classmethod
    def extract(cls, input_file: str, output_dir: Optional[str] = None, logger: Optional[Callable[[str], None]] = None) -> Dict:
        """
        Main extraction entry point.
        Attempts Tier 1 through Tier 4 extraction on input_file.
        Returns a dictionary summary with results and classified files.
        """
        def log(msg: str):
            if logger:
                logger(msg)
            else:
                print(msg)

        if not os.path.isfile(input_file):
            log(f"[ERROR] Input file does not exist: {input_file}")
            return {"success": False, "error": "File not found", "files": []}

        file_size = os.path.getsize(input_file)
        base_name = os.path.basename(input_file)
        stem = os.path.splitext(base_name)[0]

        if not output_dir:
            output_dir = os.path.join(os.path.dirname(input_file), f"{stem}_extracted")

        os.makedirs(output_dir, exist_ok=True)

        log(f"[START] R1 Universal Extractor v2.0")
        log(f"[TARGET] File: {base_name} ({file_size:,} bytes)")
        log(f"[OUTPUT] Directory: {output_dir}")

        extracted_any = False
        method_used = "None"

        # -------------------------------------------------------------
        # TIER 1: BIOS Vendor Firmware Decoders (biosutilities)
        # -------------------------------------------------------------
        log("[TIER 1] Checking specialized BIOS vendor firmware formats...")
        t1_success, t1_method = cls._try_tier1_vendor_extract(input_file, output_dir, log)
        if t1_success:
            extracted_any = True
            method_used = t1_method
            log(f"[SUCCESS] Tier 1 Extracted successfully using {method_used}!")

        # -------------------------------------------------------------
        # TIER 2: Capsule Header Stripper (ASUS/AMI/ASRock .CAP)
        # -------------------------------------------------------------
        if not extracted_any:
            log("[TIER 2] Checking for UEFI Capsule Header (.CAP) format...")
            t2_success, t2_file = cls._try_tier2_capsule_strip(input_file, output_dir, log)
            if t2_success:
                extracted_any = True
                method_used = "Aptio Capsule Stripper"
                log(f"[SUCCESS] Tier 2 Extracted raw BIOS from Capsule: {os.path.basename(t2_file)}")

        # Check for standalone protected OEM SFX Executable (HP, Acer, Lenovo, Dell, Asus, Clevo, etc.)
        if not extracted_any and cls._is_protected_sfx(input_file):
            log("[PROTECTED SFX] Detected standalone OEM protected SFX container...")
            sfx_ok, sfx_files = cls._extract_protected_sfx_live(input_file, output_dir, log)
            if sfx_ok and sfx_files:
                extracted_any = True
                method_used = "Universal OEM Protected SFX Live Unpacker"
                log(f"[SUCCESS] Extracted {len(sfx_files)} BIOS binary file(s) from protected SFX!")

        # -------------------------------------------------------------
        # TIER 3: Container & Installer Decompression (7-Zip & InnoUnp)
        # -------------------------------------------------------------
        if not extracted_any:
            log("[TIER 3] Checking Windows Installer & Archive containers (Inno, 7-Zip, SFX, CAB)...")
            t3_success, t3_method = cls._try_tier3_installer_unpack(input_file, output_dir, log)
            if t3_success:
                extracted_any = True
                method_used = t3_method
                log(f"[SUCCESS] Tier 3 Extracted successfully using {method_used}!")

        # -------------------------------------------------------------
        # TIER 4: Deep Binary Firmware Carver (Raw Signature Search)
        # -------------------------------------------------------------
        # Even if Tier 3 extracted generic installer files, check if any raw BIOS can be carved
        carved_files = cls._try_tier4_deep_carve(input_file, output_dir, log)
        if carved_files:
            extracted_any = True
            if method_used == "None":
                method_used = "Deep Firmware Carver"
            log(f"[SUCCESS] Tier 4 Carved {len(carved_files)} raw SPI/UEFI firmware image(s)!")

        # -------------------------------------------------------------
        # TIER 5: Output Classification & Audit
        # -------------------------------------------------------------
        classified = cls.classify_extracted_files(output_dir)

        # If main bios was not found yet, search for nested containers (CAB, SFX, etc.)
        if not classified["main_bios"]:
            cls._recursive_sub_extract(output_dir, log)
            classified = cls.classify_extracted_files(output_dir)

        total_files = len(classified["all_files"])
        if total_files > 0:
            extracted_any = True

        log("-" * 60)
        log(f"[SUMMARY] Extraction status: {'SUCCESS' if extracted_any else 'NO BIOS DETECTED'}")
        log(f"[METHOD] Engine used: {method_used}")
        log(f"[TOTAL FILES] {total_files} file(s) found in output directory")
        if classified["main_bios"]:
            for b in classified["main_bios"]:
                log(f"  [*] Main BIOS Candidate: {os.path.basename(b)} ({os.path.getsize(b):,} bytes)")
        if classified["ec_firmware"]:
            for ec in classified["ec_firmware"]:
                log(f"  [EC] EC/KBC Candidate: {os.path.basename(ec)} ({os.path.getsize(ec):,} bytes)")
        if classified["me_regions"]:
            for me in classified["me_regions"]:
                log(f"  [ME] ME/CSME Candidate: {os.path.basename(me)} ({os.path.getsize(me):,} bytes)")
        log("-" * 60)

        return {
            "success": extracted_any,
            "method": method_used,
            "output_dir": output_dir,
            "classified": classified,
            "total_files": total_files
        }

    # -----------------------------------------------------------------
    # TIER 1 Implementation
    # -----------------------------------------------------------------
    @classmethod
    def _try_tier1_vendor_extract(cls, input_file: str, output_dir: str, log: Callable[[str], None]) -> Tuple[bool, str]:
        if not HAS_BIOSUTILITIES:
            log("[TIER 1] biosutilities library not loaded.")
            return False, ""

        utilities = [
            DellPfsExtract, InsydeIfdExtract, AmiPfatExtract, AmiUcpExtract,
            PhoenixTdkExtract, AppleEfiPkgExtract, AppleEfiPbzxExtract,
            AppleEfiIm4pSplit, AppleEfiIdentify, FujitsuSfxExtract,
            FujitsuUpcExtract, PanasonicBiosExtract, ToshibaComExtract,
            VaioPackageExtract, PortwellEfiExtract, AwardBiosExtract
        ]

        class LogCaptureStream(io.TextIOBase):
            def write(self, s):
                st = s.strip()
                if st:
                    log(f"  [VENDOR] {st}")
                return len(s)

        for util_cls in utilities:
            try:
                util = util_cls(input_object=input_file, extract_path=output_dir, padding=0)
                if not util.check_format():
                    continue

                fmt_title = getattr(util, 'TITLE', util_cls.__name__)
                log(f"[TIER 1] Matched vendor format: {fmt_title}")

                with contextlib.redirect_stdout(LogCaptureStream()):
                    success = util.parse_format()

                if success:
                    return True, fmt_title
            except Exception as e:
                # Utility crashed or format mismatch, continue to next
                continue

        return False, ""

    # -----------------------------------------------------------------
    # TIER 2 Implementation (Capsule Stripper)
    # -----------------------------------------------------------------
    @classmethod
    def _try_tier2_capsule_strip(cls, input_file: str, output_dir: str, log: Callable[[str], None]) -> Tuple[bool, str]:
        """Checks if file is a .CAP with 2KB (0x800) or 4KB (0x1000) Aptio header, and strips it."""
        try:
            with open(input_file, "rb") as f:
                head = f.read(0x2000)

            # Common offsets where Flash Descriptor or UEFI FV begins
            for offset in [0x800, 0x1000]:
                if len(head) >= offset + 16:
                    candidate_magic = head[offset:offset+4]
                    if candidate_magic == cls.FD_MAGIC or head[offset+0x28:offset+0x2C] == cls.UEFI_FVH_MAGIC:
                        log(f"[TIER 2] Detected Capsule header of size 0x{offset:X} ({offset} bytes)")
                        # Read and write stripped payload
                        base = os.path.basename(input_file)
                        stem = os.path.splitext(base)[0]
                        out_path = os.path.join(output_dir, f"{stem}_stripped.bin")
                        with open(input_file, "rb") as src, open(out_path, "wb") as dst:
                            src.seek(offset)
                            shutil.copyfileobj(src, dst)
                        return True, out_path
        except Exception as e:
            log(f"[TIER 2] Capsule check exception: {e}")

        return False, ""

    # -----------------------------------------------------------------
    # TIER 3 Implementation (Installer & Container Decompression)
    # -----------------------------------------------------------------
    @classmethod
    def _try_tier3_installer_unpack(cls, input_file: str, output_dir: str, log: Callable[[str], None]) -> Tuple[bool, str]:
        # 1. Try InnoExtract (Modern Inno Setup 5.x / 6.x - Lenovo, Acer, HP frequent)
        innoextract = cls.get_innoextract_path()
        if innoextract:
            try:
                inno_dir = os.path.join(output_dir, "inno_extracted")
                os.makedirs(inno_dir, exist_ok=True)
                cmd = [innoextract, "-s", "-e", "-d", inno_dir, input_file]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
                if res.returncode == 0 and os.path.isdir(inno_dir) and os.listdir(inno_dir):
                    log("  [INNOEXTRACT] Inno Setup archive successfully unpacked!")
                    return True, "Inno Setup Extractor (InnoExtract)"
                else:
                    if res.stderr:
                        log(f"  [INNOEXTRACT] Error: {res.stderr.strip()}")
            except Exception as e:
                log(f"  [INNOEXTRACT] Debug: {e}")

        # 2. Try InnoUnp fallback (Older Inno Setup archives)
        innounp = cls.get_innounp_path()
        if innounp:
            try:
                inno_dir = os.path.join(output_dir, "inno_extracted")
                cmd = [innounp, "-x", f"-d{inno_dir}", "-y", input_file]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if res.returncode == 0 and os.path.isdir(inno_dir) and os.listdir(inno_dir):
                    log("  [INNO] Inno Setup archive successfully unpacked via innounp!")
                    return True, "Inno Setup Extractor (InnoUnp)"
            except Exception:
                pass

        # 3. Try 7-Zip (Comprehensive container unpacker)
        p7z = cls.get_7z_path()
        if p7z:
            try:
                temp_7z_dir = os.path.join(output_dir, "7z_extracted")
                cmd = [p7z, "x", input_file, f"-o{temp_7z_dir}", "-y"]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
                if res.returncode == 0 and os.path.isdir(temp_7z_dir):
                    files = os.listdir(temp_7z_dir)
                    # Filter out useless PE section dumps like .text, .rdata, .data, .rsrc
                    pe_sections = {'.text', '.data', '.rdata', '.rsrc', '.bss', '.edata', '.idata', '.tls', '.didata', '.itext', 'CERTIFICATE', '[0]'}
                    meaningful_files = [f for f in files if f not in pe_sections]
                    if meaningful_files:
                        # Move files up to output_dir
                        for item in files:
                            src_p = os.path.join(temp_7z_dir, item)
                            dst_p = os.path.join(output_dir, item)
                            if not os.path.exists(dst_p):
                                shutil.move(src_p, dst_p)
                        shutil.rmtree(temp_7z_dir, ignore_errors=True)
                        log("  [7-ZIP] Container unpack completed successfully.")
                        return True, "7-Zip Multi-Archive Engine"
                    else:
                        shutil.rmtree(temp_7z_dir, ignore_errors=True)
            except Exception as e:
                log(f"  [7-ZIP] Execution error: {e}")

        # 4. Native Python zipfile fallback
        import zipfile
        try:
            if zipfile.is_zipfile(input_file):
                with zipfile.ZipFile(input_file, 'r') as zf:
                    zf.extractall(output_dir)
                log("  [ZIP] Extracted standard ZIP archive.")
                return True, "Standard ZIP Unpacker"
        except Exception:
            pass

        return False, ""

    # -----------------------------------------------------------------
    # TIER 4 Implementation (Deep Firmware Carver)
    # -----------------------------------------------------------------
    @classmethod
    def _try_tier4_deep_carve(cls, input_file: str, output_dir: str, log: Callable[[str], None]) -> List[str]:
        """
        Scans binary for embedded Flash Descriptors and UEFI Firmware Volumes,
        calculates legitimate component sizes, and carves raw ROMs.
        """
        carved = []
        try:
            with open(input_file, "rb") as f:
                data = f.read()

            file_len = len(data)
            if file_len < 0x100000: # Smaller than 1MB, unlikely full BIOS
                return carved

            # Search for Intel Flash Descriptor magic: 5A A5 F0 0F
            fd_indices = [m.start() for m in re.finditer(re.escape(cls.FD_MAGIC), data)]
            for idx in fd_indices:
                # Verify that this offset contains a plausible Flash Descriptor Map
                if idx + 0x20 <= file_len:
                    # FlMAP0 is at offset 0x14
                    flmap0_raw = data[idx+0x14:idx+0x18]
                    if len(flmap0_raw) == 4:
                        flmap0 = struct.unpack("<I", flmap0_raw)[0]
                        # Component Base = ((flmap0 >> 16) & 0xFF) << 4
                        comp_base = ((flmap0 >> 16) & 0xFF) << 4
                        if idx + comp_base + 4 <= file_len:
                            # Read Component 0 & 1 density from FLCOMP register
                            flcomp = struct.unpack("<I", data[idx+comp_base:idx+comp_base+4])[0]
                            density_codes = [flcomp & 0x0F, (flcomp >> 4) & 0x0F]
                            num_components = ((flmap0 >> 8) & 0x03) + 1
                            
                            # Standard Intel Density Table (0=512KB, 1=1MB, 2=2MB, 3=4MB, 4=8MB, 5=16MB, 6=32MB, 7=64MB)
                            density_map = {
                                0: 512 * 1024,
                                1: 1024 * 1024,
                                2: 2 * 1024 * 1024,
                                3: 4 * 1024 * 1024,
                                4: 8 * 1024 * 1024,
                                5: 16 * 1024 * 1024,
                                6: 32 * 1024 * 1024,
                                7: 64 * 1024 * 1024
                            }
                            
                            total_rom_size = density_map.get(density_codes[0], 0)
                            if num_components > 1:
                                total_rom_size += density_map.get(density_codes[1], 0)
                            
                            if total_rom_size in (4*1024*1024, 8*1024*1024, 16*1024*1024, 32*1024*1024, 64*1024*1024):
                                if idx + total_rom_size <= file_len:
                                    out_name = f"carved_SPI_BIOS_{total_rom_size // (1024*1024)}MB_at_0x{idx:X}.bin"
                                    out_path = os.path.join(output_dir, out_name)
                                    if not os.path.exists(out_path):
                                        with open(out_path, "wb") as out_f:
                                            out_f.write(data[idx:idx+total_rom_size])
                                        log(f"  [CARVER] Identified & carved valid {total_rom_size // (1024*1024)}MB SPI ROM from offset 0x{idx:X}!")
                                        carved.append(out_path)

            # Search for Insyde Firmware markers: $_IFLASH_$ or $IBIOS$
            insyde_markers = [b"$_IFLASH_$", b"$IBIOS$", b"$_H2O_BIOS_$"]
            for marker in insyde_markers:
                m_indices = [m.start() for m in re.finditer(re.escape(marker), data)]
                for m_idx in m_indices:
                    log(f"  [CARVER] Detected Insyde marker '{marker.decode('latin1')}' at offset 0x{m_idx:X}")

        except Exception as e:
            log(f"  [CARVER] Deep carve error: {e}")

        return carved

    # -----------------------------------------------------------------
    # Universal OEM Protected SFX Live Unpacker (All Brands)
    # -----------------------------------------------------------------
    @classmethod
    def _is_protected_sfx(cls, file_path: str) -> bool:
        """
        Detects whether an executable or payload file is an OEM protected 7z SFX container
        (used by HP, Acer, Lenovo, Toshiba, Clevo, Asus, etc.) with custom/locked stubs.
        """
        try:
            if not os.path.isfile(file_path):
                return False
            sz = os.path.getsize(file_path)
            if sz < 1024 * 1024 or sz > 500 * 1024 * 1024:
                return False

            with open(file_path, "rb") as f:
                head = f.read(2 * 1024 * 1024)

            # Heuristic 1: Any 7z SFX configuration block (used by OEM flashers of all brands)
            if b";!@Install@!" in head:
                return True

            # Heuristic 2: OEM flasher executable stubs
            lower_head = head.lower()
            if b"hpflashwin" in lower_head or b"h2offt" in lower_head or b"isflash" in lower_head or b"afuwin" in lower_head or b"winflash" in lower_head:
                return True

            # Heuristic 3: Check file tail or overlay for ;!@Install@!
            if sz > 4 * 1024 * 1024:
                with open(file_path, "rb") as f:
                    f.seek(max(0, sz - 1024 * 1024))
                    tail = f.read()
                if b";!@Install@!" in tail:
                    return True

        except Exception:
            pass
        return False

    _is_insyde_sfx = _is_protected_sfx

    @classmethod
    def _extract_protected_sfx_live(cls, exe_path: str, dest_dir: str, log: Callable[[str], None]) -> Tuple[bool, List[str]]:
        """
        Universal live extractor for OEM protected SFX packages across all brands (HP, Acer, Lenovo, Asus, etc.).
        Patches requireAdministrator to asInvoker in-memory, spawns unpacker,
        intercepts the unpacked temporary working directory (via cwd, child process paths, or temp scan),
        copies all firmware files, and cleanly terminates the flasher GUI before any window displays.
        """
        proc = None
        temp_runner = None
        found_cwd = None
        extracted_bios_files = []

        try:
            with open(exe_path, "rb") as f:
                data = bytearray(f.read())

            # Universal UAC bypass: Patch manifest requireAdministrator -> asInvoker preserving exact byte count
            req_admin = b'level="requireAdministrator"'
            needed = len(req_admin) - len(b'level="asInvoker"')
            as_invoker = b'level="asInvoker"' + (b' ' * needed)
            if req_admin in data:
                data = data.replace(req_admin, as_invoker)
                log("  [PROTECTED SFX] Bypassed UAC requirement via PE manifest patch.")

            temp_runner = os.path.join(dest_dir, f"_oem_unpack_{int(time.time())}.exe")
            with open(temp_runner, "wb") as f:
                f.write(data)

            log("  [PROTECTED SFX] Invoking self-extracting payload engine...")
            proc = subprocess.Popen([temp_runner], cwd=dest_dir)

            user_temp = os.environ.get("TEMP", os.path.expanduser("~\\AppData\\Local\\Temp"))
            win_temp = r"C:\Windows\Temp"

            # Poll for unpacker payload location for up to 15 seconds
            start_time = time.time()
            while time.time() - start_time < 15:
                time.sleep(0.4)
                if not psutil or not proc:
                    continue

                try:
                    p_obj = psutil.Process(proc.pid)
                    # 1. Check parent working directory
                    c = p_obj.cwd()
                    if c and c.lower() != dest_dir.lower() and os.path.isdir(c):
                        found_cwd = c
                        break

                    # 2. Check child processes (flasher utility launched by SFX)
                    children = p_obj.children(recursive=True)
                    if children:
                        for ch in children:
                            try:
                                ch_exe = ch.exe()
                                if ch_exe and os.path.isfile(ch_exe):
                                    ch_dir = os.path.dirname(ch_exe)
                                    if ch_dir and ch_dir.lower() != dest_dir.lower() and os.path.isdir(ch_dir):
                                        found_cwd = ch_dir
                                        break
                                ch_cwd = ch.cwd()
                                if ch_cwd and ch_cwd.lower() != dest_dir.lower() and os.path.isdir(ch_cwd):
                                    found_cwd = ch_cwd
                                    break
                            except Exception:
                                pass
                    if found_cwd:
                        break

                    # 3. Check temp directories for newly created 7zS or flasher folders with firmware
                    for t_base in [user_temp, win_temp]:
                        if os.path.isdir(t_base):
                            try:
                                for entry in os.listdir(t_base):
                                    entry_lower = entry.lower()
                                    if (entry_lower.startswith("7zs") or "flash" in entry_lower) and ".tmp" in entry_lower:
                                        full_t = os.path.join(t_base, entry)
                                        if os.path.isdir(full_t):
                                            try:
                                                if os.path.getmtime(full_t) >= start_time - 2:
                                                    flist = os.listdir(full_t)
                                                    if any(x.lower().endswith((".bin", ".fd", ".rom", ".cap", ".wph")) for x in flist):
                                                        found_cwd = full_t
                                                        break
                                            except Exception:
                                                pass
                            except Exception:
                                pass
                    if found_cwd:
                        break

                except Exception:
                    break

            if found_cwd and os.path.isdir(found_cwd):
                log(f"  [PROTECTED SFX] Intercepted unpacked firmware directory: {found_cwd}")
                time.sleep(0.5)  # allow background file writes to complete
                try:
                    for item in os.listdir(found_cwd):
                        src_path = os.path.join(found_cwd, item)
                        dst_path = os.path.join(dest_dir, item)
                        if os.path.isfile(src_path):
                            shutil.copy2(src_path, dst_path)
                            if item.lower().endswith((".bin", ".fd", ".rom", ".cap", ".wph", ".hdr", ".fv")):
                                extracted_bios_files.append(dst_path)
                        elif os.path.isdir(src_path):
                            shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
                except Exception as e:
                    log(f"  [WARN] Partial copy warning: {e}")

                log(f"  [PROTECTED SFX] Successfully extracted {len(extracted_bios_files)} BIOS binary file(s)!")
                return True, extracted_bios_files
            else:
                log("  [WARN] SFX payload interception timed out.")
                return False, []

        except Exception as e:
            log(f"  [ERROR] Protected SFX extraction exception: {e}")
            return False, []

        finally:
            # Terminate unpacker process tree cleanly
            try:
                if psutil and proc:
                    p_obj = psutil.Process(proc.pid)
                    for child in p_obj.children(recursive=True):
                        child.kill()
                    p_obj.kill()
                elif proc:
                    proc.terminate()
            except Exception:
                pass

            # Clean up temp runner
            try:
                if temp_runner and os.path.exists(temp_runner):
                    os.remove(temp_runner)
            except Exception:
                pass

            # Clean up temporary unpacked folder
            if found_cwd and os.path.isdir(found_cwd):
                try:
                    shutil.rmtree(found_cwd, ignore_errors=True)
                except Exception:
                    pass

    _extract_insyde_sfx_live = _extract_protected_sfx_live

    # -----------------------------------------------------------------
    # Recursive Sub-Extraction for nested containers
    # -----------------------------------------------------------------
    @classmethod
    def _recursive_sub_extract(cls, root_dir: str, log: Callable[[str], None], depth: int = 0):
        """
        If 7-Zip or installer extracted nested CAB, SFX, ZIP, or embedded .exe
        (common in Lenovo, Acer, HP flasher utilities), recursively unpack and inspect them.
        """
        if depth > 2:
            return

        nested_archives = (".cab", ".zip", ".msi", ".tar")
        p7z = cls.get_7z_path()

        for root, dirs, files in os.walk(root_dir):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                nested_path = os.path.join(root, file)

                # 1. Nested Archives (CAB, ZIP, MSI, TAR)
                if ext in nested_archives and p7z:
                    nested_out = os.path.join(root, f"{os.path.splitext(file)[0]}_unpacked")
                    if not os.path.isdir(nested_out):
                        try:
                            cmd = [p7z, "x", nested_path, f"-o{nested_out}", "-y"]
                            subprocess.run(cmd, capture_output=True, timeout=30)
                            if os.path.isdir(nested_out) and os.listdir(nested_out):
                                log(f"  [NESTED ARCHIVE] Unpacked: {file}")
                                cls._recursive_sub_extract(nested_out, log, depth + 1)
                        except Exception:
                            pass

                # 2. Nested Flasher Executables (e.g. InsydeFlash.exe, H2OFFT, Lenovo/Acer installers)
                elif ext == ".exe" and depth < 2:
                    try:
                        sz = os.path.getsize(nested_path)
                    except OSError:
                        sz = 0

                    if sz > 2 * 1024 * 1024:
                        nested_out = os.path.join(root, f"{os.path.splitext(file)[0]}_extracted")
                        if not os.path.isdir(nested_out):
                            # Check first if it is an OEM protected SFX package (HP, Acer, Lenovo, Asus, etc.)
                            if cls._is_protected_sfx(nested_path):
                                log(f"  [PROTECTED SFX] Detected OEM protected SFX: {file}")
                                os.makedirs(nested_out, exist_ok=True)
                                sfx_ok, sfx_files = cls._extract_protected_sfx_live(nested_path, nested_out, log)
                                if sfx_ok and sfx_files:
                                    # Copy BIOS files up to root as well for immediate visibility
                                    for bf in sfx_files:
                                        try:
                                            shutil.copy2(bf, os.path.join(root, os.path.basename(bf)))
                                        except Exception:
                                            pass
                                    continue

                            unpacked_ok = False
                            if p7z:
                                try:
                                    cmd = [p7z, "x", nested_path, f"-o{nested_out}", "-y"]
                                    res = subprocess.run(cmd, capture_output=True, timeout=30)
                                    if res.returncode == 0 and os.path.isdir(nested_out) and os.listdir(nested_out):
                                        # Check if 7-zip only extracted raw PE sections/overlay [0] without BIOS
                                        inner_items = os.listdir(nested_out)
                                        has_firmware = any(x.lower().endswith((".bin", ".fd", ".rom", ".cap", ".wph")) for x in inner_items)
                                        if not has_firmware and ("[0]" in inner_items or any(cls._is_protected_sfx(os.path.join(nested_out, ii)) for ii in inner_items)):
                                            log(f"  [PROTECTED SFX] Detected locked payload in {file}; invoking universal live unpacker...")
                                            sfx_ok, sfx_files = cls._extract_protected_sfx_live(nested_path, nested_out, log)
                                            if sfx_ok and sfx_files:
                                                for bf in sfx_files:
                                                    try:
                                                        shutil.copy2(bf, os.path.join(root, os.path.basename(bf)))
                                                    except Exception:
                                                        pass
                                                continue

                                        log(f"  [NESTED EXE UNPACK] Extracted embedded payload from {file}")
                                        unpacked_ok = True
                                        cls._recursive_sub_extract(nested_out, log, depth + 1)
                                except Exception:
                                    pass

                            if not unpacked_ok:
                                try:
                                    carved = cls._try_tier4_deep_carve(nested_path, root, log)
                                    if carved:
                                        log(f"  [NESTED CARVE] Carved {len(carved)} ROM(s) from embedded {file}")
                                except Exception:
                                    pass

    # -----------------------------------------------------------------
    # Output Classification
    # -----------------------------------------------------------------
    @classmethod
    def classify_extracted_files(cls, target_dir: str) -> Dict[str, List[str]]:
        """Scans extracted directory and organizes files into categorized lists."""
        result = {
            "main_bios": [],
            "ec_firmware": [],
            "me_regions": [],
            "all_files": []
        }

        if not os.path.isdir(target_dir):
            return result

        bios_exts = {".bin", ".rom", ".fd", ".cap", ".wph", ".fl1", ".fl2", ".fl3", ".img", ".bio", ".fv", ".bios"}
        ec_sizes = {64*1024, 128*1024, 256*1024, 512*1024, 1024*1024, 2*1024*1024}
        bios_sizes = {4*1024*1024, 8*1024*1024, 16*1024*1024, 22*1024*1024, 24*1024*1024, 32*1024*1024, 64*1024*1024}

        for root, _, files in os.walk(target_dir):
            for f in files:
                full_path = os.path.join(root, f)
                result["all_files"].append(full_path)
                ext = os.path.splitext(f)[1].lower()
                name_lower = f.lower()
                
                try:
                    fsize = os.path.getsize(full_path)
                except OSError:
                    continue

                # Check for EC Firmware (including Lenovo .FL2 / .FL3)
                if ext in {".fl2", ".fl3"} or (("ec" in name_lower or "kbc" in name_lower or "ite" in name_lower or "ene" in name_lower) and fsize in ec_sizes):
                    result["ec_firmware"].append(full_path)
                    continue

                # Check for Intel ME / CSME Region
                if ("me" in name_lower or "csme" in name_lower or "txei" in name_lower) and ext in bios_exts:
                    result["me_regions"].append(full_path)
                    continue

                # Check for Main System BIOS (including Lenovo .FL1)
                if ext == ".fl1" or ext in bios_exts:
                    if fsize in bios_sizes or fsize > 2 * 1024 * 1024:
                        result["main_bios"].append(full_path)
                    elif "bios" in name_lower or "isflash" in name_lower or "main" in name_lower:
                        result["main_bios"].append(full_path)

        # Sort main bios by size descending (largest usually full image)
        result["main_bios"].sort(key=lambda p: os.path.getsize(p) if os.path.exists(p) else 0, reverse=True)
        return result
