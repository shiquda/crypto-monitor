"""
Alert setting card for the settings window.
Uses QFluentWidgets components for a modern Fluent Design interface.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    ComboBox,
    ExpandGroupSettingCard,
    FluentIcon,
    PrimaryPushButton,
    PushButton,
    SwitchButton,
    ToolButton,
)
from qfluentwidgets import ListWidget as FluentListWidget

from config.settings import PriceAlert, get_settings_manager
from core.i18n import _

from .alert_dialog import AlertDialog


class AlertListItem(QWidget):
    """Custom widget for displaying an alert in the list."""

    delete_clicked = pyqtSignal(str)  # Emits alert ID
    toggle_clicked = pyqtSignal(str)  # Emits alert ID

    def __init__(self, alert: PriceAlert, parent: QWidget | None = None):
        super().__init__(parent)
        self.alert = alert
        self._setup_ui()

    def _setup_ui(self):
        """Setup the item UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(12)

        # Enable/disable switch
        self.switch = SwitchButton()
        self.switch.setChecked(self.alert.enabled)
        self.switch.setOnText("")
        self.switch.setOffText("")
        self.switch.checkedChanged.connect(lambda: self.toggle_clicked.emit(self.alert.id))
        layout.addWidget(self.switch)

        # Alert info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        # Pair and type
        type_text = self._get_type_text()
        title = BodyLabel(f"{self.alert.pair}")

        # Theme-aware title color
        from config.settings import get_settings_manager

        theme_mode = get_settings_manager().settings.theme_mode
        title_color = "#FFFFFF" if theme_mode == "dark" else "#333333"
        title.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {title_color};")
        info_layout.addWidget(title)

        # Details
        mode_text = (
            _("Once")
            if self.alert.repeat_mode == "once"
            else f"{_('Repeat')} ({self.alert.cooldown_seconds}s)"
        )
        details = BodyLabel(f"{type_text} ${self.alert.target_price:,.2f} | {mode_text}")

        # Theme-aware color for details - use darker color for better visibility in light mode
        from config.settings import get_settings_manager

        theme_mode = get_settings_manager().settings.theme_mode
        details_color = "#AAAAAA" if theme_mode == "dark" else "#555555"
        details.setStyleSheet(f"font-size: 11px; color: {details_color};")
        info_layout.addWidget(details)

        layout.addLayout(info_layout, 1)

        # Delete button
        self.delete_btn = ToolButton(FluentIcon.DELETE)
        self.delete_btn.setFixedSize(28, 28)
        self.delete_btn.clicked.connect(lambda: self.delete_clicked.emit(self.alert.id))
        layout.addWidget(self.delete_btn)

    def _get_type_text(self) -> str:
        """Get human-readable alert type text."""
        if self.alert.alert_type == "price_above":
            return _("Above")
        elif self.alert.alert_type == "price_below":
            return _("Below")
        elif self.alert.alert_type == "price_multiple":
            return _("Step")
        elif self.alert.alert_type == "price_change_pct":
            return _("Change %")
        else:
            return _("Touch")


class AlertSettingCard(ExpandGroupSettingCard):
    """Expandable setting card for price alert management."""

    alerts_changed = pyqtSignal()  # Emitted when alerts list changes

    def __init__(self, parent: QWidget | None = None):
        super().__init__(
            FluentIcon.RINGER,
            _("Price Alerts"),
            _("Manage price alerts for trading pairs"),
            parent,
        )
        self._settings_manager = get_settings_manager()
        self._alert_widgets: dict = {}  # alert_id -> AlertListItem

        self._setup_ui()
        self._load_alerts()
        self.toggleExpand()

    def _setup_ui(self):
        """Setup the alerts management UI."""
        # Main container
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(48, 18, 48, 18)
        layout.setSpacing(16)

        # Alerts list - increased height for better visibility
        self.alerts_list = FluentListWidget()
        self.alerts_list.setMinimumHeight(200)
        self.alerts_list.setMaximumHeight(350)
        layout.addWidget(self.alerts_list)

        # Sound settings
        sound_container = QWidget()
        sound_layout = QHBoxLayout(sound_container)
        sound_layout.setContentsMargins(0, 0, 0, 0)

        self.sound_label = BodyLabel(_("Alert Sound"))
        self.sound_combo = ComboBox()
        self.sound_combo.addItems([_("Off"), _("System Sound"), _("Chime")])
        self.sound_combo.setMinimumWidth(150)

        # Set initial index based on settings
        mode = self._settings_manager.settings.sound_mode
        if mode == "system":
            self.sound_combo.setCurrentIndex(1)
        elif mode == "chime":
            self.sound_combo.setCurrentIndex(2)
        else:
            self.sound_combo.setCurrentIndex(0)

        self.sound_combo.currentTextChanged.connect(self._on_sound_mode_changed)

        sound_layout.addWidget(self.sound_label)
        sound_layout.addStretch(1)
        sound_layout.addWidget(self.sound_combo)

        layout.addWidget(sound_container)

        # Button bar
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.add_btn = PrimaryPushButton(FluentIcon.ADD, _("Add Alert"))
        self.add_btn.setFixedWidth(120)
        self.add_btn.clicked.connect(self._add_alert)
        btn_layout.addWidget(self.add_btn)

        self.test_btn = PushButton(FluentIcon.SEND, _("Test"))
        self.test_btn.setFixedWidth(140)
        self.test_btn.clicked.connect(self._on_test_notification)
        btn_layout.addWidget(self.test_btn)

        btn_layout.addStretch()

        self.clear_btn = PushButton(FluentIcon.DELETE, _("Clear All"))
        self.clear_btn.setFixedWidth(100)
        self.clear_btn.clicked.connect(self._clear_all_alerts)
        btn_layout.addWidget(self.clear_btn)

        layout.addLayout(btn_layout)

        # Add container to card
        self.addGroupWidget(container)

    def _load_alerts(self):
        """Load alerts from settings."""
        self.alerts_list.clear()
        self._alert_widgets.clear()

        alerts = self._settings_manager.settings.alerts

        for alert in alerts:
            self._add_alert_item(alert)

        self._update_clear_button()

    def _add_alert_item(self, alert: PriceAlert):
        """Add an alert item to the list."""
        from PyQt6.QtWidgets import QListWidgetItem

        item = QListWidgetItem()
        item.setData(256, alert.id)  # Store alert ID in item data

        widget = AlertListItem(alert)
        widget.delete_clicked.connect(self._on_delete_alert)
        widget.toggle_clicked.connect(self._on_toggle_alert)
        self._alert_widgets[alert.id] = widget

        item.setSizeHint(widget.sizeHint())
        self.alerts_list.addItem(item)
        self.alerts_list.setItemWidget(item, widget)

    def _add_alert(self):
        """Add a new alert."""
        alert = AlertDialog.create_alert(
            parent=self.window(),
            available_pairs=self._settings_manager.settings.crypto_pairs,
        )

        if alert:
            self._settings_manager.add_alert(alert)
            self._add_alert_item(alert)
            self._update_clear_button()
            self.alerts_changed.emit()

    def _on_delete_alert(self, alert_id: str):
        """Handle alert deletion."""
        # Find and remove the list item
        for i in range(self.alerts_list.count()):
            item = self.alerts_list.item(i)
            if item.data(256) == alert_id:
                self.alerts_list.takeItem(i)
                break

        # Remove from widgets dict
        if alert_id in self._alert_widgets:
            del self._alert_widgets[alert_id]

        # Remove from settings
        self._settings_manager.remove_alert(alert_id)
        self._update_clear_button()
        self.alerts_changed.emit()

    def _on_toggle_alert(self, alert_id: str):
        """Handle alert enable/disable toggle."""
        for alert in self._settings_manager.settings.alerts:
            if alert.id == alert_id:
                alert.enabled = not alert.enabled
                self._settings_manager.update_alert(alert)
                self.alerts_changed.emit()
                break

    def _on_sound_mode_changed(self, text: str):
        """Handle sound mode change."""
        if text == _("System Sound"):
            mode = "system"
        elif text == _("Chime"):
            mode = "chime"
        else:
            mode = "off"
        self._settings_manager.update_sound_mode(mode)

    def _clear_all_alerts(self):
        """Clear all alerts."""
        # Clear list
        self.alerts_list.clear()
        self._alert_widgets.clear()

        # Clear from settings
        self._settings_manager.settings.alerts.clear()
        self._settings_manager.save()

        self._update_clear_button()
        self.alerts_changed.emit()

    def _update_clear_button(self):
        """Update clear button enabled state."""
        has_alerts = len(self._settings_manager.settings.alerts) > 0
        self.clear_btn.setEnabled(has_alerts)

    def _on_test_notification(self):
        """Send a test notification."""
        from core.notifier import get_notification_service

        get_notification_service().send_test_notification()

    def refresh(self):
        """Refresh the alerts list."""
        self._load_alerts()
