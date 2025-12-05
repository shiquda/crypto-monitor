"""
Settings window - independent window for configuration.
Refactored to use QFluentWidgets for a modern Fluent Design interface.
"""

from typing import Optional
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon
from qfluentwidgets import (
    ScrollArea, SettingCardGroup, PushButton, PrimaryPushButton,
    FluentIcon, InfoBar, InfoBarPosition, Theme, setTheme
)

from ui.widgets.setting_cards import ProxySettingCard, PairsSettingCard, ThemeSettingCard, CompactModeSettingCard
from config.settings import SettingsManager, ProxyConfig


class SettingsWindow(QMainWindow):
    """Independent settings window with Fluent Design interface."""

    proxy_changed = pyqtSignal()  # Emitted when proxy settings change
    pairs_changed = pyqtSignal()  # Emitted when crypto pairs change
    theme_changed = pyqtSignal()  # Emitted when theme settings change
    compact_mode_changed = pyqtSignal()  # Emitted when compact mode settings change

    def __init__(self, settings_manager: SettingsManager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._settings_manager = settings_manager

        # Apply theme based on settings
        theme_mode = settings_manager.settings.theme_mode
        setTheme(Theme.DARK if theme_mode == "dark" else Theme.LIGHT)

        # Store theme mode for UI setup
        self._theme_mode = theme_mode

        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        """Setup the settings window UI with QFluentWidgets."""
        self.setWindowTitle("Settings")
        self.setMinimumSize(700, 650)
        self.resize(700, 650)
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowCloseButtonHint
        )
        self.setWindowIcon(QIcon("assets/icons/crypto-monitor.png"))

        # Set theme-based background color
        bg_color = "rgb(32, 32, 32)" if self._theme_mode == "dark" else "rgb(249, 249, 249)"

        self.setStyleSheet(f"QMainWindow {{ background-color: {bg_color}; }}")

        # Central widget
        central = QWidget()
        central.setStyleSheet(f"QWidget {{ background-color: {bg_color}; }}")
        self.setCentralWidget(central)

        # Main layout
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Scroll area for settings content
        scroll_area = ScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(f"QScrollArea {{ border: none; background-color: {bg_color}; }}")

        # Content widget inside scroll area
        content_widget = QWidget()
        content_widget.setStyleSheet(f"QWidget {{ background-color: {bg_color}; }}")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(60, 30, 60, 30)
        content_layout.setSpacing(20)

        # Title label
        from qfluentwidgets import TitleLabel
        title = TitleLabel("Settings")
        content_layout.addWidget(title)

        # Appearance settings group
        appearance_group = SettingCardGroup("Appearance", content_widget)
        self.theme_card = ThemeSettingCard(appearance_group)
        self.compact_mode_card = CompactModeSettingCard(appearance_group)
        appearance_group.addSettingCard(self.theme_card)
        appearance_group.addSettingCard(self.compact_mode_card)
        content_layout.addWidget(appearance_group)

        # Proxy configuration group
        proxy_group = SettingCardGroup("Network Configuration", content_widget)
        self.proxy_card = ProxySettingCard(proxy_group)
        self.proxy_card.test_requested.connect(self._test_connection)
        proxy_group.addSettingCard(self.proxy_card)
        content_layout.addWidget(proxy_group)

        # Crypto pairs management group
        pairs_group = SettingCardGroup("Trading Pairs", content_widget)
        self.pairs_card = PairsSettingCard(pairs_group)
        pairs_group.addSettingCard(self.pairs_card)
        content_layout.addWidget(pairs_group)

        # Add stretch to push content to top
        content_layout.addStretch(1)

        # Set content widget to scroll area
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)

        # Bottom button bar
        btn_bar = QWidget()
        btn_bar.setStyleSheet(f"QWidget {{ background-color: {bg_color}; }}")
        btn_layout = QHBoxLayout(btn_bar)
        btn_layout.setContentsMargins(60, 15, 60, 20)
        btn_layout.setSpacing(10)

        self.reset_btn = PushButton(FluentIcon.SYNC, "Reset to Defaults")
        self.reset_btn.clicked.connect(self._reset_settings)
        btn_layout.addWidget(self.reset_btn)

        btn_layout.addStretch()

        self.save_btn = PrimaryPushButton(FluentIcon.SAVE, "Save")
        self.save_btn.setFixedWidth(120)
        self.save_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(self.save_btn)

        main_layout.addWidget(btn_bar)

    def _load_settings(self):
        """Load current settings into UI."""
        # Load theme mode
        theme_mode = self._settings_manager.settings.theme_mode
        self.theme_card.set_theme_mode(theme_mode)

        # Load compact mode settings
        compact_config = {
            'enabled': self._settings_manager.settings.compact_mode,
            'auto_scroll': self._settings_manager.settings.compact_auto_scroll,
            'scroll_interval': self._settings_manager.settings.compact_scroll_interval
        }
        self.compact_mode_card.set_compact_mode_config(compact_config)

        # Load proxy configuration
        proxy = self._settings_manager.settings.proxy
        self.proxy_card.set_proxy_config(proxy)

        # Load crypto pairs
        pairs = self._settings_manager.settings.crypto_pairs
        self.pairs_card.set_pairs(pairs)

    def _save_settings(self):
        """Save settings."""
        # Check if theme changed
        old_theme = self._settings_manager.settings.theme_mode
        new_theme = self.theme_card.get_theme_mode()
        theme_changed = old_theme != new_theme

        # Check if compact mode changed
        old_compact_mode = self._settings_manager.settings.compact_mode
        compact_config = self.compact_mode_card.get_compact_mode_config()
        compact_mode_changed = old_compact_mode != compact_config['enabled']

        # Get theme mode from card
        self._settings_manager.update_theme(new_theme)

        # Get compact mode configuration from card
        self._settings_manager.settings.compact_mode = compact_config['enabled']
        self._settings_manager.settings.compact_auto_scroll = compact_config['auto_scroll']
        self._settings_manager.settings.compact_scroll_interval = compact_config['scroll_interval']
        self._settings_manager.save()

        # Get proxy configuration from card
        proxy = self.proxy_card.get_proxy_config()
        self._settings_manager.update_proxy(proxy)

        # Get crypto pairs from card
        pairs = self.pairs_card.get_pairs()
        self._settings_manager.update_pairs(pairs)

        # Show success message with restart hint if theme changed
        if theme_changed:
            InfoBar.success(
                title="Settings Saved",
                content="Please restart the application for theme changes to take effect",
                orient=0,  # Qt.Horizontal
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=4000,
                parent=self
            )
        else:
            InfoBar.success(
                title="Settings Saved",
                content="Your settings have been saved successfully",
                orient=0,  # Qt.Horizontal
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

        # Emit signals AFTER showing InfoBar (using QTimer to defer heavy operations)
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(100, lambda: self.proxy_changed.emit())
        QTimer.singleShot(100, lambda: self.pairs_changed.emit())
        if theme_changed:
            QTimer.singleShot(100, lambda: self.theme_changed.emit())
        if compact_mode_changed:
            QTimer.singleShot(100, lambda: self.compact_mode_changed.emit())

    def _reset_settings(self):
        """Reset settings to defaults."""
        # Reset proxy to defaults
        default_proxy = ProxyConfig()
        self.proxy_card.set_proxy_config(default_proxy)
        self._settings_manager.update_proxy(default_proxy)

        # Show info message
        InfoBar.info(
            title="Settings Reset",
            content="Settings have been reset to defaults",
            orient=0,  # Qt.Horizontal
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )

        # Emit signal
        self.proxy_changed.emit()

    def _test_connection(self):
        """Test proxy connection."""
        # Get current proxy config
        proxy = self.proxy_card.get_proxy_config()

        # Test connection (simple check)
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((proxy.host, proxy.port))
            sock.close()

            if result == 0:
                self.proxy_card.show_test_result(True, "Proxy server is reachable")
            else:
                self.proxy_card.show_test_result(False, f"Connection failed (error code: {result})")
        except socket.error as e:
            self.proxy_card.show_test_result(False, f"Socket error: {str(e)}")
        except Exception as e:
            self.proxy_card.show_test_result(False, f"Unexpected error: {str(e)}")
