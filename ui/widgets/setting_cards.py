"""
Custom setting cards for the settings window.
Uses QFluentWidgets components for a modern Fluent Design interface.
"""

from typing import Optional
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import pyqtSignal
from qfluentwidgets import (
    ExpandGroupSettingCard, FluentIcon, SwitchButton,
    PrimaryPushButton, InfoBar, InfoBarPosition,
    BodyLabel, PushButton, ToolButton, ComboBox
)

from .proxy_form import ProxyForm
from .add_pair_dialog import AddPairDialog
from .add_pair_dialog import AddPairDialog
from config.settings import ProxyConfig
from core.i18n import _


class ProxySettingCard(ExpandGroupSettingCard):
    """Expandable setting card for proxy configuration."""

    test_requested = pyqtSignal()  # Emitted when test connection is requested

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(
            FluentIcon.WIFI,
            _("Proxy Configuration"),
            _("Configure network proxy settings for WebSocket connections"),
            parent
        )
        # Description text color adapts to theme automatically via QFluentWidgets

        self._setup_ui()
        # Expand the card by default
        self.toggleExpand()

    def _setup_ui(self):
        """Setup the proxy configuration UI."""
        # Main container
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(48, 18, 48, 18)
        layout.setSpacing(16)

        # Enable proxy switch
        switch_container = QWidget()
        switch_layout = QHBoxLayout(switch_container)
        switch_layout.setContentsMargins(0, 0, 0, 0)

        from qfluentwidgets import BodyLabel
        self.enable_label = BodyLabel(_("Enable Proxy"))
        self.enable_switch = SwitchButton()
        self.enable_switch.setOffText(_("Off"))
        self.enable_switch.setOnText(_("On"))
        self.enable_switch.checkedChanged.connect(self._on_proxy_enabled_changed)

        switch_layout.addWidget(self.enable_label)
        switch_layout.addStretch(1)
        switch_layout.addWidget(self.enable_switch)

        layout.addWidget(switch_container)

        # Proxy form
        self.proxy_form = ProxyForm()
        layout.addWidget(self.proxy_form)

        # Test connection button
        self.test_btn = PrimaryPushButton(FluentIcon.SYNC, _("Test Connection"))
        self.test_btn.setFixedWidth(150)
        self.test_btn.clicked.connect(self._on_test_clicked)
        layout.addWidget(self.test_btn)

        # Add container to card
        self.addGroupWidget(container)

        # Set initial state
        self._on_proxy_enabled_changed(False)

    def _on_proxy_enabled_changed(self, enabled: bool):
        """Handle proxy enabled state change."""
        self.proxy_form.setEnabled(enabled)
        self.test_btn.setEnabled(enabled)

    def _on_test_clicked(self):
        """Handle test connection button click."""
        self.test_requested.emit()

    def get_proxy_config(self) -> ProxyConfig:
        """Get current proxy configuration."""
        values = self.proxy_form.get_values()
        return ProxyConfig(
            enabled=self.enable_switch.isChecked(),
            type=values['type'],
            host=values['host'] or "127.0.0.1",
            port=values['port'],
            username=values['username'],
            password=values['password']
        )

    def set_proxy_config(self, config: ProxyConfig):
        """Set proxy configuration."""
        self.enable_switch.setChecked(config.enabled)
        self.proxy_form.set_values({
            'type': config.type,
            'host': config.host,
            'port': config.port,
            'username': config.username,
            'password': config.password
        })
        self._on_proxy_enabled_changed(config.enabled)

    def show_test_result(self, success: bool, message: str):
        """Show test connection result using InfoBar."""
        if success:
            InfoBar.success(
                title=_("Connection Successful"),
                content=message,
                orient=0,  # Qt.Horizontal
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self.window()
            )
        else:
            InfoBar.error(
                title=_("Connection Failed"),
                content=message,
                orient=0,  # Qt.Horizontal
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=5000,
                parent=self.window()
            )


class PairsSettingCard(ExpandGroupSettingCard):
    """Expandable setting card for crypto pairs management."""

    pairs_changed = pyqtSignal()  # Emitted when pairs list changes

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(
            FluentIcon.MARKET,
            _("Crypto Pairs Management"),
            _("Add, remove, and reorder cryptocurrency trading pairs"),
            parent
        )
        # Description text color adapts to theme automatically via QFluentWidgets

        self._setup_ui()
        # Expand the card by default
        self.toggleExpand()

    def _setup_ui(self):
        """Setup the pairs management UI."""
        # Main container
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(48, 18, 48, 18)
        layout.setSpacing(16)

        # Pairs list - 使用 QFluentWidgets 的 ListWidget
        from qfluentwidgets import ListWidget as FluentListWidget
        self.pairs_list = FluentListWidget()
        self.pairs_list.setSelectionMode(FluentListWidget.SelectionMode.SingleSelection)
        self.pairs_list.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.pairs_list, 1)

        # Control buttons container
        btn_container = QWidget()
        btn_layout = QVBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(8)

        # Add button
        self.add_btn = PrimaryPushButton(FluentIcon.ADD, _("Add"))
        self.add_btn.setFixedWidth(100)
        self.add_btn.clicked.connect(self._add_pair)
        btn_layout.addWidget(self.add_btn)

        # Remove button
        self.remove_btn = PushButton(FluentIcon.DELETE, _("Delete"))
        self.remove_btn.setFixedWidth(100)
        self.remove_btn.setEnabled(False)
        self.remove_btn.clicked.connect(self._remove_pair)
        btn_layout.addWidget(self.remove_btn)

        btn_layout.addSpacing(10)

        # Move up button
        self.move_up_btn = ToolButton(FluentIcon.UP)
        self.move_up_btn.setEnabled(False)
        self.move_up_btn.clicked.connect(self._move_pair_up)
        btn_layout.addWidget(self.move_up_btn)

        # Move down button
        self.move_down_btn = ToolButton(FluentIcon.DOWN)
        self.move_down_btn.setEnabled(False)
        self.move_down_btn.clicked.connect(self._move_pair_down)
        btn_layout.addWidget(self.move_down_btn)

        btn_layout.addStretch()

        layout.addWidget(btn_container, 0)

        # Add container to card
        self.addGroupWidget(container)

    def _on_selection_changed(self):
        """Handle selection change in pairs list."""
        has_selection = self.pairs_list.currentItem() is not None
        self.remove_btn.setEnabled(has_selection)
        self.move_up_btn.setEnabled(has_selection)
        self.move_down_btn.setEnabled(has_selection)

    def _add_pair(self):
        """Add a new crypto pair."""
        pair = AddPairDialog.get_new_pair(self.window())
        if pair:
            self.pairs_list.addItem(pair)
            self.pairs_changed.emit()

    def _remove_pair(self):
        """Remove the selected crypto pair."""
        current_row = self.pairs_list.currentRow()
        if current_row >= 0:
            self.pairs_list.takeItem(current_row)
            self.pairs_changed.emit()

    def _move_pair_up(self):
        """Move selected pair up."""
        current_row = self.pairs_list.currentRow()
        if current_row > 0:
            item = self.pairs_list.takeItem(current_row)
            self.pairs_list.insertItem(current_row - 1, item)
            self.pairs_list.setCurrentRow(current_row - 1)
            self.pairs_changed.emit()

    def _move_pair_down(self):
        """Move selected pair down."""
        current_row = self.pairs_list.currentRow()
        if current_row >= 0 and current_row < self.pairs_list.count() - 1:
            item = self.pairs_list.takeItem(current_row)
            self.pairs_list.insertItem(current_row + 1, item)
            self.pairs_list.setCurrentRow(current_row + 1)
            self.pairs_changed.emit()

    def get_pairs(self) -> list[str]:
        """Get all crypto pairs."""
        pairs = []
        for i in range(self.pairs_list.count()):
            pairs.append(self.pairs_list.item(i).text())
        return pairs

    def set_pairs(self, pairs: list[str]):
        """Set crypto pairs."""
        self.pairs_list.clear()
        for pair in pairs:
            self.pairs_list.addItem(pair)


class ThemeSettingCard(ExpandGroupSettingCard):
    """Expandable setting card for theme configuration."""

    theme_changed = pyqtSignal(str)  # Emitted when theme changes

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(
            FluentIcon.BRUSH,
            _("Theme Settings"),
            _("Choose between light and dark theme"),
            parent
        )
        # Description text color adapts to theme automatically via QFluentWidgets

        self._setup_ui()
        # Expand the card by default
        self.toggleExpand()

    def _setup_ui(self):
        """Setup the theme configuration UI."""
        # Main container
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(48, 18, 48, 18)
        layout.setSpacing(16)

        # Theme selection
        theme_container = QWidget()
        theme_layout = QHBoxLayout(theme_container)
        theme_layout.setContentsMargins(0, 0, 0, 0)

        self.theme_label = BodyLabel(_("Theme Mode"))
        self.theme_combo = ComboBox()
        self.theme_combo.addItems([_("Light Theme"), _("Dark Theme")])
        self.theme_combo.setPlaceholderText("Select theme")
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)

        theme_layout.addWidget(self.theme_label)
        theme_layout.addStretch(1)
        theme_layout.addWidget(self.theme_combo)

        layout.addWidget(theme_container)

        # Info label - color adapts to theme automatically
        info_label = BodyLabel(_("Note: Application restart required for theme changes to take effect"))
        info_label.setStyleSheet("QLabel { font-size: 12px; opacity: 0.6; }")
        layout.addWidget(info_label)

        # Add container to card
        self.addGroupWidget(container)

    def _on_theme_changed(self, text: str):
        """Handle theme selection change."""
        theme_mode = "light" if text == _("Light Theme") else "dark"
        self.theme_changed.emit(theme_mode)

    def get_theme_mode(self) -> str:
        """Get current theme mode."""
        text = self.theme_combo.currentText()
        return "light" if text == _("Light Theme") else "dark"

    def set_theme_mode(self, theme_mode: str):
        """Set theme mode."""
        if theme_mode == "dark":
            self.theme_combo.setCurrentText(_("Dark Theme"))
        else:
            self.theme_combo.setCurrentText(_("Light Theme"))


class LanguageSettingCard(ExpandGroupSettingCard):
    """Expandable setting card for language configuration."""

    language_changed = pyqtSignal(str)  # Emitted when language changes

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(
            FluentIcon.LANGUAGE,
            _("Language"),
            _("Select application language"),
            parent
        )
        self._setup_ui()
        self.toggleExpand()

    def _setup_ui(self):
        """Setup the language configuration UI."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(48, 18, 48, 18)
        layout.setSpacing(16)

        # Language selection
        lang_container = QWidget()
        lang_layout = QHBoxLayout(lang_container)
        lang_layout.setContentsMargins(0, 0, 0, 0)

        from qfluentwidgets import BodyLabel, ComboBox
        self.lang_label = BodyLabel(_("Interface Language"))
        self.lang_combo = ComboBox()
        # Map display names to internal codes
        self.languages = {
            "English (US)": "en_US",
            "Chinese (Simplified)": "zh_CN"
        }
        self.lang_combo.addItems(list(self.languages.keys()))
        self.lang_combo.currentTextChanged.connect(self._on_lang_changed)

        lang_layout.addWidget(self.lang_label)
        lang_layout.addStretch(1)
        lang_layout.addWidget(self.lang_combo)

        layout.addWidget(lang_container)

        # Info label
        info_label = BodyLabel(_("Note: Application restart required for language changes to take effect"))
        info_label.setStyleSheet("QLabel { font-size: 12px; opacity: 0.6; }")
        layout.addWidget(info_label)

        self.addGroupWidget(container)

    def _on_lang_changed(self, text: str):
        """Handle language selection change."""
        code = self.languages.get(text, "en_US")
        self.language_changed.emit(code)

    def get_language(self) -> str:
        """Get current language code."""
        text = self.lang_combo.currentText()
        return self.languages.get(text, "en_US")

    def set_language(self, code: str):
        """Set language."""
        # Find key for value
        for name, lang_code in self.languages.items():
            if lang_code == code:
                self.lang_combo.setCurrentText(name)
                return
        self.lang_combo.setCurrentText("English (US)")
