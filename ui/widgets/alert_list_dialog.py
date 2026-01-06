"""
Dialog for managing alerts for a specific trading pair.
"""

from typing import List, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from qfluentwidgets import (
    Dialog, PrimaryPushButton, PushButton, 
    StrongBodyLabel, BodyLabel, SwitchButton,
    FluentIcon, ToolButton, CardWidget
)

from config.settings import PriceAlert, get_settings_manager
from core.alert_manager import get_alert_manager
from ui.widgets.alert_dialog import AlertDialog


class AlertItem(CardWidget):
    """Widget representing a single alert in the list."""
    
    deleted = pyqtSignal(str)   # Emits alert_id
    edited = pyqtSignal(object) # Emits PriceAlert object
    toggled = pyqtSignal(str, bool) # Emits alert_id, new_state

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
            target_text = f"Step: ${self.alert.target_price:,.0f}"
        elif self.alert.alert_type == "price_change_pct":
            target_text = f"Step: {self.alert.target_price:.2f}%"
        else:
            target_text = f"Target: ${self.alert.target_price:,.2f}"
            
        target_label = StrongBodyLabel(target_text)
        info_layout.addWidget(target_label)
        
        # Sub text (Type description)
        desc_text = self._get_desc_for_type(self.alert.alert_type)
        if self.alert.repeat_mode == "repeat":
            desc_text += f" • Repeat ({self.alert.cooldown_seconds}s)"
        else:
            desc_text += " • Once"
            
        desc_label = BodyLabel(desc_text)
        desc_label.setStyleSheet("color: #666666; font-size: 12px;")
        info_layout.addWidget(desc_label)
        
        layout.addLayout(info_layout, 1)

        # Controls
        
        # Edit button
        self.edit_btn = ToolButton(FluentIcon.EDIT)
        self.edit_btn.setToolTip("Edit Alert")
        self.edit_btn.clicked.connect(lambda: self.edited.emit(self.alert))
        layout.addWidget(self.edit_btn)

        # Toggle switch
        self.toggle_switch = SwitchButton()
        self.toggle_switch.setOnText("On")
        self.toggle_switch.setOffText("Off")
        self.toggle_switch.setChecked(self.alert.enabled)
        self.toggle_switch.checkedChanged.connect(self._on_toggled)
        layout.addWidget(self.toggle_switch)

        # Delete button
        self.delete_btn = ToolButton(FluentIcon.DELETE)
        self.delete_btn.setToolTip("Delete Alert")
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
            return FluentIcon.TARGET
        elif alert_type == "price_multiple":
            return FluentIcon.TILES
        elif alert_type == "price_change_pct":
            return FluentIcon.SYNC
        return FluentIcon.ALERT

    def _get_desc_for_type(self, alert_type: str) -> str:
        if alert_type == "price_above":
            return "Crosses Above"
        elif alert_type == "price_below":
            return "Crosses Below"
        elif alert_type == "price_touch":
            return "Touches"
        elif alert_type == "price_multiple":
            return "Price Multiple"
        elif alert_type == "price_change_pct":
            return "Change Step"
        return "Alert"


class AlertListDialog(Dialog):
    """Dialog showing list of alerts for a pair."""

    def __init__(self, pair: str, parent=None):
        super().__init__(title=f"Alerts for {pair}", content="", parent=parent)
        self.pair = pair
        self._settings_manager = get_settings_manager()
        self._alert_manager = get_alert_manager()
        
        # Setup window properties
        self.setFixedWidth(600)
        self.setMinimumHeight(450)
        
        # Z-order fix
        flags = Qt.WindowType.Dialog | Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowCloseButtonHint
        if parent and (parent.windowFlags() & Qt.WindowType.WindowStaysOnTopHint):
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

        self._setup_content()
        self._load_alerts()

    def _setup_content(self):
        # We replace the default content layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Add button bar
        top_bar = QHBoxLayout()
        top_bar.addStretch()
        
        self.add_btn = PrimaryPushButton(FluentIcon.ADD, "Add Alert")
        self.add_btn.clicked.connect(self._on_add_clicked)
        top_bar.addWidget(self.add_btn)
        
        layout.addLayout(top_bar)

        # Scroll area for alerts
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.container = QWidget()
        self.container.setStyleSheet(".QWidget { background: transparent; }")
        self.list_layout = QVBoxLayout(self.container)
        self.list_layout.setSpacing(8)
        self.list_layout.addStretch()
        
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)

        # Replace default text layout content
        self.textLayout.addLayout(layout)
        
        # Hide default buttons (we just need close)
        self.yesButton.hide()
        self.cancelButton.setText("Close")

    def _load_alerts(self):
        """Reload the list of alerts."""
        # Clear existing items (except stretch)
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
                
        alerts = self._settings_manager.get_alerts_for_pair(self.pair)
        
        if not alerts:
            empty_label = BodyLabel("No alerts set for this pair.")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet("color: #999999; margin-top: 20px;")
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
            parent=self, 
            pair=self.pair,
            current_price=current_price
        )
        if new_alert:
            self._settings_manager.add_alert(new_alert)
            self._load_alerts()

    def _on_delete_alert(self, alert_id: str):
        """Handle delete alert."""
        if self._settings_manager.remove_alert(alert_id):
            self._load_alerts()

    def _on_edit_alert(self, alert):
        """Handle edit alert."""
        current_price = self._alert_manager.get_current_price(self.pair)
        updated_alert = AlertDialog.edit_alert(
            alert=alert,
            parent=self,
            current_price=current_price
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
