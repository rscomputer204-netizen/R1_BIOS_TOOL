import os
import json
from path_utils import get_app_root, get_resource_path

class LanguageManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LanguageManager, cls).__new__(cls)
            cls._instance.init()
        return cls._instance
        
    def init(self):
        self.translations = {}
        self.current_lang = "en"
        # Use get_resource_path so it works when compiled (files are in _internal/)
        self.translations_dir = get_resource_path("translations")
        # Fallback: if not found in _internal (dev mode), use app root
        if not os.path.exists(self.translations_dir):
            self.translations_dir = os.path.join(get_app_root(), "translations")
        os.makedirs(self.translations_dir, exist_ok=True)
        self.load_preference()
        self.load(self.current_lang)

    def load(self, lang_code):
        file_path = os.path.join(self.translations_dir, f"{lang_code}.json")
        
        # Fallback to English if translation file doesn't exist
        if not os.path.exists(file_path):
            file_path = os.path.join(self.translations_dir, "en.json")
            if not os.path.exists(file_path):
                self.translations = {}
                return
                
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
            self.current_lang = lang_code
        except Exception as e:
            print(f"Failed to load language {lang_code}: {e}")

    def t(self, key, default=""):
        return self.translations.get(key, default)

    def get_available_langs(self):
        return [
            {"code": "en", "name": "English", "flag": "🇺🇸"},
            {"code": "zh", "name": "中文 (Simplified Chinese)", "flag": "🇨🇳"},
            {"code": "ru", "name": "Русский (Russian)", "flag": "🇷🇺"},
            {"code": "hi", "name": "हिंदी (Hindi)", "flag": "🇮🇳"},
            {"code": "tr", "name": "Türkçe (Turkish)", "flag": "🇹🇷"},
            {"code": "pt", "name": "Português (Portuguese)", "flag": "🇧🇷"},
            {"code": "vi", "name": "Tiếng Việt (Vietnamese)", "flag": "🇻🇳"},
            {"code": "id", "name": "Bahasa Indonesia", "flag": "🇮🇩"},
            {"code": "ar", "name": "العربية (Arabic)", "flag": "🇸🇦"},
            {"code": "uk", "name": "Українська (Ukrainian)", "flag": "🇺🇦"},
            {"code": "bn", "name": "বাংলা (Bengali)", "flag": "🇧🇩"}
        ]

    def save_preference(self, lang_code):
        from PySide6.QtCore import QSettings
        settings = QSettings("R1AILAB", "BIOS_TOOL")
        settings.setValue("app_language", lang_code)
        self.load(lang_code)

    def load_preference(self):
        from PySide6.QtCore import QSettings
        settings = QSettings("R1AILAB", "BIOS_TOOL")
        if not settings.contains("app_language"):
            old_s = QSettings("R1 IT LAB", "BIOS_TOOL")
            if old_s.contains("app_language"):
                settings.setValue("app_language", old_s.value("app_language", "en"))
        self.current_lang = settings.value("app_language", "en")

# Create a global instance
lm = LanguageManager()

def t(key, default=""):
    return lm.t(key, default or key)
