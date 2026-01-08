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
    BodyLabel, PushButton, ToolButton, ComboBox, SpinBox
)

from .proxy_form import ProxyForm
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
        from config.settings import get_settings_manager
        data_source = get_settings_manager().settings.data_source
        pair = AddPairDialog.get_new_pair(data_source, self.window())
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


class DisplaySettingCard(ExpandGroupSettingCard):
    """Expandable setting card for display options (color schema)."""

    color_schema_changed = pyqtSignal(str)  # Emitted when color schema changes
    dynamic_bg_changed = pyqtSignal(bool)   # Emitted when dynamic background setting changes
    period_changed = pyqtSignal(str)        # Emitted when kline period changes
    display_limit_changed = pyqtSignal(int) # Emitted when display limit changes
    auto_scroll_changed = pyqtSignal(bool, int) # Emitted when auto scroll settings change

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(
            FluentIcon.PALETTE,
            _("Display Settings"),
            _("Configure price display colors and effects"),
            parent
        )
        self._setup_ui()
        self.toggleExpand()

    def _setup_ui(self):
        """Setup the display settings UI."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(48, 18, 48, 18)
        layout.setSpacing(16)

        # Color Schema
        schema_container = QWidget()
        schema_layout = QHBoxLayout(schema_container)
        schema_layout.setContentsMargins(0, 0, 0, 0)

        from qfluentwidgets import BodyLabel, ComboBox, SwitchButton
        self.schema_label = BodyLabel(_("Color Schema"))
        self.schema_combo = ComboBox()
        # Note: Index 0 is Standard, Index 1 is Reverse
        self.schema_combo.addItems([_("Green Up / Red Down (Standard)"), _("Red Up / Green Down (Reverse)")])
        self.schema_combo.currentTextChanged.connect(self._on_schema_changed)

        schema_layout.addWidget(self.schema_label)
        schema_layout.addStretch(1)
        schema_layout.addWidget(self.schema_combo)
        
        layout.addWidget(schema_container)
        
        # Dynamic Background
        bg_container = QWidget()
        bg_layout = QHBoxLayout(bg_container)
        bg_layout.setContentsMargins(0, 0, 0, 0)
        
        # Label container for title and description
        label_container = QWidget()
        label_layout = QVBoxLayout(label_container)
        label_layout.setContentsMargins(0, 0, 0, 0)
        label_layout.setSpacing(2)

        from qfluentwidgets import CaptionLabel
        self.bg_label = BodyLabel(_("Dynamic Background"))
        self.bg_desc = CaptionLabel(_("Background opacity varies with price change magnitude"))
        # Set description text color using theme aware colors if possible, typically CaptionLabel is implicitly styled or we leave it default
        # But to be safe lets leave it default, it should be lighter than BodyLabel
        
        label_layout.addWidget(self.bg_label)
        label_layout.addWidget(self.bg_desc)
        
        self.bg_switch = SwitchButton()
        self.bg_switch.setOffText(_("Off"))
        self.bg_switch.setOnText(_("On"))
        self.bg_switch.checkedChanged.connect(self.dynamic_bg_changed.emit)
        
        bg_layout.addWidget(label_container)
        bg_layout.addStretch(1)
        bg_layout.addWidget(self.bg_switch)
        
        layout.addWidget(bg_container)
        
        # Display Limit
        limit_container = QWidget()
        limit_layout = QHBoxLayout(limit_container)
        limit_layout.setContentsMargins(0, 0, 0, 0)
        
        self.limit_label = BodyLabel(_("Pairs per Page"))
        self.limit_spin = SpinBox()
        self.limit_spin.setRange(1, 5)
        self.limit_spin.setFixedWidth(150)
        self.limit_spin.valueChanged.connect(self.display_limit_changed.emit)
        
        limit_layout.addWidget(self.limit_label)
        limit_layout.addStretch(1)
        limit_layout.addWidget(self.limit_spin)
        
        layout.addWidget(limit_container)
        
        # Auto Scroll
        scroll_container = QWidget()
        scroll_layout = QHBoxLayout(scroll_container)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        
        # Configure container for label and description
        from qfluentwidgets import CaptionLabel
        scroll_info_container = QWidget()
        scroll_info_layout = QVBoxLayout(scroll_info_container)
        scroll_info_layout.setContentsMargins(0, 0, 0, 0)
        scroll_info_layout.setSpacing(2)
        
        self.scroll_label = BodyLabel(_("Auto Scroll"))
        self.scroll_desc = CaptionLabel(_("Automatically cycle through pages"))
        scroll_info_layout.addWidget(self.scroll_label)
        scroll_info_layout.addWidget(self.scroll_desc)
        
        scroll_layout.addWidget(scroll_info_container)
        scroll_layout.addStretch(1)
        
        # Interval SpinBox
        self.interval_spin = SpinBox()
        self.interval_spin.setRange(5, 300) # 5s to 300s
        self.interval_spin.setSuffix(" s")
        self.interval_spin.setFixedWidth(150)
        self.interval_spin.valueChanged.connect(self._emit_auto_scroll_changed)
        scroll_layout.addWidget(self.interval_spin)
        
        scroll_layout.addSpacing(10)
        
        # Switch
        self.scroll_switch = SwitchButton()
        self.scroll_switch.setOnText(_("On"))
        self.scroll_switch.setOffText(_("Off"))
        self.scroll_switch.checkedChanged.connect(self._on_scroll_switch_changed)
        scroll_layout.addWidget(self.scroll_switch)
        
        layout.addWidget(scroll_container)
        
        self.addGroupWidget(container)

    def _on_scroll_switch_changed(self, checked: bool):
        self.interval_spin.setEnabled(checked)
        self._emit_auto_scroll_changed()

    def _emit_auto_scroll_changed(self):
        self.auto_scroll_changed.emit(self.scroll_switch.isChecked(), self.interval_spin.value())

    def _on_schema_changed(self, text: str):
        """Handle color schema change."""
        mode = "standard" if self.schema_combo.currentIndex() == 0 else "reverse"
        self.color_schema_changed.emit(mode)

    def set_color_schema(self, schema: str):
        """Set color schema."""
        if schema == "standard":
            self.schema_combo.setCurrentIndex(0)
        else:
            self.schema_combo.setCurrentIndex(1)

    def get_color_schema(self) -> str:
        """Get current color schema."""
        return "standard" if self.schema_combo.currentIndex() == 0 else "reverse"

    def set_dynamic_background(self, enabled: bool):
        """Set dynamic background state."""
        self.bg_switch.setChecked(enabled)

    def get_dynamic_background(self) -> bool:
        """Get current dynamic background state."""
        return self.bg_switch.isChecked()

    def set_display_limit(self, limit: int):
        """Set display limit."""
        if 1 <= limit <= 5:
            self.limit_spin.setValue(limit)

    def get_display_limit(self) -> int:
        """Get current display limit."""
        return self.limit_spin.value()

    def set_auto_scroll(self, enabled: bool, interval: int):
        """Set auto scroll settings."""
        self.scroll_switch.setChecked(enabled)
        self.interval_spin.setValue(interval)
        self.interval_spin.setEnabled(enabled)

    def get_auto_scroll(self) -> tuple[bool, int]:
        """Get current auto scroll settings."""
        return self.scroll_switch.isChecked(), self.interval_spin.value()


class HoverSettingCard(ExpandGroupSettingCard):
    """Expandable setting card for hover card configuration."""

    hover_settings_changed = pyqtSignal(bool, bool, bool) # enabled, stats, chart
    period_changed = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(
            FluentIcon.VIEW, # Used VIEW icon
            _("Hover Card"),
            _("Configure the floating information card"),
            parent
        )
        self._setup_ui()
        self.toggleExpand()

    def _setup_ui(self):
        """Setup the hover settings UI."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(48, 18, 48, 18)
        layout.setSpacing(16)

        from qfluentwidgets import BodyLabel, SwitchButton, ComboBox

        # 1. Master Toggle
        master_container = QWidget()
        master_layout = QHBoxLayout(master_container)
        master_layout.setContentsMargins(0, 0, 0, 0)
        
        self.master_label = BodyLabel(_("Enable Hover Card"))
        self.master_switch = SwitchButton()
        self.master_switch.setOffText(_("Off"))
        self.master_switch.setOnText(_("On"))
        self.master_switch.checkedChanged.connect(self._on_settings_changed)
        
        master_layout.addWidget(self.master_label)
        master_layout.addStretch(1)
        master_layout.addWidget(self.master_switch)
        
        layout.addWidget(master_container)
        
        # Sub-settings container (indented or just list)
        self.sub_settings_widget = QWidget()
        sub_layout = QVBoxLayout(self.sub_settings_widget)
        sub_layout.setContentsMargins(0, 0, 0, 0)
        sub_layout.setSpacing(16)
        
        # 2. Show Statistics
        stats_container = QWidget()
        stats_layout = QHBoxLayout(stats_container)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        
        self.stats_label = BodyLabel(_("Show Statistics"))
        self.stats_switch = SwitchButton()
        self.stats_switch.setOnText(_("On"))
        self.stats_switch.setOffText(_("Off"))
        self.stats_switch.checkedChanged.connect(self._on_settings_changed)
        
        stats_layout.addWidget(self.stats_label)
        stats_layout.addStretch(1)
        stats_layout.addWidget(self.stats_switch)
        
        sub_layout.addWidget(stats_container)
        
        # 3. Show Mini Chart
        chart_container = QWidget()
        chart_layout = QHBoxLayout(chart_container)
        chart_layout.setContentsMargins(0, 0, 0, 0)
        
        self.chart_label = BodyLabel(_("Show Mini Chart"))
        self.chart_switch = SwitchButton()
        self.chart_switch.setOnText(_("On"))
        self.chart_switch.setOffText(_("Off"))
        self.chart_switch.checkedChanged.connect(self._on_chart_switch_changed)
        
        chart_layout.addWidget(self.chart_label)
        chart_layout.addStretch(1)
        chart_layout.addWidget(self.chart_switch)
        
        sub_layout.addWidget(chart_container)
        
        # 4. Mini Chart Range (Moved from DisplaySettingCard)
        self.period_container = QWidget()
        period_layout = QHBoxLayout(self.period_container)
        period_layout.setContentsMargins(0, 0, 0, 0)
        
        self.period_label = BodyLabel(_("Mini Chart Range"))
        self.period_combo = ComboBox()
        self.period_combo.addItems(["1h", "4h", "12h", "24h", "7d"])
        self.period_combo.currentTextChanged.connect(self._on_period_changed)
        
        period_layout.addWidget(self.period_label)
        period_layout.addStretch(1)
        period_layout.addWidget(self.period_combo)
        
        sub_layout.addWidget(self.period_container)
        
        # 5. Advanced Settings - Chart Cache Duration
        from qfluentwidgets import CaptionLabel
        advanced_container = QWidget()
        advanced_layout = QVBoxLayout(advanced_container)
        advanced_layout.setContentsMargins(0, 10, 0, 0)
        advanced_layout.setSpacing(8)
        
        # Advanced section header
        advanced_header = CaptionLabel(_("Advanced Settings"))
        advanced_header.setStyleSheet("QLabel { font-weight: bold; opacity: 0.7; }")
        advanced_layout.addWidget(advanced_header)
        
        # Cache TTL setting
        cache_container = QWidget()
        cache_layout = QHBoxLayout(cache_container)
        cache_layout.setContentsMargins(0, 0, 0, 0)
        
        self.cache_label = BodyLabel(_("Chart Cache Duration"))
        self.cache_spin = SpinBox()
        self.cache_spin.setRange(10, 600)  # 10s to 10min
        self.cache_spin.setSuffix(" " + _("sec"))
        self.cache_spin.setFixedWidth(150)
        
        cache_layout.addWidget(self.cache_label)
        cache_layout.addStretch(1)
        cache_layout.addWidget(self.cache_spin)
        
        advanced_layout.addWidget(cache_container)
        sub_layout.addWidget(advanced_container)
        
        layout.addWidget(self.sub_settings_widget)
        
        self.addGroupWidget(container)

    def _on_settings_changed(self):
        """Handle toggle changes."""
        enabled = self.master_switch.isChecked()
        stats = self.stats_switch.isChecked()
        chart = self.chart_switch.isChecked()
        
        # Enable/Disable sub-settings
        self.sub_settings_widget.setEnabled(enabled)
        
        self.hover_settings_changed.emit(enabled, stats, chart)

    def _on_chart_switch_changed(self, checked: bool):
        """Handle chart switch specifically to enable/disable range combo."""
        self.period_container.setEnabled(checked)
        self._on_settings_changed()

    def _on_period_changed(self, text: str):
        self.period_changed.emit(text)

    def set_values(self, enabled: bool, show_stats: bool, show_chart: bool, period: str, cache_ttl: int = 60):
        """Set all values."""
        self.master_switch.setChecked(enabled)
        self.stats_switch.setChecked(show_stats)
        self.chart_switch.setChecked(show_chart)
        self.period_combo.setCurrentText(period)
        self.cache_spin.setValue(cache_ttl)
        
        self.sub_settings_widget.setEnabled(enabled)
        self.period_container.setEnabled(show_chart)

    def get_values(self):
        """Get all values."""
        return {
            'enabled': self.master_switch.isChecked(),
            'show_stats': self.stats_switch.isChecked(),
            'show_chart': self.chart_switch.isChecked(),
            'period': self.period_combo.currentText(),
            'cache_ttl': self.cache_spin.value()
        }
