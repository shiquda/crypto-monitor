"""
Configuration management for Crypto Monitor.
Handles loading/saving settings including proxy configuration.
"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Optional
from pathlib import Path


@dataclass
class ProxyConfig:
    """Proxy configuration settings."""
    enabled: bool = False
    type: str = "http"  # "http" or "socks5"
    host: str = "127.0.0.1"
    port: int = 7890
    username: str = ""
    password: str = ""

    def get_proxy_url(self) -> Optional[str]:
        """Get proxy URL string for requests."""
        if not self.enabled:
            return None

        auth = ""
        if self.username and self.password:
            auth = f"{self.username}:{self.password}@"

        protocol = "socks5" if self.type == "socks5" else "http"
        return f"{protocol}://{auth}{self.host}:{self.port}"


@dataclass
class AppSettings:
    """Application settings."""
    theme: str = "dark"
    opacity: int = 100
    crypto_pairs: list = field(default_factory=lambda: ["BTC-USDT", "ETH-USDT"])
    proxy: ProxyConfig = field(default_factory=ProxyConfig)
    window_x: int = 100
    window_y: int = 100
    always_on_top: bool = False


class SettingsManager:
    """Manages application settings persistence."""

    def __init__(self, config_dir: Optional[Path] = None):
        if config_dir is None:
            # Default to user's config directory
            if os.name == 'nt':  # Windows
                config_dir = Path(os.environ.get('APPDATA', '')) / 'crypto-monitor'
            else:  # Linux/Mac
                config_dir = Path.home() / '.config' / 'crypto-monitor'

        self.config_dir = config_dir
        self.config_file = config_dir / 'settings.json'
        self.settings = AppSettings()

        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def load(self) -> AppSettings:
        """Load settings from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Parse proxy config
                proxy_data = data.pop('proxy', {})
                proxy_config = ProxyConfig(**proxy_data)

                # Create settings with proxy
                self.settings = AppSettings(proxy=proxy_config, **data)
            except (json.JSONDecodeError, TypeError, KeyError) as e:
                print(f"Error loading settings: {e}")
                self.settings = AppSettings()

        return self.settings

    def save(self) -> None:
        """Save settings to file."""
        data = asdict(self.settings)

        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def update_proxy(self, proxy: ProxyConfig) -> None:
        """Update proxy configuration."""
        self.settings.proxy = proxy
        self.save()
        self._apply_proxy_env()

    def update_pairs(self, pairs: list) -> None:
        """Update crypto pairs list."""
        self.settings.crypto_pairs = pairs
        self.save()

    def add_pair(self, pair: str) -> bool:
        """Add a new crypto pair. Returns True if added."""
        pair = pair.upper()
        if pair not in self.settings.crypto_pairs:
            self.settings.crypto_pairs.append(pair)
            self.save()
            return True
        return False

    def remove_pair(self, pair: str) -> bool:
        """Remove a crypto pair. Returns True if removed."""
        pair = pair.upper()
        if pair in self.settings.crypto_pairs:
            self.settings.crypto_pairs.remove(pair)
            self.save()
            return True
        return False

    def _apply_proxy_env(self) -> None:
        """Apply proxy settings to environment variables."""
        proxy_url = self.settings.proxy.get_proxy_url()

        if proxy_url:
            os.environ['HTTP_PROXY'] = proxy_url
            os.environ['HTTPS_PROXY'] = proxy_url
            os.environ['http_proxy'] = proxy_url
            os.environ['https_proxy'] = proxy_url
        else:
            # Clear proxy environment variables
            for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
                os.environ.pop(key, None)


# Global settings instance
_settings_manager: Optional[SettingsManager] = None


def get_settings_manager() -> SettingsManager:
    """Get the global settings manager instance."""
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager()
        _settings_manager.load()
    return _settings_manager
