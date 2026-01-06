"""
Settings window - independent window for configuration.
Refactored to use QFluentWidgets for a modern Fluent Design interface.
"""

from typing import Optional
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon
from qfluentwidgets import (
    ScrollArea, SettingCardGroup, PushButton, PrimaryPushButton,
    FluentIcon, InfoBar, InfoBarPosition, Theme, setTheme
)

from ui.widgets.setting_cards import ProxySettingCard, PairsSettingCard, ThemeSettingCard
from ui.widgets.alert_setting_card import AlertSettingCard
from config.settings import SettingsManager, ProxyConfig


class SettingsWindow(QMainWindow):
    """Independent settings window with Fluent Design interface."""

    proxy_changed = pyqtSignal()  # Emitted when proxy settings change
    pairs_changed = pyqtSignal()  # Emitted when crypto pairs change
    theme_changed = pyqtSignal()  # Emitted when theme settings change

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
        flags = Qt.WindowType.Window | Qt.WindowType.WindowCloseButtonHint
        if self.parent() and (self.parent().windowFlags() & Qt.WindowType.WindowStaysOnTopHint):
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setWindowIcon(QIcon("assets/icons/crypto-monitor.png"))

        # Set theme-based background color
        bg_color = "rgb(32, 32, 32)" if self._theme_mode == "dark" else "rgb(249, 249, 249)"

        self.setStyleSheet(f"QMainWindow {{ background-color: {bg_color}; }}")

        # Central widget
        central = QWidget()
        central.setStyleSheet(f"QWidget {{ background-color: {bg_color}; }}")
        self.setCentralWidget(central)

        # Main layout (Horizontal: Sidebar | Content)
        main_h_layout = QHBoxLayout(central)
        main_h_layout.setContentsMargins(0, 0, 0, 0)
        main_h_layout.setSpacing(0)

        # 1. Sidebar
        sidebar = QWidget()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet(f"QWidget {{ background-color: {bg_color}; border-right: 1px solid #E0E0E0; }}")
        if self._theme_mode == "dark":
             sidebar.setStyleSheet(f"QWidget {{ background-color: {bg_color}; border-right: 1px solid #333333; }}")
        
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 20, 10, 20)
        sidebar_layout.setSpacing(5)

        # Sidebar Title
        from qfluentwidgets import TitleLabel, TransparentToolButton, BodyLabel
        sidebar_title = TitleLabel("Settings")
        title_color = "black" if self._theme_mode == "light" else "white"
        sidebar_title.setStyleSheet(f"padding-left: 10px; margin-bottom: 10px; color: {title_color};")
        sidebar_layout.addWidget(sidebar_title)

        # Custom Navigation Item Widget
        class NavItem(QWidget):
            clicked = pyqtSignal()
            
            def __init__(self, text, icon, parent=None, is_dark=False):
                super().__init__(parent)
                self.is_dark = is_dark
                self.setFixedHeight(40)
                self.setCursor(Qt.CursorShape.PointingHandCursor)
                
                layout = QHBoxLayout(self)
                layout.setContentsMargins(10, 0, 10, 0)
                layout.setSpacing(12)
                
                # Icon
                self.icon_label = QLabel()
                params = Qt.GlobalColor.white if is_dark else Qt.GlobalColor.black
                self.icon_label.setPixmap(icon.icon(params).pixmap(16, 16))
                layout.addWidget(self.icon_label)
                
                # Text
                self.text_label = BodyLabel(text)
                text_color = "white" if is_dark else "black"
                self.text_label.setStyleSheet(f"color: {text_color}; background: transparent; border: none;")
                layout.addWidget(self.text_label)
                
                layout.addStretch()
                
            def enterEvent(self, event):
                bg = "rgba(255, 255, 255, 0.1)" if self.is_dark else "rgba(0, 0, 0, 0.05)"
                self.setStyleSheet(f"background-color: {bg}; border-radius: 5px;")
                super().enterEvent(event)
                
            def leaveEvent(self, event):
                self.setStyleSheet("background-color: transparent;")
                super().leaveEvent(event)
                
            def mousePressEvent(self, event):
                if event.button() == Qt.MouseButton.LeftButton:
                    self.clicked.emit()
                super().mousePressEvent(event)

        # Navigation Buttons
        self.nav_btns = []
        is_dark = self._theme_mode == "dark"
        
        def create_nav_btn(text, icon, target_group):
            btn = NavItem(text, icon, self, is_dark)
            btn.clicked.connect(lambda: self._scroll_to_group(target_group))
            sidebar_layout.addWidget(btn)
            return btn

        # 2. Right Content Area
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Scroll area for settings content
        self.scroll_area = ScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(f"QScrollArea {{ border: none; background-color: {bg_color}; }}")

        # Content widget inside scroll area
        content_widget = QWidget()
        content_widget.setStyleSheet(f"QWidget {{ background-color: {bg_color}; }}")
        scroll_layout = QVBoxLayout(content_widget)
        scroll_layout.setContentsMargins(30, 30, 30, 30)
        scroll_layout.setSpacing(20)

        # Title for Content (optional, or kept as page title)
        # We can remove the "Settings" title from here since it's on the sidebar now
        # content_title = TitleLabel("Settings")
        # scroll_layout.addWidget(content_title)

        # Appearance settings group
        self.appearance_group = SettingCardGroup("Appearance", content_widget)
        self.theme_card = ThemeSettingCard(self.appearance_group)
        self.appearance_group.addSettingCard(self.theme_card)
        scroll_layout.addWidget(self.appearance_group)

        # Proxy configuration group
        self.proxy_group = SettingCardGroup("Network Configuration", content_widget)
        self.proxy_card = ProxySettingCard(self.proxy_group)
        self.proxy_card.test_requested.connect(self._test_connection)
        self.proxy_group.addSettingCard(self.proxy_card)
        scroll_layout.addWidget(self.proxy_group)

        # Crypto pairs management group
        self.pairs_group = SettingCardGroup("Trading Pairs", content_widget)
        self.pairs_card = PairsSettingCard(self.pairs_group)
        self.pairs_group.addSettingCard(self.pairs_card)
        scroll_layout.addWidget(self.pairs_group)

        # Price alerts group
        self.alerts_group = SettingCardGroup("Notifications", content_widget)
        self.alerts_card = AlertSettingCard(self.alerts_group)
        self.alerts_group.addSettingCard(self.alerts_card)
        scroll_layout.addWidget(self.alerts_group)

        # Add stretch to push content to top
        scroll_layout.addStretch(1)

        # Set content widget to scroll area
        self.scroll_area.setWidget(content_widget)
        content_layout.addWidget(self.scroll_area)

        # Bottom button bar
        btn_bar = QWidget()
        btn_bar.setStyleSheet(f"QWidget {{ background-color: {bg_color}; border-top: 1px solid #E0E0E0; }}")
        if self._theme_mode == "dark":
            btn_bar.setStyleSheet(f"QWidget {{ background-color: {bg_color}; border-top: 1px solid #333333; }}")
            
        btn_layout = QHBoxLayout(btn_bar)
        btn_layout.setContentsMargins(30, 15, 30, 20)
        btn_layout.setSpacing(10)

        self.reset_btn = PushButton(FluentIcon.SYNC, "Reset to Defaults")
        self.reset_btn.clicked.connect(self._reset_settings)
        btn_layout.addWidget(self.reset_btn)

        btn_layout.addStretch()

        self.save_btn = PrimaryPushButton(FluentIcon.SAVE, "Save")
        self.save_btn.setFixedWidth(120)
        self.save_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(self.save_btn)

        content_layout.addWidget(btn_bar)

        # Add Sidebar items now that groups are created
        create_nav_btn("Appearance", FluentIcon.BRUSH, self.appearance_group)
        create_nav_btn("Network", FluentIcon.GLOBE, self.proxy_group)
        create_nav_btn("Trading Pairs", FluentIcon.MARKET, self.pairs_group)
        create_nav_btn("Notifications", FluentIcon.RINGER, self.alerts_group)
        
        sidebar_layout.addStretch(1)

        # Add to main layout
        main_h_layout.addWidget(sidebar)
        main_h_layout.addWidget(content_container)

    def _scroll_to_group(self, group_widget):
        """Scroll to make the group widget visible."""
        self.scroll_area.ensureWidgetVisible(group_widget)

    def _load_settings(self):
        """Load current settings into UI."""
        # Load theme mode
        theme_mode = self._settings_manager.settings.theme_mode
        self.theme_card.set_theme_mode(theme_mode)

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

        # Get theme mode from card
        self._settings_manager.update_theme(new_theme)

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
