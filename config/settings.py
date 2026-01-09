"""
Configuration management for Crypto Monitor.
Handles loading/saving settings including proxy configuration.
Enhanced with automatic migration support.
"""

import json
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List
from pathlib import Path

from .migration import MigrationManager, ConfigVersion
from core.i18n import load_language
import logging

logger = logging.getLogger(__name__)


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
class PriceAlert:
    """Price alert configuration."""
    id: str = ""                           # Unique identifier (UUID)
    pair: str = ""                         # Trading pair, e.g., "BTC-USDT"
    alert_type: str = "price_above"        # "price_above" | "price_below" | "price_touch"
    target_price: float = 0.0              # Target price
    repeat_mode: str = "once"              # "once" | "repeat"
    enabled: bool = True                   # Whether the alert is enabled
    cooldown_seconds: int = 60             # Cooldown time (only for repeat mode)
    last_triggered: Optional[float] = None # Last triggered timestamp
    created_at: float = 0.0                # Creation timestamp

    def __post_init__(self):
        """Initialize default values if not set."""
        if not self.id:
            self.id = str(uuid.uuid4())
        if self.created_at == 0.0:
            self.created_at = time.time()

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'PriceAlert':
        """Create PriceAlert from dictionary."""
        return PriceAlert(
            id=data.get('id', str(uuid.uuid4())),
            pair=data.get('pair', ''),
            alert_type=data.get('alert_type', 'price_above'),
            target_price=data.get('target_price', 0.0),
            repeat_mode=data.get('repeat_mode', 'once'),
            enabled=data.get('enabled', True),
            cooldown_seconds=data.get('cooldown_seconds', 60),
            last_triggered=data.get('last_triggered'),
            created_at=data.get('created_at', time.time())
        )


@dataclass
class AppSettings:
    """Application settings."""
    # Current version
    version: str = "2.3.0"  # Bump version
    data_source: str = "OKX"  # "OKX" or "Binance"

    # Basic settings
    # Basic settings
    theme_mode: str = "light"  # "light", "dark", or "auto"
    color_schema: str = "standard"  # "standard" (Green Up/Red Down) or "reverse" (Red Up/Green Down)
    dynamic_background: bool = True  # Enable dynamic background color based on price change
    kline_period: str = "24h" # "1h", "4h", "12h", "24h", "7d"
    chart_cache_ttl: int = 60  # Mini chart cache duration in seconds (default 1 minute)
    hover_enabled: bool = True     # Master toggle for hover card
    hover_show_stats: bool = True  # Toggle for statistics in hover card
    hover_show_chart: bool = True  # Toggle for mini chart in hover card
    opacity: int = 100
    display_limit: int = 3  # Number of pairs to display per page (1-5)
    auto_scroll: bool = False   # Auto-cycle pages
    scroll_interval: int = 30   # Auto-scroll interval in seconds
    minimalist_view: bool = False  # Minimalist view mode (hide chrome when not hovered)
    crypto_pairs: list = field(default_factory=lambda: ["BTC-USDT", "ETH-USDT"])
    proxy: ProxyConfig = field(default_factory=ProxyConfig)
    window_x: int = 100
    window_y: int = 100
    always_on_top: bool = False
    language: str = "auto"  # "auto", "en_US", "zh_CN", etc.
    price_change_basis: str = "24h_rolling"  # "24h_rolling" or "utc_0"

    # V2.0.0 features
    compact_mode: CompactModeConfig = field(default_factory=CompactModeConfig)

    # V2.1.0 features
    websocket: WebSocketConfig = field(default_factory=WebSocketConfig)

    # V2.2.0 features
    alerts: List[PriceAlert] = field(default_factory=list)
    # V2.2.0 features
    alerts: List[PriceAlert] = field(default_factory=list)
    sound_mode: str = "system"  # "off", "system", "chime"


class SettingsManager:
    """Manages application settings persistence with automatic migration support."""

    # Current application configuration version
    CURRENT_VERSION = ConfigVersion.V2_2_0

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
                    logger.info(f"✅ Configuration migrated: {message}")
                    if backup_path:
                        logger.info(f"📦 Backup saved to: {backup_path}")
            except Exception as e:
                logger.error(f"⚠️  Configuration migration failed: {e}")
                logger.warning("   Using default settings")

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

                # Parse alerts config (V2.2.0+)
                alerts_data = data.pop('alerts', [])
                if not isinstance(alerts_data, list):
                    alerts_data = []
                alerts_list = [PriceAlert.from_dict(a) for a in alerts_data if isinstance(a, dict)]

                # Only keep recognized fields in data
                recognized_fields = {
                    'version', 'data_source', 'theme_mode', 'color_schema', 'dynamic_background', 'kline_period', 
                    'chart_cache_ttl', 'hover_enabled', 'hover_show_stats', 'hover_show_chart',
                    'opacity', 'crypto_pairs', 'display_limit', 'minimalist_view',
                    'auto_scroll', 'scroll_interval',
                    'window_x', 'window_y', 'always_on_top', 'language', 'price_change_basis',
                    'auto_scroll', 'scroll_interval',
                    'window_x', 'window_y', 'always_on_top', 'language', 'price_change_basis',
                    'sound_mode'
                }
                filtered_data = {k: v for k, v in data.items() if k in recognized_fields}

                # Create settings with all configs
                self.settings = AppSettings(
                    proxy=proxy_config,
                    compact_mode=compact_mode_config,
                    websocket=websocket_config,
                    alerts=alerts_list,
                    **filtered_data
                )
            except (json.JSONDecodeError, TypeError, KeyError) as e:
                logger.error(f"Error loading settings: {e}")
                logger.warning("   Resetting to default settings")
                self.settings = AppSettings()

        # Initialize language loader
        load_language(self.settings.language)

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

    def update_opacity(self, opacity: int) -> None:
        """Update background opacity setting."""
        self.settings.opacity = opacity
        self.save()

    def update_sound_mode(self, mode: str) -> None:
        """Update sound mode setting."""
        self.settings.sound_mode = mode
        self.save()

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

    def update_color_schema(self, schema: str) -> None:
        """Update color schema."""
        self.settings.color_schema = schema
        self.save()

    def update_dynamic_background(self, enabled: bool) -> None:
        """Update dynamic background setting."""
        self.settings.dynamic_background = enabled
        self.save()

    def update_kline_period(self, period: str) -> None:
        """Update kline period setting."""
        self.settings.kline_period = period
        self.save()

    def update_hover_settings(self, enabled: bool = None, show_stats: bool = None, show_chart: bool = None) -> None:
        """Update hover card settings."""
        if enabled is not None:
            self.settings.hover_enabled = enabled
        if show_stats is not None:
            self.settings.hover_show_stats = show_stats
        if show_chart is not None:
            self.settings.hover_show_chart = show_chart
        self.save()

    def update_display_limit(self, limit: int) -> None:
        """Update display limit (items per page)."""
        if 1 <= limit <= 5:
            self.settings.display_limit = limit
            self.save()

    def update_auto_scroll(self, enabled: bool, interval: int) -> None:
        """Update auto scroll settings."""
        self.settings.auto_scroll = enabled
        self.settings.scroll_interval = interval
        self.save()

    def update_minimalist_view(self, enabled: bool) -> None:
        """Update minimalist view setting."""
        self.settings.minimalist_view = enabled
        self.save()

    def update_language(self, language: str) -> None:
        """Update language setting."""
        self.settings.language = language
        load_language(language)
        self.save()

    def update_data_source(self, source: str) -> None:
        """Update data source setting."""
        self.settings.data_source = source
        self.save()

    def update_price_change_basis(self, basis: str) -> None:
        """Update price change basis setting."""
        self.settings.price_change_basis = basis
        self.save()

    # Alert management methods
    def add_alert(self, alert: PriceAlert) -> None:
        """Add a new price alert."""
        self.settings.alerts.append(alert)
        self.save()

    def remove_alert(self, alert_id: str) -> bool:
        """Remove a price alert by ID. Returns True if removed."""
        for i, alert in enumerate(self.settings.alerts):
            if alert.id == alert_id:
                self.settings.alerts.pop(i)
                self.save()
                return True
        return False

    def update_alert(self, alert: PriceAlert) -> bool:
        """Update an existing alert. Returns True if updated."""
        for i, existing in enumerate(self.settings.alerts):
            if existing.id == alert.id:
                self.settings.alerts[i] = alert
                self.save()
                return True
        return False

    def get_alerts_for_pair(self, pair: str) -> List[PriceAlert]:
        """Get all alerts for a specific trading pair."""
        return [a for a in self.settings.alerts if a.pair == pair]

    def get_enabled_alerts(self) -> List[PriceAlert]:
        """Get all enabled alerts."""
        return [a for a in self.settings.alerts if a.enabled]

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
                logger.info(f"✅ {message}")
                if backup_path:
                    logger.info(f"📦 Backup: {backup_path}")
            else:
                logger.info(f"ℹ️  {message}")
            return migrated
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
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
        logger.warning("⚠️  Resetting configuration to defaults...")
        self.settings = AppSettings()
        self.save()
        logger.info("✅ Configuration reset to defaults")

    def export_to_file(self, filepath: str) -> None:
        """Export settings to a specific file."""
        data = asdict(self.settings)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def import_from_file(self, filepath: str) -> None:
        """Import settings from a specific file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Basic validation by trying to load it like normal settings logic
        # For simplicity, we can temporarily save it to the main config file location and reload,
        # or parse it manually. Let's reuse the parsing logic in load() by updating self.settings using this data.
        
        # We can simulate loading by mocking the file read, but here we'll just replicate the parsing logic
        # or slightly refactor. For safety and consistency with existing validation/parsing:
        
        # Parse proxy config
        proxy_data = data.pop('proxy', {})
        if not isinstance(proxy_data, dict):
            proxy_data = {}
        proxy_config = ProxyConfig(**proxy_data)

        # Parse compact mode config
        compact_mode_data = data.pop('compact_mode', {})
        if not isinstance(compact_mode_data, dict):
            compact_mode_data = {}
        compact_mode_config = CompactModeConfig(**compact_mode_data)

        # Parse websocket config
        websocket_data = data.pop('websocket', {})
        if not isinstance(websocket_data, dict):
            websocket_data = {}
        websocket_config = WebSocketConfig(**websocket_data)

        # Parse alerts config
        alerts_data = data.pop('alerts', [])
        if not isinstance(alerts_data, list):
            alerts_data = []
        alerts_list = [PriceAlert.from_dict(a) for a in alerts_data if isinstance(a, dict)]

        # Only keep recognized fields
        recognized_fields = {
            'version', 'data_source', 'theme_mode', 'color_schema', 'dynamic_background',
            'kline_period', 'chart_cache_ttl', 'hover_enabled', 'hover_show_stats', 'hover_show_chart',
            'opacity', 'crypto_pairs', 'display_limit', 'minimalist_view',
            'auto_scroll', 'scroll_interval',
            'window_x', 'window_y', 'always_on_top', 'language', 'price_change_basis',
            'auto_scroll', 'scroll_interval',
            'window_x', 'window_y', 'always_on_top', 'language', 'price_change_basis',
            'sound_mode'
        }
        filtered_data = {k: v for k, v in data.items() if k in recognized_fields}

        # Create new settings object
        new_settings = AppSettings(
            proxy=proxy_config,
            compact_mode=compact_mode_config,
            websocket=websocket_config,
            alerts=alerts_list,
            **filtered_data
        )

        # Upon successful parse, update current settings and save
        self.settings = new_settings
        self.save()
        
        # Apply immediate effects if needed (like load_language)
        load_language(self.settings.language)
        self._apply_proxy_env()


# Global settings instance
_settings_manager: Optional[SettingsManager] = None


def get_settings_manager() -> SettingsManager:
    """Get the global settings manager instance."""
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager()
        _settings_manager.load()
    return _settings_manager
