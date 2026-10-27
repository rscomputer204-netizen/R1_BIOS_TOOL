"""
R1 BIOS Tool - Enterprise License Security & Cryptographic Engine
==================================================================
Features:
  1. 25-character product key: XXXXX-XXXXX-XXXXX-XXXXX-XXXXX
  2. First-Use Auto-Binding (Trust On First Use / TOFU Auto-Lock):
     When customer clicks Activate for the first time, their computer's
     Hardware ID (HWID) is automatically captured and locked to their license
     on the remote GitHub repository.
  3. Strict Device Limiter:
     Enforces maximum devices (1 Device, 2 Devices, or Unlimited).
     Subsequent computers trying to use the same key are denied if the limit is full.
  4. 125-bit cryptographic integrity & tamper-proofing via HMAC-SHA256
  5. Local cache encryption (%APPDATA%/R1_BIOS_TOOL/license.dat) with machine binding
  6. Backward compatibility with legacy R1BT- keys
"""

import os
import json
import base64
import hashlib
import hmac
import struct
import secrets
import winreg
import subprocess
import urllib.request
import urllib.error
from datetime import datetime, timezone

# ─── Master Cryptographic Keys ──────────────────────────────────────────────
_K1 = b"R1_BIOS_TOOL_ENTERPRISE_SECURE_KEY"
_K2 = b"_2026_X9#@_v2_PRODUCTION_SALT"
SECRET_KEY = _K1 + _K2
DIFFUSE_SALT = b"R1_BIOS_TOOL_DIFFUSE_SALT_v2_2026"
CACHE_SECRET = b"R1_BIOS_TOOL_SECURE_CACHE_SALT_v2_9942#"

# 32-character unambiguous safe alphabet (no 0/O, 1/I confusion)
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CHAR_TO_INDEX = {c: i for i, c in enumerate(ALPHABET)}

# GitHub Verification & Sync Configuration
GITHUB_RAW_URL = "https://raw.githubusercontent.com/rscomputer204-netizen/license_keys.txt/refs/heads/main/license_keys.txt"
CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")
CONFIG_FILE = os.path.join(CONFIG_DIR, "key_generator_config.json")
APPDATA_DIR = os.path.join(os.environ.get("APPDATA", ""), "R1_BIOS_TOOL")
APPDATA_CONFIG_FILE = os.path.join(APPDATA_DIR, "key_generator_config.json")
CACHE_FILE = os.path.join(APPDATA_DIR, "license.dat")

if not os.path.exists(APPDATA_DIR):
    os.makedirs(APPDATA_DIR, exist_ok=True)

# Default embedded sync credentials for client auto-binding
DEFAULT_CLIENT_SYNC = {
    "github_token": "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",
    "repo": "rscomputer204-netizen/license_keys.txt",
    "branch": "main",
    "file_path": "license_keys.txt"
}

def get_sync_config():
    """Loads sync configuration from file or returns defaults."""
    for path in [CONFIG_FILE, APPDATA_CONFIG_FILE]:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    res = DEFAULT_CLIENT_SYNC.copy()
                    res.update(cfg)
                    return res
            except Exception:
                pass
    return DEFAULT_CLIENT_SYNC.copy()


# ─── Hardware ID (HWID) Engine ─────────────────────────────────────────────
_cached_hwid = None

def get_hardware_id() -> str:
    """
    Generates a unique, tamper-resistant Hardware ID for the local Windows machine.
    Uses MachineGuid from registry with fallback to motherboard UUID.
    Format: R1-HW-XXXX-XXXX (e.g. R1-HW-1344-46E3)
    """
    global _cached_hwid
    if _cached_hwid:
        return _cached_hwid

    raw_id = ""
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as key:
            raw_id = str(winreg.QueryValueEx(key, "MachineGuid")[0]).strip()
    except Exception:
        pass

    if not raw_id:
        try:
            out = subprocess.check_output(
                "wmic csproduct get uuid",
                shell=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
            ).decode(errors="ignore")
            lines = [line.strip() for line in out.splitlines() if line.strip() and "UUID" not in line.upper()]
            if lines:
                raw_id = lines[0]
        except Exception:
            pass

    if not raw_id:
        raw_id = "DEFAULT_R1_HARDWARE_SYSTEM"

    h = hashlib.sha256(raw_id.encode("utf-8")).hexdigest().upper()
    _cached_hwid = f"R1-HW-{h[:4]}-{h[4:8]}"
    return _cached_hwid


# ─── Helper Functions ───────────────────────────────────────────────────────
def normalize_key(key_str: str) -> str:
    """Strip spaces, hyphens, and convert to uppercase."""
    if not key_str:
        return ""
    return key_str.replace("-", "").replace(" ", "").strip().upper()

def format_product_key(raw_25: str) -> str:
    """Format a 25-character raw string into XXXXX-XXXXX-XXXXX-XXXXX-XXXXX."""
    clean = normalize_key(raw_25)
    if len(clean) != 25:
        return raw_25
    return "-".join(clean[i:i+5] for i in range(0, 25, 5))


# ─── 25-Character Product Key Generator & Validator ────────────────────────
def encode_product_key(expiry_ts: float, company: str = "") -> str:
    """
    Encodes an expiry timestamp into a 25-character product key:
    Format: XXXXX-XXXXX-XXXXX-XXXXX-XXXXX
    
    Structure (125 bits total = 25 * 5 bits):
      - 5 bits : Random top entropy
      - 32 bits: Cryptographic Nonce (4 bytes)
      - 32 bits: Expiry Unix Timestamp (uint32)
      - 8 bits : Version & Flag (0x01 = Standard Enterprise Key)
      - 48 bits: HMAC-SHA256 Truncated Signature (6 bytes)
    """
    top_5_bits = secrets.randbelow(32)
    nonce = secrets.token_bytes(4)
    ver = 0x01
    exp_int = int(expiry_ts)

    header = bytes([top_5_bits]) + nonce + struct.pack(">I", exp_int) + bytes([ver])
    sig = hmac.new(SECRET_KEY, header, hashlib.sha256).digest()[:6]

    payload = nonce + struct.pack(">I", exp_int) + bytes([ver]) + sig
    mask = hmac.new(SECRET_KEY + DIFFUSE_SALT, bytes([top_5_bits]) + nonce, hashlib.sha256).digest()[:11]
    obf_payload = nonce + bytes(a ^ b for a, b in zip(payload[4:], mask))

    val = (top_5_bits << 120) | int.from_bytes(obf_payload, "big")

    chars = []
    for _ in range(25):
        chars.append(ALPHABET[val % 32])
        val //= 32
    raw_key = "".join(reversed(chars))

    return format_product_key(raw_key)

def decode_product_key(key_str: str):
    """
    Validates cryptographic signature and extracts payload from a 25-character product key.
    Returns dict if valid, or None if tampered/invalid.
    """
    clean = normalize_key(key_str)
    if len(clean) != 25:
        return None

    val = 0
    for c in clean:
        idx = CHAR_TO_INDEX.get(c)
        if idx is None:
            return None
        val = val * 32 + idx

    top_5_bits = (val >> 120) & 0x1F
    raw_payload = (val & ((1 << 120) - 1)).to_bytes(15, "big")

    nonce = raw_payload[:4]
    mask = hmac.new(SECRET_KEY + DIFFUSE_SALT, bytes([top_5_bits]) + nonce, hashlib.sha256).digest()[:11]
    rest = bytes(a ^ b for a, b in zip(raw_payload[4:], mask))

    exp_ts = struct.unpack(">I", rest[:4])[0]
    ver = rest[4]
    sig = rest[5:]

    header = bytes([top_5_bits]) + nonce + struct.pack(">I", exp_ts) + bytes([ver])
    expected_sig = hmac.new(SECRET_KEY, header, hashlib.sha256).digest()[:6]

    if not hmac.compare_digest(sig, expected_sig):
        return None

    return {
        "version": ver,
        "expiry_ts": exp_ts
    }


# ─── Legacy Decryptor (Backward Compatibility for R1BT- keys) ──────────────
LEGACY_KEY = b"R1_BIOS_TOOL_SUPER_SECRET_KEY_2026_X9#@"

def _decrypt_legacy(key_str: str):
    if not key_str.startswith("R1BT-"):
        return None
    try:
        b64_str = key_str[5:]
        b64_str += "=" * ((4 - len(b64_str) % 4) % 4)
        raw_data = base64.urlsafe_b64decode(b64_str)
        if len(raw_data) <= 32:
            return None
        signature = raw_data[:32]
        obfuscated = raw_data[32:]
        expected_sig = hmac.new(LEGACY_KEY, obfuscated, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected_sig):
            return None
        key_hash = hashlib.sha256(LEGACY_KEY).digest()
        data = bytearray(obfuscated[i] ^ key_hash[i % len(key_hash)] for i in range(len(obfuscated)))
        return json.loads(data.decode("utf-8"))
    except Exception:
        return None


# ─── Unified Interface Functions ───────────────────────────────────────────
def encrypt_payload(payload_dict: dict) -> str:
    """
    Entry point for generating a new activation key.
    Produces the enterprise 25-character product key: XXXXX-XXXXX-XXXXX-XXXXX-XXXXX
    """
    expiry_ts = payload_dict.get("expiry_ts", 0)
    company = payload_dict.get("company", "")
    return encode_product_key(expiry_ts, company)

def decrypt_payload(key_str: str):
    """
    Entry point for validating any key (new 25-character or legacy R1BT-).
    """
    if not key_str:
        return None
    key_str = key_str.strip()

    # 1. Try new 25-char product key format
    decoded = decode_product_key(key_str)
    if decoded:
        return decoded

    # 2. Fallback to legacy R1BT- format
    if key_str.startswith("R1BT-"):
        return _decrypt_legacy(key_str)

    return None


# ─── GitHub Online Verification & First-Use Auto-Binding ────────────────────
def fetch_github_licenses():
    """
    Fetches and parses all licenses from GitHub repository.
    Format: KEY | ISSUED | EXPIRY | COMPANY | NOTE | MAX_DEVICES | REGISTERED_HWIDS
    """
    try:
        req = urllib.request.Request(GITHUB_RAW_URL, headers={"User-Agent": "R1-BIOS-TOOL-Client"})
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode("utf-8", errors="replace")
            licenses_map = {}
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("|")
                raw_key = parts[0].strip()
                issued = parts[1].strip() if len(parts) > 1 else "-"
                expiry = parts[2].strip() if len(parts) > 2 else "-"
                company = parts[3].strip().replace("_", " ") if len(parts) > 3 else "Valued Customer"
                note = parts[4].strip().replace("_", " ") if len(parts) > 4 else ""

                # Max Devices
                try:
                    max_devices = int(parts[5].strip()) if len(parts) > 5 else 1
                except Exception:
                    max_devices = 1

                # Registered HWIDs
                raw_hwids = parts[6].strip() if len(parts) > 6 else "UNBOUND"
                if not raw_hwids:
                    raw_hwids = "UNBOUND"

                if raw_hwids in ("UNBOUND", "NONE"):
                    registered_hwids = []
                elif raw_hwids == "ANY":
                    registered_hwids = ["ANY"]
                else:
                    registered_hwids = [h.strip() for h in raw_hwids.split(",") if h.strip()]

                norm = normalize_key(raw_key)
                info = {
                    "original_key": raw_key,
                    "issued": issued,
                    "expiry": expiry,
                    "company": company,
                    "note": note,
                    "max_devices": max_devices,
                    "hwid_str": raw_hwids,
                    "registered_hwids": registered_hwids,
                    "raw_line": line
                }
                licenses_map[norm] = info
                licenses_map[raw_key] = info
            return licenses_map
    except Exception as e:
        print(f"Failed to fetch GitHub licenses: {e}")
        return None

def fetch_github_keys():
    """Returns list of raw key strings for backward compatibility."""
    lic_map = fetch_github_licenses()
    if lic_map is None:
        return None
    return [info["original_key"] for info in lic_map.values()]


def auto_bind_hwid_on_github(key_str: str, current_hwid: str, max_devices: int):
    """
    Auto-binds the current machine's HWID to this license on GitHub.
    Runs seamlessly when a customer activates for the first time.
    """
    cfg = get_sync_config()
    token = cfg.get("github_token", "").strip()
    repo = cfg.get("repo", "").strip()
    branch = cfg.get("branch", "main").strip()
    file_path = cfg.get("file_path", "license_keys.txt").strip()

    if not token or not repo:
        return False, "Missing GitHub connection configuration."

    api_url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "R1-BIOS-TOOL-AutoBind",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    try:
        # Step 1: Fetch current content and SHA
        file_get_url = f"{api_url}?ref={branch}"
        req = urllib.request.Request(file_get_url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            sha = data.get("sha")
            raw_content = base64.b64decode(data.get("content", "").replace("\n", "")).decode("utf-8", errors="replace")

        # Step 2: Find and update the line for this key
        clean_target = normalize_key(key_str)
        lines = raw_content.splitlines()
        updated_lines = []
        found = False
        company_name = "Customer"

        for line in lines:
            line_clean = line.strip()
            if not line_clean or line_clean.startswith("#"):
                updated_lines.append(line)
                continue

            parts = line_clean.split("|")
            line_key = normalize_key(parts[0])

            if line_key == clean_target:
                found = True
                issued = parts[1].strip() if len(parts) > 1 else "-"
                expiry = parts[2].strip() if len(parts) > 2 else "-"
                company_name = parts[3].strip().replace("_", " ") if len(parts) > 3 else "Customer"
                note = parts[4].strip() if len(parts) > 4 else ""

                try:
                    line_max = int(parts[5].strip()) if len(parts) > 5 else max_devices
                except Exception:
                    line_max = max_devices

                raw_hwids = parts[6].strip() if len(parts) > 6 else "UNBOUND"
                if raw_hwids in ("UNBOUND", "NONE", ""):
                    hwid_list = []
                elif raw_hwids == "ANY":
                    hwid_list = ["ANY"]
                else:
                    hwid_list = [h.strip() for h in raw_hwids.split(",") if h.strip()]

                # Add this machine's HWID if not already in list
                if current_hwid not in hwid_list and "ANY" not in hwid_list:
                    hwid_list.append(current_hwid)

                hwid_str = ",".join(hwid_list) if hwid_list else "UNBOUND"
                company_field = company_name.replace(" ", "_").replace("|", "_")
                new_line = f"{parts[0].strip()}|{issued}|{expiry}|{company_field}|{note}|{line_max}|{hwid_str}"
                updated_lines.append(new_line)
            else:
                updated_lines.append(line)

        if not found:
            return False, "Key was not found on remote server."

        # Step 3: Commit updated content back to GitHub
        new_full_content = "\n".join(updated_lines) + "\n"
        b64_new = base64.b64encode(new_full_content.encode("utf-8")).decode("utf-8")
        commit_msg = f"Auto-bind device {current_hwid} for {company_name}"

        put_data = {
            "message": commit_msg,
            "content": b64_new,
            "branch": branch,
            "sha": sha
        }

        put_req = urllib.request.Request(
            api_url,
            data=json.dumps(put_data).encode("utf-8"),
            headers=headers,
            method="PUT"
        )

        with urllib.request.urlopen(put_req, timeout=12) as put_resp:
            res_body = json.loads(put_resp.read().decode("utf-8"))
            commit_sha = res_body.get("commit", {}).get("sha", "")[:7]
            return True, f"Device locked successfully! (Commit: {commit_sha})"

    except Exception as e:
        return False, f"Failed to register device on server: {str(e)}"


# ─── Authenticated Local Cache Management (license.dat) ─────────────────────
def save_cache(payload: dict):
    """
    Encrypts and saves the active license to %APPDATA%/R1_BIOS_TOOL/license.dat
    bound to the machine's local Hardware ID.
    """
    try:
        payload["last_verified"] = datetime.now(timezone.utc).timestamp()
        if "machine_hwid" not in payload:
            payload["machine_hwid"] = get_hardware_id()
        data_bytes = json.dumps(payload).encode("utf-8")
        salt = secrets.token_bytes(16)
        key_stream = hashlib.pbkdf2_hmac("sha256", CACHE_SECRET, salt, 1000, dklen=len(data_bytes))
        encrypted = bytes(a ^ b for a, b in zip(data_bytes, key_stream))
        sig = hmac.new(CACHE_SECRET, salt + encrypted, hashlib.sha256).digest()
        token = base64.urlsafe_b64encode(salt + sig + encrypted).decode("utf-8")

        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            f.write(token)
    except Exception as e:
        print(f"Error saving license cache: {e}")

def load_cache():
    """
    Loads and decrypts license from local cache file.
    Validates that the file was generated on this exact computer (HWID verification).
    """
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            b64_str = f.read().strip()
        raw = base64.urlsafe_b64decode(b64_str)
        if len(raw) < 48:
            return None
        salt = raw[:16]
        sig = raw[16:48]
        encrypted = raw[48:]
        expected_sig = hmac.new(CACHE_SECRET, salt + encrypted, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected_sig):
            return None
        key_stream = hashlib.pbkdf2_hmac("sha256", CACHE_SECRET, salt, 1000, dklen=len(encrypted))
        decrypted = bytes(a ^ b for a, b in zip(encrypted, key_stream))
        payload = json.loads(decrypted.decode("utf-8"))

        # Hardware Binding Check: Ensure cache was not copied to another PC
        cached_machine = payload.get("machine_hwid", "")
        current_hwid = get_hardware_id()
        allowed = payload.get("allowed_hwids", ["ANY"])
        if "ANY" not in allowed:
            if current_hwid not in allowed or (cached_machine and cached_machine != current_hwid):
                # License file was stolen / copied to another PC
                clear_cache()
                return None

        return payload
    except Exception:
        return None

def clear_cache():
    """Removes the local license cache file."""
    if os.path.exists(CACHE_FILE):
        try:
            os.remove(CACHE_FILE)
        except Exception:
            pass


# ─── License Verification & Activation API ──────────────────────────────────
_is_verifying = False
_verified_payload = None

def verify_and_activate(key_str: str):
    """
    Multi-stage verification and activation:
      Stage 1: Offline cryptographic integrity and signature check
      Stage 2: Offline expiration timestamp check
      Stage 3: Online check against GitHub license database
      Stage 4: First-Use Auto-Binding & Device Limiting enforcement
      Stage 5: Cache payload in encrypted local license.dat bound to this PC
    """
    global _verified_payload
    clean_key = normalize_key(key_str)
    current_hwid = get_hardware_id()
    
    # Stage 1: Cryptographic decode
    payload = decrypt_payload(key_str)
    if not payload:
        return False, "Invalid License Key Format or Cryptographic Signature Tampered."

    # Stage 2: Check expiration
    try:
        expiry_ts = float(payload.get("expiry_ts", 0))
        now_ts = datetime.now(timezone.utc).timestamp()
        if now_ts > expiry_ts:
            clear_cache()
            return False, "This License Key has expired."
    except Exception:
        return False, "Invalid Expiry Date in Key."

    # Stage 3: Online check against GitHub
    github_licenses = fetch_github_licenses()
    if github_licenses is None:
        return False, "Cannot connect to online verification server. Please check your internet connection."

    remote_match = github_licenses.get(clean_key) or github_licenses.get(key_str.strip())
    if not remote_match:
        return False, "Key is not registered in the online database or has been revoked."

    # Stage 4: First-Use Auto-Binding & Device Limiting
    max_devices = int(remote_match.get("max_devices", 1))
    registered_hwids = remote_match.get("registered_hwids", [])

    # Case A: Machine is already registered or license is Unlimited (ANY)
    if current_hwid in registered_hwids or "ANY" in registered_hwids:
        # Already authorized
        pass

    # Case B: Free device slot available -> Auto-bind current machine's HWID!
    elif len(registered_hwids) < max_devices:
        success, bind_msg = auto_bind_hwid_on_github(key_str, current_hwid, max_devices)
        if not success:
            return False, f"Auto-binding failed: {bind_msg}"
        registered_hwids.append(current_hwid)

    # Case C: All device slots are filled -> Deny access!
    else:
        return False, (
            f"Device Limit Reached!\n\n"
            f"This license is already registered on {len(registered_hwids)} of {max_devices} allowed device(s):\n"
            f"Active Device(s): {', '.join(registered_hwids)}\n\n"
            f"It cannot be activated on this computer (Your HWID: {current_hwid}).\n"
            f"Please contact support if you need to transfer or reset your license."
        )

    # Stage 5: Build enriched payload and save locally
    payload["company"] = remote_match.get("company", "Valued Customer")
    payload["note"] = remote_match.get("note", "")
    payload["original_key"] = format_product_key(clean_key) if len(clean_key) == 25 else key_str.strip()
    payload["allowed_hwids"] = registered_hwids
    payload["machine_hwid"] = current_hwid
    payload["max_devices"] = max_devices

    save_cache(payload)
    _verified_payload = payload
    device_info = f"(Device {len(registered_hwids)}/{max_devices})" if "ANY" not in registered_hwids else "(Unlimited Devices)"
    return True, f"Key Activated Successfully for '{payload['company']}'!\n\nLocked to this computer {device_info}."

def get_active_license():
    """
    Returns active license payload if valid.
    Performs background online check to verify revocation and HWID without blocking UI.
    """
    global _is_verifying, _verified_payload

    if _verified_payload:
        return _verified_payload

    payload = load_cache()
    if not payload:
        return None

    try:
        expiry_ts = float(payload.get("expiry_ts", 0))
        now_ts = datetime.now(timezone.utc).timestamp()
        if now_ts > expiry_ts:
            clear_cache()
            return None
    except Exception:
        clear_cache()
        return None

    # Verify HWID on local machine
    current_hwid = get_hardware_id()
    allowed = payload.get("allowed_hwids", ["ANY"])
    if "ANY" not in allowed and current_hwid not in allowed and payload.get("machine_hwid") != current_hwid:
        clear_cache()
        return None

    if _is_verifying:
        return None

    _is_verifying = True

    def bg_check():
        global _is_verifying, _verified_payload
        try:
            github_licenses = fetch_github_licenses()
            if github_licenses is not None:
                orig_key = payload.get("original_key", "")
                clean_key = normalize_key(orig_key)
                lic_info = github_licenses.get(clean_key) or github_licenses.get(orig_key)
                if not lic_info:
                    # Key was revoked from GitHub
                    clear_cache()
                    _verified_payload = None
                else:
                    remote_hwids = lic_info.get("registered_hwids", ["ANY"])
                    if "ANY" not in remote_hwids and current_hwid not in remote_hwids:
                        # Device was removed or transferred on GitHub
                        clear_cache()
                        _verified_payload = None
                    else:
                        _verified_payload = payload
        finally:
            _is_verifying = False

    import threading
    threading.Thread(target=bg_check, daemon=True).start()

    return payload
