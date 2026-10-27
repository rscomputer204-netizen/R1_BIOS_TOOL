"""
R1 BIOS Tool - Hardware License Guard
=======================================
Programmer device (FT232H) must be connected for the software to run.
FTDI FT232H: VID=0403, PID=6014

This module is checked at:
  1. Startup (hard check - won't launch without device)
  2. Periodically every 30 seconds (soft check - warns if disconnected mid-session)
"""

import subprocess
import threading


# ─── Device Identity ──────────────────────────────────────────────────────────
PROGRAMMER_VID = "VID_0403"   # FTDI
PROGRAMMER_PID = "PID_6014"   # FT232H
PROGRAMMER_NAME = "R1 BIOS Programmer (FT232H)"

# ─── Check interval (seconds) for background monitoring ──────────────────────
CHECK_INTERVAL_SECONDS = 30


def is_programmer_connected() -> bool:
    """
    Returns True if the FT232H programmer is detected on any USB port.
    Fast: uses WMIC, no driver install required.
    """
    try:
        result = subprocess.run(
            ['wmic', 'path', 'Win32_PnPEntity', 'get', 'DeviceID'],
            capture_output=True, timeout=6,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
        )
        output = result.stdout.decode('utf-8', errors='ignore').upper()
        return (PROGRAMMER_VID in output) and (PROGRAMMER_PID in output)
    except Exception:
        # If detection fails (e.g. wmic not available), fail CLOSED (deny access)
        return False


def get_programmer_info() -> dict:
    """
    Returns detailed info about the connected programmer device.
    """
    try:
        result = subprocess.run(
            ['wmic', 'path', 'Win32_PnPEntity', 'get', 'DeviceID,Name,Status'],
            capture_output=True, timeout=6,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
        )
        output_raw = result.stdout.decode('utf-8', errors='ignore')
        output_up  = output_raw.upper()

        if (PROGRAMMER_VID in output_up) and (PROGRAMMER_PID in output_up):
            for line in output_raw.splitlines():
                if "0403" in line.upper() and "6014" in line.upper():
                    parts = line.strip().split()
                    return {
                        "connected": True,
                        "device_id": parts[0] if parts else "Unknown",
                        "vid": "0403",
                        "pid": "6014",
                        "name": PROGRAMMER_NAME,
                    }
        return {"connected": False}
    except Exception:
        return {"connected": False}


class ProgrammerGuard:
    """
    Hardware license guard.
    - startup_check(): Call once at launch. Returns True = OK, False = deny.
    - start_background_monitor(callback): Monitors every N seconds.
      callback(connected: bool) is called when status changes.
    """

    def __init__(self):
        self._last_state = None
        self._monitor_thread = None
        self._stop_event = threading.Event()

    def startup_check(self) -> bool:
        """Hard check at startup. Returns True if programmer is connected."""
        return is_programmer_connected()

    def start_background_monitor(self, on_change_callback):
        """
        Starts a background thread that monitors the programmer connection.
        on_change_callback(connected: bool) is called whenever state changes.
        """
        self._stop_event.clear()
        self._last_state = is_programmer_connected()

        def _monitor():
            while not self._stop_event.is_set():
                self._stop_event.wait(CHECK_INTERVAL_SECONDS)
                if self._stop_event.is_set():
                    break
                current = is_programmer_connected()
                if current != self._last_state:
                    self._last_state = current
                    try:
                        on_change_callback(current)
                    except Exception:
                        pass

        self._monitor_thread = threading.Thread(target=_monitor, daemon=True)
        self._monitor_thread.start()

    def stop_monitor(self):
        self._stop_event.set()
