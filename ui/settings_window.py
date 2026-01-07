"""
Settings window - independent window for configuration.
Refactored to use QFluentWidgets for a modern Fluent Design interface.
"""

import webbrowser
from typing import Optional
from datetime import datetime
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon
from qfluentwidgets import (
    ScrollArea, SettingCardGroup, PushButton, PrimaryPushButton,
    FluentIcon, InfoBar, InfoBarPosition, Theme, setTheme,
    PrimaryPushSettingCard
)

from ui.widgets.setting_cards import ProxySettingCard, PairsSettingCard, ThemeSettingCard, LanguageSettingCard, DisplaySettingCard
from ui.widgets.alert_setting_card import AlertSettingCard
from ui.widgets.data_source_setting_card import DataSourceSettingCard
from config.settings import SettingsManager, ProxyConfig
from core.i18n import _


class SettingsWindow(QMainWindow):
    """Independent settings window with Fluent Design interface."""

    proxy_changed = pyqtSignal()  # Emitted when proxy settings change
    pairs_changed = pyqtSignal()  # Emitted when crypto pairs change
    theme_changed = pyqtSignal(str)  # Emitted when theme settings change
    display_changed = pyqtSignal()  # Emitted when display settings (like dynamic bg) change
    data_source_changed = pyqtSignal()  # Emitted when data source changes

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
        self.setWindowTitle(_("Settings"))
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
        from PyQt6.QtWidgets import QStackedWidget

        sidebar_title = TitleLabel(_("Settings"))
        title_color = "black" if self._theme_mode == "light" else "white"
        sidebar_title.setStyleSheet(f"padding-left: 10px; margin-bottom: 10px; color: {title_color};")
        sidebar_layout.addWidget(sidebar_title)

        # Custom Navigation Item Widget
        class NavItem(QWidget):
            clicked = pyqtSignal()
            
            def __init__(self, text, icon, parent=None, is_dark=False):
                super().__init__(parent)
                self.is_dark = is_dark
                self.is_selected = False
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
                
            def set_selected(self, selected: bool):
                self.is_selected = selected
                self._update_style()
                
            def _update_style(self):
                if self.is_selected:
                    bg = "rgba(255, 255, 255, 0.1)" if self.is_dark else "rgba(0, 0, 0, 0.05)"
                    self.setStyleSheet(f"background-color: {bg}; border-radius: 5px;")
                else:
                    self.setStyleSheet("background-color: transparent;")

            def enterEvent(self, event):
                if not self.is_selected:
                    bg = "rgba(255, 255, 255, 0.05)" if self.is_dark else "rgba(0, 0, 0, 0.03)"
                    self.setStyleSheet(f"background-color: {bg}; border-radius: 5px;")
                super().enterEvent(event)
                
            def leaveEvent(self, event):
                self._update_style()
                super().leaveEvent(event)
                
            def mousePressEvent(self, event):
                if event.button() == Qt.MouseButton.LeftButton:
                    self.clicked.emit()
                super().mousePressEvent(event)

        # Navigation Buttons Container to keep track
        self.nav_btns = []
        is_dark = self._theme_mode == "dark"

        # 2. Right Content Area (QStackedWidget)
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        self.stack_widget = QStackedWidget()
        self.stack_widget.setStyleSheet("background: transparent;")
        
        # Helper to create pages
        def create_page(group_widget):
            page_widget = QWidget()
            page_layout = QVBoxLayout(page_widget)
            page_layout.setContentsMargins(30, 30, 30, 30)
            page_layout.setSpacing(20)
            
            # Use ScrollArea for the page content
            scroll = ScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
            
            scroll_content = QWidget()
            scroll_content.setStyleSheet("background: transparent;")
            scroll_content_layout = QVBoxLayout(scroll_content)
            scroll_content_layout.setContentsMargins(0, 0, 0, 0)
            scroll_content_layout.setSpacing(20)
            
            scroll_content_layout.addWidget(group_widget)
            scroll_content_layout.addStretch(1)
            
            scroll.setWidget(scroll_content)
            page_layout.addWidget(scroll)
            
            return page_widget

        # --- Create Setting Groups ---

        # Appearance settings group
        self.appearance_group = SettingCardGroup(_("Appearance"), None)
        self.language_card = LanguageSettingCard(self.appearance_group)
        self.appearance_group.addSettingCard(self.language_card)
        self.theme_card = ThemeSettingCard(self.appearance_group)
        self.appearance_group.addSettingCard(self.theme_card)
        
        # Display Settings
        self.display_card = DisplaySettingCard(self.appearance_group)
        self.appearance_group.addSettingCard(self.display_card)
        
        # Proxy query group (Network)
        self.proxy_group = SettingCardGroup(_("Network Configuration"), None)
        
        # Data Source
        self.data_source_card = DataSourceSettingCard(self.proxy_group)
        self.proxy_group.addSettingCard(self.data_source_card)
        
        self.proxy_card = ProxySettingCard(self.proxy_group)
        self.proxy_card.test_requested.connect(self._test_connection)
        self.proxy_group.addSettingCard(self.proxy_card)
        
        # Crypto pairs management group
        self.pairs_group = SettingCardGroup(_("Trading Pairs"), None)
        self.pairs_card = PairsSettingCard(self.pairs_group)
        self.pairs_group.addSettingCard(self.pairs_card)
        
        # Price alerts group
        self.alerts_group = SettingCardGroup(_("Notifications"), None)
        self.alerts_card = AlertSettingCard(self.alerts_group)
        self.alerts_group.addSettingCard(self.alerts_card)

        # --- Add pages to stack and buttons to sidebar ---

        def add_nav_item(text, icon, group_widget):
            index = self.stack_widget.count()
            self.stack_widget.addWidget(create_page(group_widget))
            
            btn = NavItem(text, icon, self, is_dark)
            btn.clicked.connect(lambda: self._switch_view(index))
            sidebar_layout.addWidget(btn)
            self.nav_btns.append(btn)
            return btn

        add_nav_item(_("Appearance"), FluentIcon.BRUSH, self.appearance_group)
        add_nav_item(_("Network"), FluentIcon.GLOBE, self.proxy_group)
        add_nav_item(_("Trading Pairs"), FluentIcon.MARKET, self.pairs_group)
        add_nav_item(_("Notifications"), FluentIcon.RINGER, self.alerts_group)

        # About group
        self.about_group = SettingCardGroup(_("About"), None)
        
        # Version Card
        # Using PrimaryPushSettingCard but disabling button for static display
        self.version_card = PrimaryPushSettingCard(
            _("Check Update"),
            FluentIcon.INFO,
            _("Current Version"),
            "0.2.0",
            self.about_group
        )
        self.version_card.button.hide()
        self.about_group.addSettingCard(self.version_card)
        
        # GitHub Card
        self.github_card = PrimaryPushSettingCard(
            _("View"),
            FluentIcon.GITHUB,
            _("GitHub Repository"),
            _("View source code, report issues, or contribute"),
            self.about_group
        )
        self.github_card.button.setText(_("View"))
        self.github_card.button.clicked.connect(lambda: webbrowser.open("https://github.com/shiquda/crypto-monitor"))
        self.about_group.addSettingCard(self.github_card)
        
        add_nav_item(_("About"), FluentIcon.PEOPLE, self.about_group)

        sidebar_layout.addStretch(1)

        # Add Stack to content layout
        content_layout.addWidget(self.stack_widget)

        # Bottom button bar (persistent)
        btn_bar = QWidget()
        btn_bar.setStyleSheet(f"QWidget {{ background-color: {bg_color}; border-top: 1px solid #E0E0E0; }}")
        if self._theme_mode == "dark":
            btn_bar.setStyleSheet(f"QWidget {{ background-color: {bg_color}; border-top: 1px solid #333333; }}")
            
        btn_layout = QHBoxLayout(btn_bar)
        btn_layout.setContentsMargins(30, 15, 30, 20)
        btn_layout.setSpacing(10)

        self.reset_btn = PushButton(FluentIcon.SYNC, _("Reset to Defaults"))
        self.reset_btn.clicked.connect(self._reset_settings)
        btn_layout.addWidget(self.reset_btn)

        # Export Button
        self.export_btn = PushButton(FluentIcon.SHARE, _("Export Config"))
        self.export_btn.clicked.connect(self._export_settings)
        btn_layout.addWidget(self.export_btn)

        # Import Button
        self.import_btn = PushButton(FluentIcon.DOWNLOAD, _("Import Config"))
        self.import_btn.clicked.connect(self._import_settings)
        btn_layout.addWidget(self.import_btn)

        btn_layout.addStretch()

        self.save_btn = PrimaryPushButton(FluentIcon.SAVE, _("Save"))
        self.save_btn.setFixedWidth(120)
        self.save_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(self.save_btn)

        content_layout.addWidget(btn_bar)

        # Add to main layout
        main_h_layout.addWidget(sidebar)
        main_h_layout.addWidget(content_container)

        # Select first item by default
        if self.nav_btns:
            self._switch_view(0)

    def _switch_view(self, index):
        """Switch the stacked widget view."""
        self.stack_widget.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_btns):
            btn.set_selected(i == index)

    def _export_settings(self):
        """Export settings to a JSON file."""
        from PyQt6.QtWidgets import QFileDialog
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"crypto-monitor_config_{timestamp}.json"
        
        filepath, _filter = QFileDialog.getSaveFileName(
            self,
            _("Export Configuration"),
            default_filename,
            "JSON Files (*.json)"
        )
        
        if filepath:
            try:
                self._settings_manager.export_to_file(filepath)
                InfoBar.success(
                    title=_("Success"),
                    content=_("Configuration exported successfully"),
                    orient=0,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
            except Exception as e:
                InfoBar.error(
                    title=_("Error"),
                    content=f"{_('Failed to export configuration')}: {str(e)}",
                    orient=0,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )

    def _import_settings(self):
        """Import settings from a JSON file."""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        
        filepath, _filter = QFileDialog.getOpenFileName(
            self,
            _("Import Configuration"),
            "",
            "JSON Files (*.json)"
        )
        
        if filepath:
            # Confirm with user
            reply = QMessageBox.question(
                self, 
                _("Confirm Import"), 
                _("Importing configuration will overwrite your current settings. This requires a restart. Continue?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    self._settings_manager.import_from_file(filepath)
                    self._load_settings() # Reload settings into UI
                    
                    # Notify and Restart
                    msg = QMessageBox()
                    msg.setIcon(QMessageBox.Icon.Information)
                    msg.setText(_("Configuration imported successfully"))
                    msg.setInformativeText(_("The application needs to restart to apply all changes."))
                    msg.setWindowTitle(_("Success"))
                    msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                    msg.exec()

                    # Emit changes signals
                    self.proxy_changed.emit()
                    self.pairs_changed.emit()
                    self.theme_changed.emit()
                    
                    # For a clean state, better to restart app, but here we just re-applied settings
                    # and notified the user.
                except Exception as e:
                    InfoBar.error(
                        title=_("Error"),
                        content=f"{_('Failed to import configuration')}: {str(e)}",
                        orient=0,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=2000,
                        parent=self
                    )

    def _load_settings(self):
        """Load current settings into UI."""
        # Load theme mode
        theme_mode = self._settings_manager.settings.theme_mode
        self.theme_card.set_theme_mode(theme_mode)

        # Load language
        language = self._settings_manager.settings.language
        self.language_card.set_language(language)

        # Load color schema
        schema = self._settings_manager.settings.color_schema
        self.display_card.set_color_schema(schema)
        
        # Load dynamic background
        dynamic_bg = self._settings_manager.settings.dynamic_background
        self.display_card.set_dynamic_background(dynamic_bg)
        
        # Load data source
        source = self._settings_manager.settings.data_source
        self.data_source_card.set_data_source(source)

        # Load proxy configuration
        proxy = self._settings_manager.settings.proxy
        self.proxy_card.set_proxy_config(proxy)

        # Load crypto pairs
        pairs = self._settings_manager.settings.crypto_pairs
        self.pairs_card.set_pairs(pairs)

    def _save_settings(self):
        """Save settings."""
        # ... (checks) ...
        # Check if theme changed
        old_theme = self._settings_manager.settings.theme_mode
        new_theme = self.theme_card.get_theme_mode()
        theme_changed = old_theme != new_theme

        # Check if language changed
        old_lang = self._settings_manager.settings.language
        new_lang = self.language_card.get_language()
        lang_changed = old_lang != new_lang
        
        # Check if data source changed
        old_source = self._settings_manager.settings.data_source
        new_source = self.data_source_card.get_data_source()
        source_changed = old_source != new_source

        # Check if color schema changed
        old_schema = self._settings_manager.settings.color_schema
        new_schema = self.display_card.get_color_schema()
        # schema_changed = old_schema != new_schema
        
        # Check if dynamic background changed
        old_dynamic_bg = self._settings_manager.settings.dynamic_background
        new_dynamic_bg = self.display_card.get_dynamic_background()
        dynamic_bg_changed = old_dynamic_bg != new_dynamic_bg 

        # Get theme mode from card
        self._settings_manager.update_theme(new_theme)
        
        # Get language from card
        self._settings_manager.update_language(new_lang)

        # Update color schema
        self._settings_manager.update_color_schema(new_schema)
        
        # Update dynamic background
        self._settings_manager.update_dynamic_background(new_dynamic_bg)
        
        # Update data source
        self._settings_manager.update_data_source(new_source)

        # Get proxy configuration from card
        proxy = self.proxy_card.get_proxy_config()
        self._settings_manager.update_proxy(proxy)

        # Get crypto pairs from card
        pairs = self.pairs_card.get_pairs()
        self._settings_manager.update_pairs(pairs)

        # Show success message with restart hint if theme or language changed
        if theme_changed or lang_changed:
            InfoBar.success(
                title=_("Settings Saved"),
                content=_("Please restart the application for changes to take effect"),
                orient=0,  # Qt.Horizontal
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=4000,
                parent=self
            )
        else:
            InfoBar.success(
                title=_("Settings Saved"),
                content=_("Your settings have been saved successfully"),
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
        if source_changed:
            QTimer.singleShot(100, lambda: self.data_source_changed.emit())
        if dynamic_bg_changed:
            QTimer.singleShot(100, lambda: self.display_changed.emit())

    def _reset_settings(self):
        """Reset settings to defaults."""
        # Reset proxy to defaults
        default_proxy = ProxyConfig()
        self.proxy_card.set_proxy_config(default_proxy)
        self._settings_manager.update_proxy(default_proxy)

        # Show info message
        InfoBar.info(
            title=_("Settings Reset"),
            content=_("Settings have been reset to defaults"),
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
                self.proxy_card.show_test_result(True, _("Proxy server is reachable"))
            else:
                self.proxy_card.show_test_result(False, f"{_('Connection failed')} ({_('error code')}: {result})")
        except socket.error as e:
            self.proxy_card.show_test_result(False, f"{_('Socket error')}: {str(e)}")
        except Exception as e:
            self.proxy_card.show_test_result(False, f"{_('Unexpected error')}: {str(e)}")
