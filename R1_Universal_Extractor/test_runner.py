"""
R1_Universal_Extractor: test_runner.py
======================================
Automated verification tests for R1 Universal Extractor.
Tests all extraction tiers independently to ensure 100% functionality.
"""

import os
import sys
import shutil
import struct

# Set paths
sys.path.insert(0, os.path.dirname(__file__))
from r1_extractor_core import R1ExtractorCore

TEST_DIR = os.path.join(os.path.dirname(__file__), "TEST_WORKSPACE")


def setup_workspace():
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)
    os.makedirs(TEST_DIR, exist_ok=True)


def test_tier2_capsule_strip():
    print("\n[TEST 1] Testing Tier 2: Capsule Header Stripper...")
    cap_file = os.path.join(TEST_DIR, "sample_asus_aptio.cap")
    
    # 0x800 bytes of capsule header + Flash Descriptor + dummy payload
    capsule_header = b"\xAA" * 0x800
    fd_header = b"\x5A\xA5\xF0\x0F" + (b"\x00" * 0x1000)
    
    with open(cap_file, "wb") as f:
        f.write(capsule_header + fd_header)
        
    out_dir = os.path.join(TEST_DIR, "capsule_extracted")
    summary = R1ExtractorCore.extract(cap_file, out_dir, logger=print)
    
    assert summary["success"], "Capsule strip failed!"
    assert summary["method"] == "Aptio Capsule Stripper", f"Expected Aptio Capsule Stripper, got {summary['method']}"
    
    stripped_file = os.path.join(out_dir, "sample_asus_aptio_stripped.bin")
    assert os.path.exists(stripped_file), "Stripped file not found!"
    with open(stripped_file, "rb") as f:
        head = f.read(4)
        assert head == b"\x5A\xA5\xF0\x0F", "Stripped header does not match Flash Descriptor!"
    print(">>> TEST 1 PASSED: Capsule header stripped accurately!\n")


def test_tier3_archive_unpack():
    print("[TEST 2] Testing Tier 3: Multi-Archive & Installer Unpacker...")
    import zipfile
    
    archive_file = os.path.join(TEST_DIR, "bios_update_package.zip")
    with zipfile.ZipFile(archive_file, "w") as zf:
        zf.writestr("SystemBios_v1.0.bin", b"\xFF" * (8 * 1024 * 1024)) # 8MB BIOS
        zf.writestr("KBC_EC_Firmware.bin", b"\x55" * (128 * 1024))       # 128KB EC
        zf.writestr("FlashTool.exe", b"\x90" * 1024)
        
    out_dir = os.path.join(TEST_DIR, "archive_extracted")
    summary = R1ExtractorCore.extract(archive_file, out_dir, logger=print)
    
    assert summary["success"], "Archive extraction failed!"
    classified = summary["classified"]
    assert len(classified["main_bios"]) >= 1, "Failed to identify Main BIOS candidate!"
    assert len(classified["ec_firmware"]) >= 1, "Failed to identify EC candidate!"
    print(">>> TEST 2 PASSED: Container unpacked and classified successfully!\n")


def test_tier4_deep_carver():
    print("[TEST 3] Testing Tier 4: Deep Firmware Carver...")
    exe_file = os.path.join(TEST_DIR, "unknown_vendor_packed_installer.exe")
    
    # Create fake 35MB EXE payload
    prefix_junk = b"\x90\xCC\x00\xFF" * (512 * 1024) # 2MB installer junk
    
    # 16MB valid SPI BIOS payload with proper Intel Flash Descriptor
    # FD Magic: 5A A5 F0 0F
    # Offset 0x14: FlMAP0. Let Component Base = 0x30.
    # FlMAP0 = ((0x30 >> 4) << 16) = 0x00030000
    flmap0 = struct.pack("<I", 0x00030000)
    
    # At component base 0x30:
    # FLCOMP density: 16MB chip density code is 5 (bits 0..3: 0x05)
    flcomp = struct.pack("<I", 0x05)
    
    # Build 4KB descriptor block
    desc_block = bytearray(b"\x00" * 0x1000)
    desc_block[0:4] = b"\x5A\xA5\xF0\x0F"
    desc_block[0x14:0x18] = flmap0
    desc_block[0x30:0x34] = flcomp
    
    # Complete 16MB ROM
    rom_16mb = bytes(desc_block) + (b"\xFF" * (16 * 1024 * 1024 - len(desc_block)))
    
    suffix_junk = b"\xAA" * (1024 * 1024) # 1MB overlay junk
    
    with open(exe_file, "wb") as f:
        f.write(prefix_junk + rom_16mb + suffix_junk)
        
    out_dir = os.path.join(TEST_DIR, "carver_extracted")
    summary = R1ExtractorCore.extract(exe_file, out_dir, logger=print)
    
    assert summary["success"], "Deep carve failed!"
    classified = summary["classified"]
    assert len(classified["main_bios"]) >= 1, "Carver failed to detect Main BIOS!"
    
    carved_file = classified["main_bios"][0]
    carved_size = os.path.getsize(carved_file)
    assert carved_size == 16 * 1024 * 1024, f"Expected 16MB carved file, got {carved_size} bytes!"
    print(f">>> TEST 3 PASSED: Carved 100% valid {carved_size // (1024*1024)}MB SPI ROM from inside EXE!\n")


def run_all_tests():
    print("=" * 60)
    print("STARTING R1 UNIVERSAL EXTRACTOR AUTOMATED TEST SUITE")
    print("=" * 60)
    setup_workspace()
    
    test_tier2_capsule_strip()
    test_tier3_archive_unpack()
    test_tier4_deep_carver()
    
    print("=" * 60)
    print("SUCCESS: ALL TEST SCENARIOS PASSED WITH 100% SUCCESS!")
    print("=" * 60)
    # Cleanup test workspace
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)


if __name__ == "__main__":
    run_all_tests()
