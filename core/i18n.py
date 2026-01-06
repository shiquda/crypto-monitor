import json
import os
from pathlib import Path
from typing import Dict, Optional

class Translations:
    _instance = None
    _translations: Dict[str, str] = {}
    _current_lang = "en_US"
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Translations, cls).__new__(cls)
        return cls._instance

    def load_language(self, lang_code: str):
        """Load translations for the specified language code."""
        self._current_lang = lang_code
        self._translations = {}
        
        if lang_code == "en_US":
            return

        # Look for json file in i18n directory
        # Assuming i18n is in the root of the repo, relative to this file
        # core/i18n.py -> ../i18n
        root_dir = Path(__file__).parent.parent
        file_path = root_dir / "i18n" / f"{lang_code}.json"
        
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    self._translations = json.load(f)
            except Exception as e:
                print(f"Error loading translations for {lang_code}: {e}")
        else:
            print(f"Translation file not found: {file_path}")

    def get(self, key: str) -> str:
        """Get translation for key."""
        return self._translations.get(key, key)

# Global helper function
_translator = Translations()

def _(text: str) -> str:
    """Translate text."""
    return _translator.get(text)

def load_language(lang_code: str):
    """Load language helper."""
    _translator.load_language(lang_code)
