"""
Configuration management for Crypto Monitor.
Handles loading/saving settings including proxy configuration.
Enhanced with automatic migration support.
"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List
from pathlib import Path

from .migration import MigrationManager, ConfigVersion


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
class CompactModeConfig:
    """Compact mode configuration."""
    enabled: bool = False
    auto_scroll: bool = True
    scroll_interval: int = 5  # seconds
    window_x: int = 100
    window_y: int = 100


@dataclass
class WebSocketConfig:
    """WebSocket configuration."""
    auto_reconnect: bool = True
    reconnect_initial_delay: float = 1.0
    reconnect_max_delay: float = 30.0
    backoff_factor: float = 2.0
    heartbeat_timeout: int = 60
    connection_timeout: int = 60


@dataclass
class AppSettings:
    """Application settings."""
    # Current version
    version: str = "2.1.0"

    # Basic settings
    theme_mode: str = "light"  # "light", "dark", or "auto"
    opacity: int = 100
    crypto_pairs: list = field(default_factory=lambda: ["BTC-USDT", "ETH-USDT"])
    proxy: ProxyConfig = field(default_factory=ProxyConfig)
    window_x: int = 100
    window_y: int = 100
    always_on_top: bool = False

    # V2.0.0 features
    compact_mode: CompactModeConfig = field(default_factory=CompactModeConfig)

    # V2.1.0 features
    websocket: WebSocketConfig = field(default_factory=WebSocketConfig)


class SettingsManager:
    """Manages application settings persistence with automatic migration support."""

    # Current application configuration version
    CURRENT_VERSION = ConfigVersion.V2_1_0

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

        # Initialize migration manager
        self.migration_manager = MigrationManager(self.config_file, self.CURRENT_VERSION)

    def load(self, auto_migrate: bool = True) -> AppSettings:
        """
        Load settings from file.

        Args:
            auto_migrate: If True, automatically migrate configuration to current version

        Returns:
            Loaded settings
        """
        if auto_migrate:
            try:
                migrated, message, backup_path = self.migration_manager.migrate_if_needed()
                if migrated:
                    print(f"✅ Configuration migrated: {message}")
                    if backup_path:
                        print(f"📦 Backup saved to: {backup_path}")
            except Exception as e:
                print(f"⚠️  Configuration migration failed: {e}")
                print("   Using default settings")

        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Parse proxy config
                proxy_data = data.pop('proxy', {})
                if not isinstance(proxy_data, dict):
                    proxy_data = {}
                proxy_config = ProxyConfig(**proxy_data)

                # Parse compact mode config (V2.0.0+)
                compact_mode_data = data.pop('compact_mode', {})
                if not isinstance(compact_mode_data, dict):
                    compact_mode_data = {}
                compact_mode_config = CompactModeConfig(**compact_mode_data)

                # Parse websocket config (V2.1.0+)
                websocket_data = data.pop('websocket', {})
                if not isinstance(websocket_data, dict):
                    websocket_data = {}
                websocket_config = WebSocketConfig(**websocket_data)

                # Only keep recognized fields in data
                recognized_fields = {
                    'version', 'theme_mode', 'opacity', 'crypto_pairs',
                    'window_x', 'window_y', 'always_on_top'
                }
                filtered_data = {k: v for k, v in data.items() if k in recognized_fields}

                # Create settings with all configs
                self.settings = AppSettings(
                    proxy=proxy_config,
                    compact_mode=compact_mode_config,
                    websocket=websocket_config,
                    **filtered_data
                )
            except (json.JSONDecodeError, TypeError, KeyError) as e:
                print(f"Error loading settings: {e}")
                print("   Resetting to default settings")
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

    def update_theme(self, theme_mode: str) -> None:
        """Update theme mode."""
        self.settings.theme_mode = theme_mode
        self.save()

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

    def force_migration(self) -> bool:
        """
        Force migration to current version.

        Returns:
            True if migration was performed, False otherwise
        """
        try:
            migrated, message, backup_path = self.migration_manager.migrate_if_needed(force=True)
            if migrated:
                print(f"✅ {message}")
                if backup_path:
                    print(f"📦 Backup: {backup_path}")
            else:
                print(f"ℹ️  {message}")
            return migrated
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            return False

    def get_config_version(self) -> str:
        """
        Get current configuration version.

        Returns:
            Version string
        """
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('version', '1.0.0')
            except:
                pass

        return self.settings.version

    def get_backup_list(self) -> List[Path]:
        """
        Get list of configuration backups.

        Returns:
            List of backup file paths (newest first)
        """
        backup_dir = self.config_dir / 'backups'
        if not backup_dir.exists():
            return []

        backups = sorted(
            backup_dir.glob('settings_*.json'),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        return backups

    def reset_to_defaults(self) -> None:
        """Reset configuration to default values."""
        print("⚠️  Resetting configuration to defaults...")
        self.settings = AppSettings()
        self.save()
        print("✅ Configuration reset to defaults")


# Global settings instance
_settings_manager: Optional[SettingsManager] = None


def get_settings_manager() -> SettingsManager:
    """Get the global settings manager instance."""
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager()
        _settings_manager.load()
    return _settings_manager
