import sys, os, struct, hashlib
sys.path.insert(0, r'd:\BIOS_-TOOL')
from R1_CSME_Analyzer.r1_csme_parser import get_mea_db, SIG_MN2

with open(r'D:\SDD DATA\all bios\Bios\HP\6050a2930901-mb-a01(a1)\EC16MB\read meraj.bin', 'rb') as f:
    data = f.read()

pos = 0
mn2_entries = []
mea_db = get_mea_db()

while True:
    pos = data.find(SIG_MN2, pos)
    if pos == -1: break
    hdr_start = pos - 0x1C
    if hdr_start >= 0 and hdr_start + 0x30 <= len(data):
        day = data[hdr_start + 0x14]
        month = data[hdr_start + 0x15]
        year = struct.unpack("<H", data[hdr_start + 0x16 : hdr_start + 0x18])[0]
        major, minor, hotfix, build = struct.unpack("<HHHH", data[hdr_start + 0x24 : hdr_start + 0x2C])
        sig_hash = ""
        if hdr_start + 0x80 <= len(data):
            pk_size_dw = struct.unpack("<I", data[hdr_start+0x78:hdr_start+0x7C])[0]
            exp_size_dw = struct.unpack("<I", data[hdr_start+0x7C:hdr_start+0x80])[0]
            pk_size = pk_size_dw * 4
            exp_size = exp_size_dw * 4
            if 64 <= pk_size <= 1024 and 1 <= exp_size <= 64:
                sig_off = hdr_start + 0x80 + pk_size + exp_size
                if sig_off + pk_size <= len(data):
                    sig_data = data[sig_off : sig_off + pk_size]
                    sig_hash = hashlib.sha256(sig_data).hexdigest().upper()

        tag = mea_db.get(sig_hash, "")
        print(f"MN2 @ 0x{pos:X}: ver {major}.{minor}.{hotfix}.{build}, hash={sig_hash[:16]}, db_tag={tag}")
    pos += 4
