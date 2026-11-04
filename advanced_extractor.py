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
        Attempts to extract a file using the Native R1 5-Tier Universal BIOS Extractor Engine.
        """
        if not os.path.exists(file_path):
            if terminal_callback:
                terminal_callback("[ERROR] File not found.")
            return False

        try:
            from R1_Universal_Extractor.r1_extractor_core import R1ExtractorCore
            res = R1ExtractorCore.extract(file_path, output_dir, logger=terminal_callback)
            return bool(res.get("success", False))
        except Exception as e:
            if terminal_callback:
                terminal_callback(f"[ERROR] Native Universal Extractor error: {e}")
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
