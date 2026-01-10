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
    isDarkTheme,
)
from qfluentwidgets import ListWidget as FluentListWidget

from config.settings import PriceAlert, get_settings_manager
from core.i18n import _

from .alert_dialog import AlertDialog


class AlertListItem(QWidget):
    delete_clicked = pyqtSignal(str)
    toggle_clicked = pyqtSignal(str)

    def __init__(self, alert: PriceAlert, parent: QWidget | None = None):
        super().__init__(parent)
        self.alert = alert
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(12)

        self.switch = SwitchButton()
        self.switch.setChecked(self.alert.enabled)
        self.switch.setOnText("")
        self.switch.setOffText("")
        self.switch.checkedChanged.connect(lambda: self.toggle_clicked.emit(self.alert.id))
        layout.addWidget(self.switch)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        from core.utils import get_display_name

        type_text = self._get_type_text()
        self.title = BodyLabel(get_display_name(self.alert.pair))

        is_dark = isDarkTheme()
        title_color = "#FFFFFF" if is_dark else "#333333"
        self.title.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {title_color};")
        info_layout.addWidget(self.title)

        mode_text = (
            _("Once")
            if self.alert.repeat_mode == "once"
            else f"{_('Repeat')} ({self.alert.cooldown_seconds}s)"
        )
        self.details = BodyLabel(f"{type_text} ${self.alert.target_price:,.2f} | {mode_text}")

        details_color = "#AAAAAA" if is_dark else "#555555"
        self.details.setStyleSheet(f"font-size: 11px; color: {details_color};")
        info_layout.addWidget(self.details)

        layout.addLayout(info_layout, 1)

        self.delete_btn = ToolButton(FluentIcon.DELETE)
        self.delete_btn.setFixedSize(28, 28)
        self.delete_btn.clicked.connect(lambda: self.delete_clicked.emit(self.alert.id))
        layout.addWidget(self.delete_btn)

    def _get_type_text(self) -> str:
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
    alerts_changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(
            FluentIcon.RINGER,
            _("Price Alerts"),
            _("Manage price alerts for trading pairs"),
            parent,
        )
        self._settings_manager = get_settings_manager()
        self._alert_widgets: dict = {}

        self._setup_ui()
        self._load_alerts()
        self.toggleExpand()

    def _setup_ui(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(48, 18, 48, 18)
        layout.setSpacing(16)

        self.alerts_list = FluentListWidget()
        self.alerts_list.setMinimumHeight(200)
        self.alerts_list.setMaximumHeight(350)
        layout.addWidget(self.alerts_list)

        sound_container = QWidget()
        sound_layout = QHBoxLayout(sound_container)
        sound_layout.setContentsMargins(0, 0, 0, 0)

        self.sound_label = BodyLabel(_("Alert Sound"))
        self.sound_combo = ComboBox()
        self.sound_combo.addItems([_("Off"), _("System Sound"), _("Chime")])
        self.sound_combo.setMinimumWidth(150)

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

        self.addGroupWidget(container)

    def _load_alerts(self):
        self.alerts_list.clear()
        self._alert_widgets.clear()

        alerts = self._settings_manager.settings.alerts

        for alert in alerts:
            self._add_alert_item(alert)

        self._update_clear_button()

    def _add_alert_item(self, alert: PriceAlert):
        from PyQt6.QtWidgets import QListWidgetItem

        item = QListWidgetItem()
        item.setData(256, alert.id)

        widget = AlertListItem(alert)
        widget.delete_clicked.connect(self._on_delete_alert)
        widget.toggle_clicked.connect(self._on_toggle_alert)
        self._alert_widgets[alert.id] = widget

        item.setSizeHint(widget.sizeHint())
        self.alerts_list.addItem(item)
        self.alerts_list.setItemWidget(item, widget)

    def _add_alert(self):
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
        for i in range(self.alerts_list.count()):
            item = self.alerts_list.item(i)
            if item.data(256) == alert_id:
                self.alerts_list.takeItem(i)
                break

        if alert_id in self._alert_widgets:
            del self._alert_widgets[alert_id]

        self._settings_manager.remove_alert(alert_id)
        self._update_clear_button()
        self.alerts_changed.emit()

    def _on_toggle_alert(self, alert_id: str):
        for alert in self._settings_manager.settings.alerts:
            if alert.id == alert_id:
                alert.enabled = not alert.enabled
                self._settings_manager.update_alert(alert)
                self.alerts_changed.emit()
                break

    def _on_sound_mode_changed(self, text: str):
        if text == _("System Sound"):
            mode = "system"
        elif text == _("Chime"):
            mode = "chime"
        else:
            mode = "off"
        self._settings_manager.update_sound_mode(mode)

    def _clear_all_alerts(self):
        self.alerts_list.clear()
        self._alert_widgets.clear()

        self._settings_manager.settings.alerts.clear()
        self._settings_manager.save()

        self._update_clear_button()
        self.alerts_changed.emit()

    def _update_clear_button(self):
        has_alerts = len(self._settings_manager.settings.alerts) > 0
        self.clear_btn.setEnabled(has_alerts)

    def _on_test_notification(self):
        from core.notifier import get_notification_service

        get_notification_service().send_test_notification()

    def refresh(self):
        self._load_alerts()
