"""
Dialog for managing alerts for a specific trading pair.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    FluentIcon,
    PrimaryPushButton,
    StrongBodyLabel,
    SwitchButton,
    ToolButton,
)

from config.settings import PriceAlert, get_settings_manager
from core.alert_manager import get_alert_manager
from core.i18n import _
from ui.widgets.alert_dialog import AlertDialog


class AlertItem(CardWidget):
    """Widget representing a single alert in the list."""

    # Define Signals
    deleted = pyqtSignal(str)  # alert_id
    edited = pyqtSignal(object)  # PriceAlert object
    toggled = pyqtSignal(str, bool)  # alert_id, enabled status

    def __init__(self, alert: PriceAlert, parent=None):
        super().__init__(parent)
        self.alert = alert
        self.setFixedHeight(80)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # Icon based on type
        icon_label = QLabel()
        icon = self._get_icon_for_type(self.alert.alert_type)
        icon_label.setPixmap(icon.icon(Qt.GlobalColor.black).pixmap(24, 24))
        layout.addWidget(icon_label)

        # Info text
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        # Main text (Target)
        if self.alert.alert_type == "price_multiple":
            target_text = f"{_('Step')}: ${self.alert.target_price:,.0f}"
        elif self.alert.alert_type == "price_change_pct":
            target_text = f"{_('Step')}: {self.alert.target_price:.2f}%"
        else:
            target_text = f"{_('Target')}: ${self.alert.target_price:,.2f}"

        target_label = StrongBodyLabel(target_text)
        info_layout.addWidget(target_label)

        # Sub text (Type description)
        desc_text = self._get_desc_for_type(self.alert.alert_type)
        if self.alert.repeat_mode == "repeat":
            desc_text += f" • {_('Repeat')} ({self.alert.cooldown_seconds}s)"
        else:
            desc_text += f" • {_('Once')}"

        desc_label = BodyLabel(desc_text)
        theme_mode = get_settings_manager().settings.theme_mode
        desc_color = "#CCCCCC" if theme_mode == "dark" else "#666666"
        desc_label.setStyleSheet(f"color: {desc_color}; font-size: 12px;")
        info_layout.addWidget(desc_label)

        layout.addLayout(info_layout, 1)

        # Controls

        # Edit button
        self.edit_btn = ToolButton(FluentIcon.EDIT)
        self.edit_btn.setToolTip(_("Edit Alert"))
        self.edit_btn.clicked.connect(lambda: self.edited.emit(self.alert))
        layout.addWidget(self.edit_btn)

        # Toggle switch
        self.toggle_switch = SwitchButton()
        self.toggle_switch.setOnText(_("On"))
        self.toggle_switch.setOffText(_("Off"))
        self.toggle_switch.setChecked(self.alert.enabled)
        self.toggle_switch.checkedChanged.connect(self._on_toggled)
        layout.addWidget(self.toggle_switch)

        # Delete button
        self.delete_btn = ToolButton(FluentIcon.DELETE)
        self.delete_btn.setToolTip(_("Delete Alert"))
        self.delete_btn.clicked.connect(lambda: self.deleted.emit(self.alert.id))
        layout.addWidget(self.delete_btn)

    def _on_toggled(self, checked: bool):
        self.toggled.emit(self.alert.id, checked)

    def _get_icon_for_type(self, alert_type: str) -> FluentIcon:
        if alert_type == "price_above":
            return FluentIcon.UP
        elif alert_type == "price_below":
            return FluentIcon.DOWN
        elif alert_type == "price_touch":
            return FluentIcon.MARKET
        elif alert_type == "price_multiple":
            return FluentIcon.TILES
        elif alert_type == "price_change_pct":
            return FluentIcon.SYNC
        return FluentIcon.ALERT

    def _get_desc_for_type(self, alert_type: str) -> str:
        if alert_type == "price_above":
            return _("Crosses Above")
        elif alert_type == "price_below":
            return _("Crosses Below")
        elif alert_type == "price_touch":
            return _("Touches")
        elif alert_type == "price_multiple":
            return _("Price Multiple")
        elif alert_type == "price_change_pct":
            return _("Change Step")
        return _("Alert")


class AlertListDialog(QDialog):
    """Dialog showing list of alerts for a pair."""

    def __init__(self, pair: str, parent=None):
        super().__init__(parent)
        self.pair = pair
        self._settings_manager = get_settings_manager()
        self._alert_manager = get_alert_manager()

        # Setup window properties
        self.setFixedSize(600, 600)

        # Frameless window with styling
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog
        if parent and (parent.windowFlags() & Qt.WindowType.WindowStaysOnTopHint):
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._drag_pos = None

        self._setup_ui()
        self._load_alerts()

    # ... mouse events ...

    def _setup_ui(self):
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Window frame (for background and border)
        self.window_frame = QWidget()
        self.window_frame.setObjectName("windowFrame")

        # Theme handling
        theme_mode = self._settings_manager.settings.theme_mode
        bg_color = "#202020" if theme_mode == "dark" else "#F9F9F9"
        text_color = "white" if theme_mode == "dark" else "black"
        border_color = "#333333" if theme_mode == "dark" else "#E0E0E0"

        self.window_frame.setStyleSheet(f"""
            #windowFrame {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 8px;
            }}
        """)

        layout.addWidget(self.window_frame)

        # Content layout inside frame
        frame_layout = QVBoxLayout(self.window_frame)
        frame_layout.setContentsMargins(24, 24, 24, 24)
        frame_layout.setSpacing(20)

        # Title bar
        title_layout = QHBoxLayout()

        # Title
        from qfluentwidgets import TitleLabel, TransparentToolButton

        from core.utils import get_display_name

        title_label = TitleLabel(f"{_('Alerts for')} {get_display_name(self.pair)}")
        title_label.setStyleSheet(f"color: {text_color};")
        title_layout.addWidget(title_label)

        title_layout.addStretch()

        # Add Alert Button
        self.add_btn = PrimaryPushButton(FluentIcon.ADD, _("Add Alert"))
        self.add_btn.clicked.connect(self._on_add_clicked)
        title_layout.addWidget(self.add_btn)

        # Close Button
        self.close_btn = TransparentToolButton(FluentIcon.CLOSE)
        self.close_btn.setFixedSize(32, 32)
        self.close_btn.clicked.connect(self.accept)
        title_layout.addWidget(self.close_btn)

        frame_layout.addLayout(title_layout)

        # Scroll area for alerts
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.container = QWidget()
        self.container.setStyleSheet(".QWidget { background: transparent; }")
        self.list_layout = QVBoxLayout(self.container)
        self.list_layout.setSpacing(8)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.addStretch()

        self.scroll.setWidget(self.container)
        frame_layout.addWidget(self.scroll)

    def _load_alerts(self):
        """Reload the list of alerts."""
        # Clear existing items (except stretch)
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        alerts = self._settings_manager.get_alerts_for_pair(self.pair)

        if not alerts:
            from qfluentwidgets import BodyLabel

            empty_label = BodyLabel(_("No alerts set for this pair."))
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            theme_mode = self._settings_manager.settings.theme_mode
            empty_color = "#AAAAAA" if theme_mode == "dark" else "#999999"
            empty_label.setStyleSheet(f"color: {empty_color}; margin-top: 20px;")

            self.list_layout.insertWidget(0, empty_label)
        else:
            for alert in alerts:
                item = AlertItem(alert)
                item.deleted.connect(self._on_delete_alert)
                item.edited.connect(self._on_edit_alert)
                item.toggled.connect(self._on_toggle_alert)
                self.list_layout.insertWidget(self.list_layout.count() - 1, item)

    def _on_add_clicked(self):
        """Handle add alert click."""
        current_price = self._alert_manager.get_current_price(self.pair)
        new_alert = AlertDialog.create_alert(
            parent=self, pair=self.pair, current_price=current_price
        )
        if new_alert:
            self._settings_manager.add_alert(new_alert)
            self._load_alerts()

    def _on_delete_alert(self, alert_id: str):
        """Handle delete alert."""
        # Confirm deletion? For now just delete
        if self._settings_manager.remove_alert(alert_id):
            self._load_alerts()

    def _on_edit_alert(self, alert):
        """Handle edit alert."""
        current_price = self._alert_manager.get_current_price(self.pair)
        updated_alert = AlertDialog.edit_alert(
            alert=alert, parent=self, current_price=current_price
        )
        if updated_alert:
            self._settings_manager.update_alert(updated_alert)
            self._load_alerts()

    def _on_toggle_alert(self, alert_id: str, checked: bool):
        """Handle toggle alert."""
        # Find and update alert
        alerts = self._settings_manager.settings.alerts
        for alert in alerts:
            if alert.id == alert_id:
                alert.enabled = checked
                self._settings_manager.update_alert(alert)
                break
