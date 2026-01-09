import json
import locale
import sys
from pathlib import Path
from typing import Dict, Optional, List

class Translations:
    _instance = None
    _translations: Dict[str, str] = {}
    _current_lang = "en_US"
    
    # Supported languages map: prefix -> full code (default for that prefix)
    # Also includes full codes
    SUPPORTED_LANGUAGES = {
        "en": "en_US",
        "zh": "zh_CN",
        "es": "es_ES",
        "fr": "fr_FR",
        "de": "de_DE",
        "ja": "ja_JP",
        "ru": "ru_RU",
        "pt": "pt_BR",
        "en_US": "en_US",
        "zh_CN": "zh_CN",
        "es_ES": "es_ES",
        "fr_FR": "fr_FR",
        "de_DE": "de_DE",
        "ja_JP": "ja_JP",
        "ru_RU": "ru_RU",
        "pt_BR": "pt_BR"
    }
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Translations, cls).__new__(cls)
        return cls._instance

    def detect_system_language(self) -> str:
        """Detect system language and return corresponding supported language code."""
        try:
            # Get default locale
            loc = locale.getdefaultlocale()
            if not loc or not loc[0]:
                return "en_US"
            
            sys_lang = loc[0] # e.g., 'en_GB', 'zh_TW'
            
            # Exact match check (if we supported more specific variants)
            # Currently we don't have separate files for en_GB vs en_US
            
            # Prefix check
            lang_prefix = sys_lang.split('_')[0].lower()
            
            if lang_prefix in self.SUPPORTED_LANGUAGES:
                return self.SUPPORTED_LANGUAGES[lang_prefix]
                
            return "en_US"
            
        except Exception:
            return "en_US"

    def load_language(self, lang_code: str):
        """Load translations for the specified language code. Supports 'auto'."""
        
        target_lang = lang_code
        if lang_code == "auto":
            target_lang = self.detect_system_language()
        
        self._current_lang = target_lang
        self._translations = {}
        
        if target_lang == "en_US":
            # Default fallback is usually English, so we might return
            # But we also have an en_US.json, let's try to load it to be consistent
            # incase keys in code are different from display text (though usually keys are English)
            pass

        # Look for json file in i18n directory
        root_dir = Path(__file__).parent.parent
        file_path = root_dir / "i18n" / f"{target_lang}.json"
        
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    self._translations = json.load(f)
            except Exception as e:
                print(f"Error loading translations for {target_lang}: {e}")
        else:
            # Fallback to en_US if target not found (and not en_US)
            if target_lang != "en_US":
                print(f"Translation file not found: {file_path}, falling back to en_US")
                fallback_path = root_dir / "i18n" / "en_US.json"
                if fallback_path.exists():
                     try:
                        with open(fallback_path, "r", encoding="utf-8") as f:
                            self._translations = json.load(f)
                     except:
                         pass

    def get(self, key: str) -> str:
        """Get translation for key. Returns key if translation is missing or empty."""
        val = self._translations.get(key)
        if val and isinstance(val, str) and val.strip():
            return val
        return key
    
    def get_current_language(self) -> str:
        return self._current_lang

# Global helper function
_translator = Translations()

def _(text: str) -> str:
    """Translate text."""
    return _translator.get(text)

def load_language(lang_code: str):
    """Load language helper."""
    _translator.load_language(lang_code)

def get_current_language() -> str:
    """Get current active language code"""
    return _translator.get_current_language()
