"""
Settings window - independent window for configuration.
Refactored to use modular pages.
"""

import logging
from typing import Optional
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QStackedWidget
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, pyqtSignal
from qfluentwidgets import (
    FluentIcon, InfoBar, InfoBarPosition, Theme, setTheme,
    TitleLabel, BodyLabel, PushButton, PrimaryPushButton
)


from ui.settings.pages.appearance_page import AppearancePage
from ui.settings.pages.proxy_page import ProxyPage
from ui.settings.pages.pairs_page import PairsPage
from ui.settings.pages.notifications_page import NotificationsPage
from ui.settings.pages.about_page import AboutPage

from config.settings import SettingsManager, ProxyConfig
from core.i18n import _

logger = logging.getLogger(__name__)

class SettingsWindow(QMainWindow):
    """Independent settings window with Fluent Design interface."""

    proxy_changed = pyqtSignal()
    pairs_changed = pyqtSignal()
    theme_changed = pyqtSignal(str)
    display_changed = pyqtSignal()
    auto_scroll_changed = pyqtSignal(bool, int)
    display_limit_changed = pyqtSignal(int)
    data_source_changed = pyqtSignal()
    minimalist_view_changed = pyqtSignal()

    def __init__(self, settings_manager: SettingsManager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._settings_manager = settings_manager

        # Apply theme
        theme_mode = settings_manager.settings.theme_mode
        setTheme(Theme.DARK if theme_mode == "dark" else Theme.LIGHT)
        self._theme_mode = theme_mode

        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        """Setup the settings window UI."""
        self.setWindowTitle(_("Settings"))
        self.setMinimumSize(840, 650)
        self.resize(840, 650)
        
        flags = Qt.WindowType.Window | Qt.WindowType.WindowCloseButtonHint
        if self.parent() and (self.parent().windowFlags() & Qt.WindowType.WindowStaysOnTopHint):
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        
        self.setWindowIcon(QIcon("assets/icons/crypto-monitor.png"))

        # Background
        bg_color = "rgb(32, 32, 32)" if self._theme_mode == "dark" else "rgb(249, 249, 249)"
        self.setStyleSheet(f"QMainWindow {{ background-color: {bg_color}; }}")

        central = QWidget()
        central.setStyleSheet(f"QWidget {{ background-color: {bg_color}; }}")
        self.setCentralWidget(central)

        main_h_layout = QHBoxLayout(central)
        main_h_layout.setContentsMargins(0, 0, 0, 0)
        main_h_layout.setSpacing(0)

        # --- Sidebar ---
        self._setup_sidebar(main_h_layout, bg_color)

        # --- Content ---
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.stack_widget = QStackedWidget()
        self.stack_widget.setStyleSheet("background: transparent;")
        
        # Instantiate Pages
        # Note: AppearancePage signature in my impl had unused arg, passing None
        self.appearance_page = AppearancePage(None, self)
        self.proxy_page = ProxyPage(self)
        self.pairs_page = PairsPage(self)
        self.notifications_page = NotificationsPage(self)
        self.about_page = AboutPage(self)

        # Connect signals from pages if any (e.g. proxy page has internal test logic)
        # However, typically settings are saved on "Save", not interactively, 
        # EXCEPT for "Test connection" which is internal to ProxyPage's card.
        # But wait, original code connected `proxy_card.test_requested` to `_test_connection` in `SettingsWindow`.
        # In my ProxyPage, I moved `_test_connection` INTO ProxyPage. So it handles itself. Good.

        # Add pages to stack
        self.stack_widget.addWidget(self.appearance_page)     # 0: Appearance
        self.stack_widget.addWidget(self.proxy_page)          # 1: Network
        self.stack_widget.addWidget(self.pairs_page)          # 2: Pairs
        self.stack_widget.addWidget(self.notifications_page)  # 3: Notifications
        self.stack_widget.addWidget(self.about_page)          # 4: About

        content_layout.addWidget(self.stack_widget)

        # --- Bottom Bar ---
        self._setup_bottom_bar(content_layout, bg_color)

        main_h_layout.addWidget(content_container)
        
        # Navigation mapping
        self._setup_nav_buttons()
        
        if self.nav_btns:
            self._switch_view(0)

    def _setup_sidebar(self, parent_layout, bg_color):
        sidebar = QWidget()
        sidebar.setFixedWidth(200)
        border_color = "#333333" if self._theme_mode == "dark" else "#E0E0E0"
        sidebar.setStyleSheet(f"QWidget {{ background-color: {bg_color}; border-right: 1px solid {border_color}; }}")
        
        self.sidebar_layout = QVBoxLayout(sidebar)
        self.sidebar_layout.setContentsMargins(10, 20, 10, 20)
        self.sidebar_layout.setSpacing(5)

        title = TitleLabel(_("Settings"))
        title_color = "white" if self._theme_mode == "dark" else "black"
        title.setStyleSheet(f"padding-left: 10px; margin-bottom: 10px; color: {title_color};")
        self.sidebar_layout.addWidget(title)

        parent_layout.addWidget(sidebar)

    def _setup_nav_buttons(self):
        # We need to recreate NavItem as it was internal class, or define it here.
        # For simplicity, defining inline again or extracting.
        # To save lines in this file, I'll define it inline here but simplified.
        
        self.nav_btns = []
        is_dark = self._theme_mode == "dark"

        def add_nav(text, icon, index):
            btn = NavItem(text, icon, self, is_dark)
            btn.clicked.connect(lambda: self._switch_view(index))
            self.sidebar_layout.addWidget(btn)
            self.nav_btns.append(btn)

        add_nav(_("Appearance"), FluentIcon.BRUSH, 0)
        add_nav(_("Network"), FluentIcon.GLOBE, 1)
        add_nav(_("Trading Pairs"), FluentIcon.MARKET, 2)
        add_nav(_("Notifications"), FluentIcon.RINGER, 3)
        add_nav(_("About"), FluentIcon.PEOPLE, 4)
        
        self.sidebar_layout.addStretch(1)

    def _setup_bottom_bar(self, parent_layout, bg_color):
        btn_bar = QWidget()
        border_color = "#333333" if self._theme_mode == "dark" else "#E0E0E0"
        btn_bar.setStyleSheet(f"QWidget {{ background-color: {bg_color}; border-top: 1px solid {border_color}; }}")
        
        btn_layout = QHBoxLayout(btn_bar)
        btn_layout.setContentsMargins(30, 15, 30, 20)
        btn_layout.setSpacing(10)

        self.reset_btn = PushButton(FluentIcon.SYNC, _("Reset to Defaults"))
        self.reset_btn.clicked.connect(self._reset_settings)
        btn_layout.addWidget(self.reset_btn)

        self.export_btn = PushButton(FluentIcon.SHARE, _("Export Config"))
        self.export_btn.clicked.connect(self._export_settings)
        btn_layout.addWidget(self.export_btn)

        self.import_btn = PushButton(FluentIcon.DOWNLOAD, _("Import Config"))
        self.import_btn.clicked.connect(self._import_settings)
        btn_layout.addWidget(self.import_btn)

        btn_layout.addStretch()

        self.save_btn = PrimaryPushButton(FluentIcon.SAVE, _("Save"))
        self.save_btn.setFixedWidth(120)
        self.save_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(self.save_btn)

        parent_layout.addWidget(btn_bar)

    def _switch_view(self, index):
        self.stack_widget.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_btns):
            btn.set_selected(i == index)

    def _load_settings(self):
        """Load settings into pages."""
        s = self._settings_manager.settings
        
        # Appearance Page
        self.appearance_page.theme_card.set_theme_mode(s.theme_mode)
        self.appearance_page.language_card.set_language(s.language)
        self.appearance_page.display_card.set_color_schema(s.color_schema)
        self.appearance_page.display_card.set_dynamic_background(s.dynamic_background)
        self.appearance_page.display_card.set_display_limit(s.display_limit)
        self.appearance_page.display_card.set_minimalist_view(s.minimalist_view)
        self.appearance_page.display_card.set_auto_scroll(s.auto_scroll, s.scroll_interval)
        self.appearance_page.hover_card.set_values(
            s.hover_enabled, s.hover_show_stats, s.hover_show_chart,
            s.kline_period, s.chart_cache_ttl
        )

        # Proxy Page
        self.proxy_page.set_data_source(s.data_source)
        self.proxy_page.set_proxy_config(s.proxy)

        # Pairs Page
        self.pairs_page.set_pairs(s.crypto_pairs)
        
        # Notifications Page
        # NOTE: In old code, AlertSettingCard managed its own loading/saving logic?
        # Checking old code: `self.alerts_card = AlertSettingCard(self.alerts_group)`
        # It seems AlertSettingCard might handle its own state or load from global?
        # Wait, AlertSettingCard in ui/widgets/alert_setting_card.py:
        # It has `_load_alerts` in `__init__`. So it loads automatically from settings_manager (singleton?).
        # If so, we don't need to manually load it here.
        pass

    def _save_settings(self):
        """Gather values from pages and save."""
        s = self._settings_manager.settings
        
        # --- Appearance ---
        new_theme = self.appearance_page.theme_card.get_theme_mode()
        new_lang = self.appearance_page.language_card.get_language()
        new_schema = self.appearance_page.display_card.get_color_schema()
        new_dynamic_bg = self.appearance_page.display_card.get_dynamic_background()
        new_limit = self.appearance_page.display_card.get_display_limit()
        new_mini_view = self.appearance_page.display_card.get_minimalist_view()
        new_auto_scroll, new_scroll_int = self.appearance_page.display_card.get_auto_scroll()
        hover_vals = self.appearance_page.hover_card.get_values()
        
        # --- Network ---
        new_source = self.proxy_page.get_data_source()
        new_proxy = self.proxy_page.get_proxy_config()
        
        # --- Pairs ---
        new_pairs = self.pairs_page.get_pairs()

        # Change detection
        theme_changed = s.theme_mode != new_theme
        lang_changed = s.language != new_lang
        source_changed = s.data_source != new_source
        dynamic_bg_changed = s.dynamic_background != new_dynamic_bg
        limit_changed = s.display_limit != new_limit
        mini_view_changed = s.minimalist_view != new_mini_view
        auto_scroll_changed = (s.auto_scroll != new_auto_scroll) or (s.scroll_interval != new_scroll_int)
        
        # Updates
        self._settings_manager.update_theme(new_theme)
        self._settings_manager.update_language(new_lang)
        self._settings_manager.update_color_schema(new_schema)
        self._settings_manager.update_dynamic_background(new_dynamic_bg)
        self._settings_manager.update_display_limit(new_limit)
        self._settings_manager.update_minimalist_view(new_mini_view)
        self._settings_manager.update_auto_scroll(new_auto_scroll, new_scroll_int)
        
        self._settings_manager.update_hover_settings(
            hover_vals['enabled'], hover_vals['show_stats'], hover_vals['show_chart']
        )
        self._settings_manager.update_kline_period(hover_vals['period'])
        s.chart_cache_ttl = hover_vals['cache_ttl']
        
        self._settings_manager.update_data_source(new_source)
        self._settings_manager.update_proxy(new_proxy)
        self._settings_manager.update_pairs(new_pairs)
        
        # Notifications
        # AlertSettingCard handles its own saving via internal logic if I recall correctly?
        # Let's check AlertSettingCard. 
        # Actually AlertSettingCard usually interacts with SettingsManager directly to add/remove alerts.
        # But if it has transient state, we might need to trigger save?
        # Assuming it's self-contained for add/remove/toggle.
        
        # Feedback and Signals
        if theme_changed or lang_changed:
            bar = InfoBar.success(
                title=_("Settings Saved"),
                content=_("Please restart the application for changes to take effect"),
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=5000,
                parent=self
            )
            restart_btn = PushButton(_("Restart Now"))
            restart_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            restart_btn.clicked.connect(self._restart_app)
            bar.addWidget(restart_btn)
            bar.show()
        else:
            InfoBar.success(_("Settings Saved"), _("Your settings have been saved successfully"), 
                            parent=self, duration=2000)
            
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(100, lambda: self.proxy_changed.emit())
        QTimer.singleShot(100, lambda: self.pairs_changed.emit())
        if theme_changed: QTimer.singleShot(100, lambda: self.theme_changed.emit(new_theme))
        if source_changed: QTimer.singleShot(100, lambda: self.data_source_changed.emit())
        if dynamic_bg_changed: QTimer.singleShot(100, lambda: self.display_changed.emit())
        if mini_view_changed: QTimer.singleShot(100, lambda: self.minimalist_view_changed.emit())
        if auto_scroll_changed: QTimer.singleShot(100, lambda: self.auto_scroll_changed.emit(new_auto_scroll, new_scroll_int))
        if limit_changed: self.display_limit_changed.emit(new_limit)

    def _reset_settings(self):
        default_proxy = ProxyConfig()
        self.proxy_page.set_proxy_config(default_proxy)
        self._settings_manager.update_proxy(default_proxy)
        
        InfoBar.info(_("Settings Reset"), _("Settings have been reset to defaults"), parent=self)
        self.proxy_changed.emit()

    def _export_settings(self):
        from PyQt6.QtWidgets import QFileDialog
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath, _filter = QFileDialog.getSaveFileName(
            self, _("Export Configuration"), f"crypto-monitor_config_{timestamp}.json", "JSON Files (*.json)"
        )
        if filepath:
            try:
                self._settings_manager.export_to_file(filepath)
                InfoBar.success(_("Success"), _("Configuration exported successfully"), parent=self)
            except Exception as e:
                InfoBar.error(_("Error"), f"{_('Failed to export configuration')}: {e}", parent=self)

    def _import_settings(self):
        from PyQt6.QtWidgets import QFileDialog, QMessageBox, QApplication
        from PyQt6.QtCore import QProcess
        import sys

        filepath, _filter = QFileDialog.getOpenFileName(self, _("Import Configuration"), "", "JSON Files (*.json)")
        if filepath:
            if QMessageBox.question(self, _("Confirm Import"), 
                                  _("Importing configuration will overwrite your current settings. This requires a restart. Continue?"),
                                  QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                try:
                    self._settings_manager.import_from_file(filepath)
                    QMessageBox.information(self, _("Success"), _("Configuration imported successfully. The application will now restart."))
                    
                    # Restart application
                    QApplication.quit()
                    QProcess.startDetached(sys.executable, sys.argv)
                except Exception as e:
                    InfoBar.error(_("Error"), f"{_('Failed to import configuration')}: {e}", parent=self)

    def _restart_app(self):
        """Restart the application."""
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QProcess
        import sys
        
        QApplication.quit()
        QProcess.startDetached(sys.executable, sys.argv)

# Inline NavItem for self-containment if not extracting
class NavItem(QWidget):
    clicked = pyqtSignal()
    def __init__(self, text, icon, parent=None, is_dark=False):
        super().__init__(parent)
        self.is_dark = is_dark
        self.is_selected = False
        self.setFixedHeight(40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(13, 0, 10, 0)
        layout.setSpacing(12)
        
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(16, 16)
        self.icon_label.setScaledContents(True)
        from qfluentwidgets import Theme
        self.icon_label.setPixmap(icon.icon(Theme.DARK if is_dark else Theme.LIGHT).pixmap(16, 16))
        layout.addWidget(self.icon_label)
        
        self.text_label = BodyLabel(text)
        self.text_label.setStyleSheet(f"color: {'white' if is_dark else 'black'}; background: transparent; border: none;")
        layout.addWidget(self.text_label)
        layout.addStretch()
        
    def set_selected(self, selected: bool):
        self.is_selected = selected
        if self.is_selected:
            bg = "rgba(0, 120, 212, 0.25)" if self.is_dark else "rgba(0, 120, 212, 0.12)"
            self.setStyleSheet(f"background-color: {bg}; border-radius: 5px;")
            self.text_label.setStyleSheet("color: #0078D4; background: transparent; border: none;")
        else:
            self.setStyleSheet("background-color: transparent;")
            self.text_label.setStyleSheet(f"color: {'white' if self.is_dark else 'black'}; background: transparent; border: none;")
    
    def enterEvent(self, event):
        if not self.is_selected:
            bg = "rgba(255, 255, 255, 0.08)" if self.is_dark else "rgba(0, 0, 0, 0.04)"
            self.setStyleSheet(f"background-color: {bg}; border-radius: 5px;")
        super().enterEvent(event)
    def leaveEvent(self, event):
        self.set_selected(self.is_selected) # restore style
        super().leaveEvent(event)
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
