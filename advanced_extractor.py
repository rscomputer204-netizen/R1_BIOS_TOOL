import os
import sys
import io
import contextlib
import threading
import subprocess
from typing import Final
from biosutilities.common.templates import BIOSUtility
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

class AdvancedExtractor:
    """
    Wrapper for BIOSUtilities to provide universal extraction capabilities.
    """
    
    UTILITIES: Final[list[type[BIOSUtility]]] = [
        AppleEfiPkgExtract, AmiUcpExtract, AmiPfatExtract, InsydeIfdExtract, 
        DellPfsExtract, PhoenixTdkExtract, PanasonicBiosExtract, 
        VaioPackageExtract, PortwellEfiExtract, ToshibaComExtract, 
        FujitsuSfxExtract, FujitsuUpcExtract, AwardBiosExtract, 
        AppleEfiPbzxExtract, AppleEfiIm4pSplit, AppleEfiIdentify
    ]

    @staticmethod
    def run_universal_extract(file_path: str, output_dir: str, terminal_callback):
        """
        Attempts to extract a file using all available BIOSUtilities.
        """
        if not os.path.exists(file_path):
            if terminal_callback:
                terminal_callback("[ERROR] File not found.")
            return False

        base_name = os.path.basename(file_path)
        safe_name = os.path.splitext(base_name)[0]
        extraction_path = os.path.join(output_dir, f"{safe_name}_extracted")
        
        if terminal_callback:
            terminal_callback(f"[INFO] Initializing Advanced Extraction for: {base_name}")
            terminal_callback(f"[INFO] Target Directory: {extraction_path}")

        found_format = False
        
        # We need to capture the output of BIOSUtilities which uses print()
        class TerminalStream(io.TextIOBase):
            def __init__(self, callback):
                self.callback = callback
            def write(self, s):
                if s.strip():
                    self.callback(f"[ADVANCED] {s.strip()}")
                return len(s)

        # Iterate through utilities
        for utility_class in AdvancedExtractor.UTILITIES:
            try:
                # Instantiate utility
                # Note: padding is set to 0 for GUI use
                utility = utility_class(
                    input_object=file_path, 
                    extract_path=extraction_path, 
                    padding=0
                )

                # Check if format is supported by this utility
                if not utility.check_format():
                    continue

                found_format = True
                if terminal_callback:
                    terminal_callback(f"[SUCCESS] Detected Format: {utility.TITLE}")
                    terminal_callback("[INFO] Starting extraction process...")

                # Redirect stdout to capture internal logs from the library
                with contextlib.redirect_stdout(TerminalStream(terminal_callback)):
                    is_parsed = utility.parse_format()
                
                if is_parsed:
                    if terminal_callback:
                        terminal_callback(f"[SUCCESS] Extraction completed successfully: {extraction_path}")
                    return True
                else:
                    if terminal_callback:
                        terminal_callback("[ERROR] Extraction failed during parsing.")
                    return False
                    
            except Exception as e:
                if terminal_callback:
                    terminal_callback(f"[ERROR] Utility {utility_class.__name__} crashed: {str(e)}")
                continue

        if not found_format:
            if terminal_callback:
                terminal_callback("[INFO] No advanced BIOS format detected. Attempting Universal Archive Unpack (7-Zip)...")
            
            # 7-Zip Fallback
            if AdvancedExtractor.run_7z_fallback(file_path, extraction_path, terminal_callback):
                return True

            if terminal_callback:
                terminal_callback("[WARNING] Universal Unpack failed or no recognizable BIOS files found inside.")
            return False
            
        return False

    @staticmethod
    def run_7z_fallback(file_path: str, extraction_path: str, terminal_callback):
        """Attempts to unpack the file using 7-Zip and looks for bios targets inside."""
        try:
            # Ensure directory exists
            os.makedirs(extraction_path, exist_ok=True)
            
            # Execute 7z
            # -y: yes to all, -o: output dir
            cmd = ["7z", "x", file_path, f"-o{extraction_path}", "-y"]
            
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                if terminal_callback:
                    terminal_callback("[SUCCESS] 7-Zip Unpack Successful.")
                
                # Scan extracted files for BIOS-like extensions
                found_files = []
                bios_extensions = {".bin", ".fd", ".rom", ".cap", ".wph"}
                
                for root, _, files in os.walk(extraction_path):
                    for f in files:
                        if os.path.splitext(f)[1].lower() in bios_extensions:
                            found_files.append(f)
                
                if found_files:
                    if terminal_callback:
                        terminal_callback(f"[INFO] Found {len(found_files)} potential BIOS image(s) inside:")
                        for bf in found_files:
                            terminal_callback(f"  -> {bf}")
                    return True
                else:
                    if terminal_callback:
                        terminal_callback("[WARNING] Archive extracted but no BIOS images (.bin, .fd, .rom) were found inside.")
                    return False
            else:
                return False
                
        except Exception as e:
            if terminal_callback:
                terminal_callback(f"[ERROR] 7-Zip execution failed: {str(e)}")
            return False
