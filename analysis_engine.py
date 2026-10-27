from path_utils import get_script_cmd, get_subprocess_env
import os
import sys
import json
import subprocess
import hashlib
import zlib
import tempfile
import shutil


class FirmwareAnalyzer:
    """
    MEAnalyzer Wrapper Engine.
    Runs MEAnalyzer (MEA.py) with -json -dfpt flags and parses
    the output into a structured dictionary for the UI.
    """

    # Key names MEAnalyzer uses in JSON for various firmware types
    MEA_SECTIONS = [
        "Management Engine",
        "Power Management Controller",
        "Platform Controller Hub Configuration",
        "USB Type C Physical",
        "Graphics Option ROM",
        "Trusted Execution Engine",
        "Server Platform Services",
        "Graphics System Controller",
    ]

    def __init__(self, bios_path, mea_path):
        """
        :param bios_path: Full path to the BIOS/firmware file to analyze.
        :param mea_path:  Full path to MEA.py script.
        """
        self.bios_path = bios_path
        self.mea_path = mea_path

        self.general_info = {}
        self.firmware_sections = {}   # dict of {section_name: [list of dicts]}
        self.fpt_table = []
        self.bpdt_table = []
        self.messages = []            # raw MEA messages (Warnings / Errors)
        self.health_score = 100
        self.repair_suggestions = []
        self.mea_available = False

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def run_analysis(self):
        """Runs all stages and returns a single structured dict."""
        self._analyze_general()

        if os.path.isfile(self.mea_path):
            self.mea_available = True
            self._run_mea()
        else:
            self.messages.append(
                f"[WARNING] MEAnalyzer not found at: {self.mea_path}"
            )
            self.health_score -= 20
            self.repair_suggestions.append(
                "Set the correct MEA.py path in Report Settings."
            )

        self._generate_health_report()

        return {
            "general": self.general_info,
            "firmware": self.firmware_sections,   # replaces old me/pmc split
            "fpt": self.fpt_table,
            "bpdt": self.bpdt_table,
            "messages": self.messages,
            "health": {
                "score": self.health_score,
                "suggestions": self.repair_suggestions,
            },
            "mea_available": self.mea_available,
        }

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _analyze_general(self):
        """Compute basic file-level info (size, hashes, descriptor check)."""
        try:
            size = os.path.getsize(self.bios_path)
            self.general_info["File Name"] = os.path.basename(self.bios_path)
            self.general_info["File Size"] = (
                f"{size:,} bytes  ({size / (1024 * 1024):.2f} MB)"
            )

            with open(self.bios_path, "rb") as fh:
                data = fh.read()

            self.general_info["SHA-256"] = hashlib.sha256(data).hexdigest().upper()
            self.general_info["CRC-32"] = f"0x{zlib.crc32(data) & 0xFFFFFFFF:08X}"

            # Intel Flash Descriptor magic: 5A A5 F0 0F at offset 0x10
            if len(data) >= 20 and data[0x10:0x14] == b"\x5A\xA5\xF0\x0F":
                self.general_info["Flash Descriptor"] = "Present (Valid)"
            else:
                self.general_info["Flash Descriptor"] = "Not Found / Not Intel SPI"

        except Exception as exc:
            self.general_info["Error"] = str(exc)

    def _run_mea(self):
        """Execute MEA.py and parse both JSON and table output."""
        temp_dir = tempfile.mkdtemp(prefix="bios_tool_mea_")
        try:
            # Use get_script_cmd so that when the app is frozen (PyInstaller),
            # we use the system 'python' instead of the compiled .exe
            cmd = get_script_cmd(self.mea_path) + [
                self.bios_path,
                "-skip",
                "-exit",
                "-duc",   # disable update check
                "-json",
                "-dfpt",
                "-out", temp_dir,
            ]

            # Build env: inject the bundled _deps folder next to MEA.py so that
            # crccheck / colorama / pltable are always available on any PC
            env = get_subprocess_env()
            mea_dir = os.path.dirname(self.mea_path)
            deps_dir = os.path.join(mea_dir, "_deps")
            if os.path.isdir(deps_dir):
                existing_pp = env.get("PYTHONPATH", "")
                env["PYTHONPATH"] = deps_dir + (os.pathsep + existing_pp if existing_pp else "")

            cf = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            result = subprocess.run(
                cmd,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                creationflags=cf,
                timeout=60,
                env=env
            )

            # Parse table output from stdout
            self._parse_tables(result.stdout)

            # Parse JSON file
            filename = os.path.basename(self.bios_path)
            json_path = os.path.join(temp_dir, f"{filename}.json")
            if os.path.isfile(json_path):
                self._parse_json(json_path)
            else:
                self.messages.append(
                    "[WARNING] MEAnalyzer produced no JSON. "
                    "File may be unsupported or truncated."
                )
                self.health_score -= 15

        except subprocess.TimeoutExpired:
            self.messages.append("[ERROR] MEAnalyzer timed out after 60 seconds.")
            self.health_score -= 15
        except Exception as exc:
            self.messages.append(f"[ERROR] MEA execution failed: {exc}")
            self.health_score -= 20
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _parse_json(self, json_path):
        """Parse MEA JSON output into self.firmware_sections."""
        try:
            with open(json_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)

            if not data:
                return

            # The top-level key is the full BIOS path
            root_key = next(iter(data))
            bios_data = data[root_key]

            # Pull each known firmware section
            for section in self.MEA_SECTIONS:
                entries = bios_data.get(section, [])
                if entries:
                    self.firmware_sections[section] = entries

            # Messages (warnings/errors from MEA)
            for msg in bios_data.get("Messages", []):
                self.messages.append(msg)
                if any(kw in msg.lower() for kw in ("error", "corrupt", "invalid", "warning")):
                    self.health_score -= 10

        except Exception as exc:
            self.messages.append(f"[ERROR] JSON parse failed: {exc}")

    def _parse_tables(self, stdout):
        """
        Parse the unicode table output of -dfpt into list-of-dicts.
        MEA uses box-drawing characters (╔, ║, ╚, ─, ╧, ╤, ╟, ╪).
        """
        current_table = None
        headers = []

        for raw_line in stdout.splitlines():
            line = raw_line.strip()

            # Detect section headers
            if "Flash Partition Table" in line and current_table is None:
                current_table = "FPT"
                headers = []
                continue
            if "Boot Partition Descriptor Table" in line and current_table != "FPT":
                current_table = "BPDT"
                headers = []
                continue
            # Table ends
            if line.startswith("╚") and current_table:
                current_table = None
                headers = []
                continue

            # Data rows start/end with ║
            if current_table and line.startswith("║") and line.endswith("║"):
                inner = line[1:-1]
                # Split on various box separators MEA uses
                parts = [p.strip() for p in inner.replace("┼", "│").replace("╪", "│").split("│")]

                if not headers:
                    # First row is header
                    headers = parts
                else:
                    if len(parts) == len(headers):
                        row = dict(zip(headers, parts))
                        if current_table == "FPT":
                            self.fpt_table.append(row)
                        elif current_table == "BPDT":
                            self.bpdt_table.append(row)

    def _generate_health_report(self):
        """Generate health score adjustments and repair suggestions."""
        me_entries = self.firmware_sections.get("Management Engine", [])

        if not me_entries:
            if self.mea_available:
                self.messages.append(
                    "[INFO] No Intel ME region detected. "
                    "This may be an ME-only extract or AMD/non-Intel firmware."
                )
        else:
            me = me_entries[0]
            self.messages.insert(0, f"[OK] Intel ME detected: {me.get('Family', '?')} v{me.get('Version', '?')}")

            if me.get("Production Ready", "Yes") == "No":
                self.messages.append("[WARNING] ME Firmware is Pre-Production!")
                self.health_score -= 5
                self.repair_suggestions.append(
                    "Replace ME firmware with a Production-Ready version."
                )

            if me.get("Release", "") == "ROM-Bypass":
                self.messages.append("[ERROR] ROM-Bypass detected — firmware is incomplete!")
                self.health_score -= 30
                self.repair_suggestions.append(
                    "Perform a full ME re-flash using a valid Production firmware."
                )

        if self.health_score >= 100 and not self.repair_suggestions:
            self.repair_suggestions.append(
                "Firmware appears structurally healthy. No automatic repair required."
            )

        self.health_score = max(0, self.health_score)
