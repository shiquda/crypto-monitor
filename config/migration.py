"""
Configuration Migration System for Crypto Monitor.
Handles automatic migration of configuration files across application versions.
"""

import json
import re
import shutil
import time
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


class ConfigVersion(Enum):
    """
    Configuration file version enumeration.

    Version History:
    - V1_0_0: Initial version without explicit version field
    - V2_0_0: Added compact_mode configuration and version field
    - V2_1_0: Added WebSocket reconnection settings
    - V3_0_0: Future version for multi-source support
    """

    V1_0_0 = "1.0.0"
    V2_0_0 = "2.0.0"
    V2_1_0 = "2.1.0"
    V3_0_0 = "3.0.0"

    @classmethod
    def from_string(cls, version_str: Optional[str]) -> 'ConfigVersion':
        """Convert version string to enum, defaulting to V1_0_0 for legacy configs."""
        if not version_str:
            return cls.V1_0_0

        for version in cls:
            if version.value == version_str:
                return version

        # Unknown version, return oldest version for safety
        return cls.V1_0_0

    def __str__(self) -> str:
        return self.value


class MigrationError(Exception):
    """Exception raised during configuration migration."""
    pass


class BaseMigration(ABC):
    """
    Abstract base class for configuration migrations.

    Each migration handles upgrading from one specific version to another.
    """

    @property
    @abstractmethod
    def from_version(self) -> ConfigVersion:
        """Source version for this migration."""
        pass

    @property
    @abstractmethod
    def to_version(self) -> ConfigVersion:
        """Target version for this migration."""
        pass

    @abstractmethod
    def validate(self, config: Dict[str, Any]) -> bool:
        """
        Validate that the config is eligible for this migration.

        Args:
            config: Configuration dictionary

        Returns:
            True if config should be migrated by this migration, False otherwise
        """
        pass

    @abstractmethod
    def migrate(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform the actual migration.

        Args:
            config: Configuration dictionary to migrate

        Returns:
            Migrated configuration dictionary

        Raises:
            MigrationError: If migration fails
        """
        pass

    @property
    def name(self) -> str:
        """Human-readable migration name."""
        return f"{self.from_version.value} → {self.to_version.value}"


class MigrationV1ToV2(BaseMigration):
    """
    Migration from V1.0.0 (no version) to V2.0.0.

    Changes:
    - Add version field
    - Add compact_mode configuration block
    """

    @property
    def from_version(self) -> ConfigVersion:
        return ConfigVersion.V1_0_0

    @property
    def to_version(self) -> ConfigVersion:
        return ConfigVersion.V2_0_0

    def validate(self, config: Dict[str, Any]) -> bool:
        """Validate that this is a V1.0.0 config (no version)."""
        # V1.0.0 configs don't have a version field
        # compact_mode may exist but be a bool or other type (migration artifact)
        return 'version' not in config

    def migrate(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Perform V1.0.0 → V2.0.0 migration."""
        # Add version field
        config['version'] = '2.0.0'

        # Add compact mode configuration
        config['compact_mode'] = {
            'enabled': False,
            'auto_scroll': True,
            'scroll_interval': 5,
            'window_x': config.get('window_x', 100),
            'window_y': config.get('window_y', 100)
        }

        return config


class MigrationV2ToV21(BaseMigration):
    """
    Migration from V2.0.0 to V2.1.0.

    Changes:
    - Update version field to 2.1.0
    - Add WebSocket reconnection settings
    """

    @property
    def from_version(self) -> ConfigVersion:
        return ConfigVersion.V2_0_0

    @property
    def to_version(self) -> ConfigVersion:
        return ConfigVersion.V2_1_0

    def validate(self, config: Dict[str, Any]) -> bool:
        """Validate that this is a V2.0.0 config."""
        return config.get('version') == '2.0.0'

    def migrate(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Perform V2.0.0 → V2.1.0 migration."""
        # Add WebSocket reconnection settings
        if 'websocket' not in config:
            config['websocket'] = {
                'auto_reconnect': True,
                'reconnect_initial_delay': 1.0,
                'reconnect_max_delay': 30.0,
                'backoff_factor': 2.0,
                'heartbeat_timeout': 60,
                'connection_timeout': 60
            }

        # Update version
        config['version'] = '2.1.0'

        return config


class ConfigValidator:
    """
    Configuration data validator.

    Validates configuration structure and values.
    """

    @staticmethod
    def validate_required_fields(config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate that all required fields are present.

        Args:
            config: Configuration dictionary

        Returns:
            Tuple of (is_valid, error_message)
        """
        required_fields = ['theme_mode', 'opacity', 'crypto_pairs']

        for field in required_fields:
            if field not in config:
                return False, f"Missing required field: {field}"

        return True, ""

    @staticmethod
    def validate_pairs(config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate crypto pairs format.

        Args:
            config: Configuration dictionary

        Returns:
            Tuple of (is_valid, error_message)
        """
        pairs = config.get('crypto_pairs', [])

        if not isinstance(pairs, list):
            return False, "crypto_pairs must be a list"

        for pair in pairs:
            if not isinstance(pair, str):
                return False, f"Invalid pair type: {pair} (must be string)"

            if not re.match(r'^[A-Z0-9]+-[A-Z0-9]+$', pair):
                return False, f"Invalid pair format: {pair} (must be like BTC-USDT)"

        return True, ""

    @staticmethod
    def validate_theme_mode(config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate theme mode value.

        Args:
            config: Configuration dictionary

        Returns:
            Tuple of (is_valid, error_message)
        """
        valid_modes = ['light', 'dark', 'auto']
        theme_mode = config.get('theme_mode', 'light')

        if theme_mode not in valid_modes:
            return False, f"Invalid theme_mode: {theme_mode} (must be one of {valid_modes})"

        return True, ""

    @staticmethod
    def validate_opacity(config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate opacity value.

        Args:
            config: Configuration dictionary

        Returns:
            Tuple of (is_valid, error_message)
        """
        opacity = config.get('opacity', 100)

        if not isinstance(opacity, int):
            return False, f"opacity must be an integer, got {type(opacity).__name__}"

        if not 0 <= opacity <= 100:
            return False, f"opacity must be between 0 and 100, got {opacity}"

        return True, ""

    @staticmethod
    def validate_proxy(config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate proxy configuration.

        Args:
            config: Configuration dictionary

        Returns:
            Tuple of (is_valid, error_message)
        """
        proxy = config.get('proxy', {})

        if not isinstance(proxy, dict):
            return False, "proxy must be a dictionary"

        # Check type field
        proxy_type = proxy.get('type', 'http')
        if proxy_type not in ['http', 'socks5']:
            return False, f"proxy.type must be 'http' or 'socks5', got {proxy_type}"

        # Check port
        port = proxy.get('port', 7890)
        if not isinstance(port, int) or not 1 <= port <= 65535:
            return False, f"proxy.port must be between 1 and 65535, got {port}"

        return True, ""

    @staticmethod
    def validate_all(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Run all validations.

        Args:
            config: Configuration dictionary

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        validations = [
            ConfigValidator.validate_required_fields,
            ConfigValidator.validate_pairs,
            ConfigValidator.validate_theme_mode,
            ConfigValidator.validate_opacity,
            ConfigValidator.validate_proxy,
        ]

        for validation in validations:
            is_valid, error = validation(config)
            if not is_valid:
                errors.append(error)

        return len(errors) == 0, errors


class MigrationManager:
    """
    Configuration migration manager.

    Handles automatic migration of configuration files, including:
    - Version detection
    - Migration chain execution
    - Validation
    - Backup and rollback
    """

    def __init__(self, config_file: Path, current_version: ConfigVersion):
        """
        Initialize migration manager.

        Args:
            config_file: Path to configuration file
            current_version: Current application configuration version
        """
        self.config_file = config_file
        self.current_version = current_version
        self.migrations: List[BaseMigration] = []
        self.backup_dir = config_file.parent / 'backups'
        self.backup_dir.mkdir(exist_ok=True)

        # Register built-in migrations
        self._register_builtin_migrations()

    def _register_builtin_migrations(self):
        """Register all built-in migration handlers."""
        self.register_migration(MigrationV1ToV2())
        self.register_migration(MigrationV2ToV21())

    def register_migration(self, migration: BaseMigration):
        """
        Register a migration handler.

        Args:
            migration: Migration instance
        """
        self.migrations.append(migration)

        # Keep migrations in order
        self.migrations.sort(key=lambda m: m.from_version.value)

    def _get_config_version(self, config: Dict[str, Any]) -> ConfigVersion:
        """
        Detect configuration version.

        Args:
            config: Configuration dictionary

        Returns:
            Detected version
        """
        version_str = config.get('version')
        return ConfigVersion.from_string(version_str)

    def _find_migration_path(self, from_version: ConfigVersion, to_version: ConfigVersion) -> List[BaseMigration]:
        """
        Find migration path from one version to another.

        Args:
            from_version: Source version
            to_version: Target version

        Returns:
            List of migrations to apply in order

        Raises:
            MigrationError: If no migration path exists
        """
        # Simple linear migration chain for now
        # Can be extended to support branching in the future

        path = []
        current = from_version

        while current != to_version:
            # Find next migration
            next_migration = None
            for migration in self.migrations:
                if migration.from_version == current:
                    next_migration = migration
                    break

            if next_migration is None:
                raise MigrationError(
                    f"No migration available from {current.value} to {to_version.value}"
                )

            path.append(next_migration)
            current = next_migration.to_version

        return path

    def _create_backup(self, config: Dict[str, Any], version: ConfigVersion) -> Path:
        """
        Create a backup of the configuration.

        Args:
            config: Configuration dictionary
            version: Version of the configuration

        Returns:
            Path to backup file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"settings_{timestamp}_v{version.value}.json"
        backup_path = self.backup_dir / backup_filename

        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        return backup_path

    def _cleanup_old_backups(self, max_backups: int = 5):
        """
        Clean up old backup files, keeping only the most recent ones.

        Args:
            max_backups: Maximum number of backups to keep
        """
        backup_files = sorted(
            self.backup_dir.glob('settings_*.json'),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        for backup_file in backup_files[max_backups:]:
            backup_file.unlink()

    def migrate_if_needed(self, force: bool = False) -> Tuple[bool, Optional[str], Optional[Path]]:
        """
        Migrate configuration if needed.

        Args:
            force: Force migration even if up to date

        Returns:
            Tuple of (migrated, message, backup_path)
            - migrated: True if migration was performed
            - message: Status message
            - backup_path: Path to backup file (if created)

        Raises:
            MigrationError: If migration fails
        """
        # Load current config
        if not self.config_file.exists():
            # No config file, nothing to migrate
            return False, "No configuration file found", None

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            raise MigrationError(f"Failed to read configuration file: {e}")

        # Detect current config version
        config_version = self._get_config_version(config)

        # Check if migration is needed
        if not force and config_version == self.current_version:
            return False, f"Configuration already at version {self.current_version.value}", None

        # Find migration path
        try:
            migration_path = self._find_migration_path(config_version, self.current_version)
        except MigrationError as e:
            raise MigrationError(f"Migration path not found: {e}")

        if not migration_path:
            return False, f"Configuration already at version {self.current_version.value}", None

        # Create backup before migration
        backup_path = self._create_backup(config, config_version)

        # Apply migrations
        current_config = config.copy()
        for migration in migration_path:
            # Validate before migration
            if not migration.validate(current_config):
                raise MigrationError(
                    f"Configuration is not valid for migration {migration.name}"
                )

            # Perform migration
            current_config = migration.migrate(current_config)

            # Validate after migration
            is_valid, errors = ConfigValidator.validate_all(current_config)
            if not is_valid:
                raise MigrationError(
                    f"Migration {migration.name} produced invalid configuration: {errors}"
                )

        # Save migrated configuration
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(current_config, f, indent=2, ensure_ascii=False)

        # Clean up old backups
        self._cleanup_old_backups()

        # Create migration log entry
        self._log_migration(config_version, self.current_version, migration_path, backup_path)

        message = f"Migrated configuration from {config_version.value} to {self.current_version.value}"
        return True, message, backup_path

    def _log_migration(self, from_version: ConfigVersion, to_version: ConfigVersion,
                       migration_path: List[BaseMigration], backup_path: Path):
        """
        Log migration event.

        Args:
            from_version: Source version
            to_version: Target version
            migration_path: Applied migrations
            backup_path: Backup file path
        """
        log_file = self.config_file.parent / 'migrations.log'
        timestamp = datetime.now().isoformat()

        migration_names = " -> ".join([m.name for m in migration_path])

        log_entry = (
            f"[{timestamp}] Migrated {from_version.value} → {to_version.value}\n"
            f"  Path: {migration_names}\n"
            f"  Backup: {backup_path}\n\n"
        )

        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
