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
from pathlib import Path
from typing import Callable, Optional, Dict, List, Tuple

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

    # External CLI helpers bundled with R1 BIOS TOOL
    _BIN_DIR = os.path.join(PROJECT_ROOT, "external", "UniExtract", "bin")
    _7Z_PATH = os.path.join(_BIN_DIR, "7z.exe")
    _INNOUNP_PATH = os.path.join(_BIN_DIR, "innounp.exe")

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

        # If files were extracted in subdirectories, flatten or search for nested containers
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
        # 1. Try Inno Setup (Lenovo, Acer, HP frequent)
        innounp = cls.get_innounp_path()
        if innounp:
            try:
                inno_dir = os.path.join(output_dir, "inno_extracted")
                cmd = [innounp, "-x", f"-d{inno_dir}", "-y", input_file]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if res.returncode == 0 and os.path.isdir(inno_dir) and os.listdir(inno_dir):
                    log("  [INNO] Inno Setup archive successfully unpacked!")
                    return True, "Inno Setup Extractor"
            except Exception:
                pass

        # 2. Try 7-Zip (Comprehensive container unpacker)
        p7z = cls.get_7z_path()
        if p7z:
            try:
                cmd = [p7z, "x", input_file, f"-o{output_dir}", "-y"]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
                if res.returncode == 0:
                    # Check if output has files
                    files = os.listdir(output_dir)
                    if files:
                        log("  [7-ZIP] Container unpack completed successfully.")
                        return True, "7-Zip Multi-Archive Engine"
            except Exception as e:
                log(f"  [7-ZIP] Execution error: {e}")

        # 3. Native Python zipfile fallback
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
                            unpacked_ok = False
                            if p7z:
                                try:
                                    cmd = [p7z, "x", nested_path, f"-o{nested_out}", "-y"]
                                    res = subprocess.run(cmd, capture_output=True, timeout=30)
                                    if res.returncode == 0 and os.path.isdir(nested_out) and os.listdir(nested_out):
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

        bios_exts = {".bin", ".rom", ".fd", ".cap", ".wph"}
        ec_sizes = {64*1024, 128*1024, 256*1024, 512*1024, 1024*1024, 2*1024*1024}
        bios_sizes = {4*1024*1024, 8*1024*1024, 16*1024*1024, 32*1024*1024, 64*1024*1024}

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

                # Check for EC Firmware
                if ("ec" in name_lower or "kbc" in name_lower or "ite" in name_lower or "ene" in name_lower) and fsize in ec_sizes:
                    result["ec_firmware"].append(full_path)
                    continue

                # Check for Intel ME / CSME Region
                if ("me" in name_lower or "csme" in name_lower or "txei" in name_lower) and ext in bios_exts:
                    result["me_regions"].append(full_path)
                    continue

                # Check for Main System BIOS
                if ext in bios_exts:
                    if fsize in bios_sizes or fsize > 2 * 1024 * 1024:
                        result["main_bios"].append(full_path)
                    elif "bios" in name_lower or "isflash" in name_lower or "main" in name_lower:
                        result["main_bios"].append(full_path)

        # Sort main bios by size descending (largest usually full image)
        result["main_bios"].sort(key=lambda p: os.path.getsize(p) if os.path.exists(p) else 0, reverse=True)
        return result
