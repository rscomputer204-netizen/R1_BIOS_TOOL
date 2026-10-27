from firmware_organizer import detect_and_organize_local_firmware
import os
from pathlib import Path

def create_test_files():
    # Create some dummy files
    files = {
        "me_test.bin": b"some data $FPT more data",
        "csme_test.rom": b"some data $FPT more ME14 data",
        "random_bios.fd": b"just a normal bios file" * 100
    }
    
    for name, content in files.items():
        with open(name, "wb") as f:
            f.write(content)
    print("Created test firmware files.")

def test_organizer():
    create_test_files()
    
    print("\n--- Running Organizer ---")
    detect_and_organize_local_firmware(os.getcwd())
    
    # Check if files moved
    db_path = Path("firmware_database")
    print(f"\nChecking directory: {db_path}")
    for sub in ["intel_me", "csme", "other"]:
        folder = db_path / sub
        files = list(folder.glob("*"))
        print(f"{sub}: {[f.name for f in files]}")
        
    # Cleanup (not strictly necessary but good practice)
    # shutil.rmtree(db_path)

if __name__ == "__main__":
    test_organizer()
