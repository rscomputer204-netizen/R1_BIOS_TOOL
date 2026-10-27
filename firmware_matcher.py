import os
import re
from pathlib import Path

class FirmwareMatcher:
    def __init__(self, base_dir):
        self.base_dir = Path(base_dir)
        self.repos = {
            "ME": self.base_dir / "Firmware_Repository" / "ME_Region",
            "PMC": self.base_dir / "Firmware_Repository" / "PMC_Region",
            "PCHC": self.base_dir / "Firmware_Repository" / "PCHC_Region",
            "PHY": self.base_dir / "Firmware_Repository" / "PHY_Region"
        }

    def _extract_version(self, name):
        # Matches patterns like 15.0.35.1952
        match = re.search(r"(\d+\.\d+\.\d+\.\d+)", name)
        return match.group(1) if match else None

    def find_best_match(self, fw_type, target_version, target_sku=None):
        """
        Finds the best matching firmware file in the local repository.
        """
        repo_path = self.repos.get(fw_type)
        if not repo_path or not repo_path.exists():
            return None

        best_file = None
        
        # Simple matching: look for the exact version or highest version in the same major range
        target_major = target_version.split('.')[0] if '.' in target_version else target_version
        
        for file in os.listdir(repo_path):
            if not file.lower().endswith('.bin'):
                continue
            
            file_ver = self._extract_version(file)
            if not file_ver:
                continue
                
            # Strict match attempt
            if file_ver == target_version:
                if self._match_sku(target_sku, file):
                    return str(repo_path / file)
            
            # Sub-family match attempt
            if file_ver.startswith(target_major):
                if self._match_sku(target_sku, file):
                    if not best_file:
                        best_file = str(repo_path / file)
                    else:
                        best_ver = self._extract_version(os.path.basename(best_file))
                        if best_ver and file_ver > best_ver:
                            best_file = str(repo_path / file)
                        
        return best_file

    def get_repair_set(self, mea_metadata):
        """
        Returns a dictionary of suggested firmware files for all regions.
        """
        version = mea_metadata.get("version")
        sku = mea_metadata.get("sku")
        
        if not version:
            return {}
            
        results = {
            "ME": self.find_best_match("ME", version, sku),
            "PMC": self.find_best_match("PMC", version, sku),
            "PCHC": self.find_best_match("PCHC", version, sku),
            "PHY": self.find_best_match("PHY", version, sku)
        }
        
        return {k: v for k, v in results.items() if v}

    def _match_sku(self, target_sku, name):
        """Helper to check if SKU keywords exist in file/folder name."""
        if not target_sku or not name:
            return True # Default to match if unknown
            
        ts = target_sku.lower()
        nm = name.lower()
        
        # 1. Family Check (Strict)
        if "corporate" in ts:
            if not ("cor" in nm or "extr-y" in nm or "prd_rgn" in nm): return False
            if "con" in nm and "cor" not in nm: return False # Extra safety against CON
        elif "consumer" in ts:
            if not ("con" in nm): return False
            if "cor" in nm: return False # Extra safety against COR

        # 2. Suffix Check (LP/H/V)
        if " lp" in ts and not ("lp" in nm): return False
        if " h" in ts and not (" h" in nm or "_h" in nm): return False
        if " v" in ts and not (" v" in nm or "_v" in nm): return False
                
        return True
