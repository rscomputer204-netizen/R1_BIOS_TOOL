import sys
import subprocess
import os
import time

def check_python_version():
    print(f"✅ Python is installed. Version: {sys.version.split(' ')[0]}")
    print("--------------------------------------------------")

def install_packages():
    print("⏳ প্রয়োজনীয় প্যাকেজগুলো ইন্সটল করা হচ্ছে, অনুগ্রহ করে অপেক্ষা করুন...")
    
    # List of important packages for this project (fallback if requirements.txt is missing)
    fallback_packages = [
        "PySide6", 
        "requests", 
        "colorama", 
        "pydantic", 
        "SQLAlchemy", 
        "celery",
        "pyinstaller"
    ]
    
    req_file = os.path.join(os.path.dirname(__file__), "requirements.txt")
    
    try:
        if os.path.exists(req_file):
            print("📦 requirements.txt পাওয়া গেছে। এখান থেকে সব প্যাকেজ ইন্সটল করা হচ্ছে...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_file])
        else:
            print("⚠️ requirements.txt পাওয়া যায়নি! ডিফল্ট প্যাকেজগুলো ইন্সটল করা হচ্ছে...")
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + fallback_packages)
            
        print("\n🎉 অভিনন্দন! সব প্যাকেজ সফলভাবে ইন্সটল হয়েছে।")
        print("▶️ এখন আপনি 'python main.py' রান করে সফটওয়্যারটি ব্যবহার করতে পারেন।")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ প্যাকেজ ইন্সটল করতে সমস্যা হয়েছে: {e}")
        print("💡 দয়া করে ইন্টারনেট কানেকশন চেক করুন এবং আবার চেষ্টা করুন।")

if __name__ == "__main__":
    print("==================================================")
    print("      BIOS TOOL - Automatic Package Installer     ")
    print("==================================================")
    print("💡 নির্দেশিকা: এই স্ক্রিপ্টটি রান করার আগে নিশ্চিত করুন")
    print("আপনার পিসিতে Python ইন্সটল করা আছে এবং ইন্টারনেট কানেকশন আছে।")
    print("--------------------------------------------------")
    
    time.sleep(2)
    check_python_version()
    install_packages()
    
    input("\nউইন্ডোটি বন্ধ করতে Enter চাপুন...")
