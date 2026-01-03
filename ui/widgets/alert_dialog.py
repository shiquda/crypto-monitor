"""
Dialog for adding/editing price alerts using Fluent Design.
"""

from typing import Optional, List
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QLabel
from PyQt6.QtCore import Qt
from qfluentwidgets import (
    Dialog, LineEdit, ComboBox, SpinBox, BodyLabel,
    RadioButton, PrimaryPushButton, PushButton
)

from config.settings import PriceAlert, get_settings_manager


class AlertDialog(Dialog):
    """Fluent Design dialog for adding/editing a price alert."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        pair: Optional[str] = None,
        current_price: Optional[float] = None,
        available_pairs: Optional[List[str]] = None,
        edit_alert: Optional[PriceAlert] = None
    ):
        """
        Initialize the alert dialog.

        Args:
            parent: Parent widget
            pair: Pre-selected trading pair
            current_price: Current price for reference
            available_pairs: List of available trading pairs
            edit_alert: Existing alert to edit (None for new alert)
        """
        title = "Edit Price Alert" if edit_alert else "Add Price Alert"
        super().__init__(title=title, content="", parent=parent)

        self._alert: Optional[PriceAlert] = None
        self._edit_alert = edit_alert
        self._pair = pair
        self._current_price = current_price
        self._available_pairs = available_pairs or get_settings_manager().settings.crypto_pairs

        self._setup_content()
        self._load_edit_values()

        # Set dialog size
        self.setFixedSize(420, 400)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowCloseButtonHint
        )

    def _setup_content(self):
        """Setup dialog content."""
        content_layout = QVBoxLayout()
        content_layout.setSpacing(16)

        # Trading pair selection
        pair_layout = QHBoxLayout()
        pair_label = BodyLabel("Trading Pair:")
        pair_label.setFixedWidth(100)
        self.pair_combo = ComboBox()
        self.pair_combo.addItems(self._available_pairs)
        if self._pair and self._pair in self._available_pairs:
            self.pair_combo.setCurrentText(self._pair)
        pair_layout.addWidget(pair_label)
        pair_layout.addWidget(self.pair_combo, 1)
        content_layout.addLayout(pair_layout)

        # Current price reference
        if self._current_price is not None:
            price_ref = BodyLabel(f"Current price: ${self._current_price:,.2f}")
            price_ref.setStyleSheet("color: #666666; font-size: 12px;")
            content_layout.addWidget(price_ref)

        # Alert type selection
        type_label = BodyLabel("Alert Type:")
        content_layout.addWidget(type_label)

        type_container = QWidget()
        type_layout = QVBoxLayout(type_container)
        type_layout.setContentsMargins(20, 0, 0, 0)
        type_layout.setSpacing(8)

        self.type_above = RadioButton("Price rises above target")
        self.type_below = RadioButton("Price falls below target")
        self.type_touch = RadioButton("Price touches target")
        self.type_above.setChecked(True)

        type_layout.addWidget(self.type_above)
        type_layout.addWidget(self.type_below)
        type_layout.addWidget(self.type_touch)
        content_layout.addWidget(type_container)

        # Target price input
        price_layout = QHBoxLayout()
        price_label = BodyLabel("Target Price:")
        price_label.setFixedWidth(100)
        self.price_input = LineEdit()
        self.price_input.setPlaceholderText("0.00")
        if self._current_price is not None:
            self.price_input.setText(f"{self._current_price:.2f}")
        self.price_input.textChanged.connect(self._validate_input)
        price_layout.addWidget(price_label)
        price_layout.addWidget(self.price_input, 1)
        content_layout.addLayout(price_layout)

        # Repeat mode selection
        mode_label = BodyLabel("Reminder Mode:")
        content_layout.addWidget(mode_label)

        mode_container = QWidget()
        mode_layout = QVBoxLayout(mode_container)
        mode_layout.setContentsMargins(20, 0, 0, 0)
        mode_layout.setSpacing(8)

        self.mode_once = RadioButton("Once (disable after triggered)")
        self.mode_repeat = RadioButton("Repeat (with cooldown)")
        self.mode_once.setChecked(True)
        self.mode_repeat.toggled.connect(self._on_repeat_toggled)

        mode_layout.addWidget(self.mode_once)

        # Repeat mode with cooldown spinner
        repeat_layout = QHBoxLayout()
        repeat_layout.setSpacing(8)
        repeat_layout.addWidget(self.mode_repeat)

        self.cooldown_spin = SpinBox()
        self.cooldown_spin.setRange(10, 3600)
        self.cooldown_spin.setValue(60)
        self.cooldown_spin.setSuffix(" sec")
        self.cooldown_spin.setFixedWidth(100)
        self.cooldown_spin.setEnabled(False)
        repeat_layout.addWidget(self.cooldown_spin)
        repeat_layout.addStretch()

        mode_layout.addLayout(repeat_layout)
        content_layout.addWidget(mode_container)

        # Error label
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #D13438; font-size: 12px;")
        self.error_label.setVisible(False)
        content_layout.addWidget(self.error_label)

        # Add content to dialog
        self.textLayout.addLayout(content_layout)

        # Customize buttons
        self.yesButton.setText("Save" if self._edit_alert else "Add")
        self.yesButton.setEnabled(False)
        self.cancelButton.setText("Cancel")
        self.yesButton.clicked.connect(self._on_confirm)

        # Initial validation
        self._validate_input()

    def _load_edit_values(self):
        """Load values from existing alert for editing."""
        if not self._edit_alert:
            return

        # Set pair
        if self._edit_alert.pair in self._available_pairs:
            self.pair_combo.setCurrentText(self._edit_alert.pair)

        # Set alert type
        if self._edit_alert.alert_type == "price_above":
            self.type_above.setChecked(True)
        elif self._edit_alert.alert_type == "price_below":
            self.type_below.setChecked(True)
        else:
            self.type_touch.setChecked(True)

        # Set target price
        self.price_input.setText(f"{self._edit_alert.target_price:.2f}")

        # Set repeat mode
        if self._edit_alert.repeat_mode == "repeat":
            self.mode_repeat.setChecked(True)
            self.cooldown_spin.setValue(self._edit_alert.cooldown_seconds)
        else:
            self.mode_once.setChecked(True)

    def _on_repeat_toggled(self, checked: bool):
        """Handle repeat mode toggle."""
        self.cooldown_spin.setEnabled(checked)

    def _validate_input(self, text: str = None):
        """Validate the price input."""
        try:
            price_text = self.price_input.text().strip()
            if not price_text:
                self.error_label.setVisible(False)
                self.yesButton.setEnabled(False)
                return

            price = float(price_text.replace(',', ''))
            if price <= 0:
                self.error_label.setText("Price must be greater than 0")
                self.error_label.setVisible(True)
                self.yesButton.setEnabled(False)
            else:
                self.error_label.setVisible(False)
                self.yesButton.setEnabled(True)
        except ValueError:
            self.error_label.setText("Invalid price format")
            self.error_label.setVisible(True)
            self.yesButton.setEnabled(False)

    def _on_confirm(self):
        """Handle confirm button click."""
        try:
            price = float(self.price_input.text().strip().replace(',', ''))
            if price <= 0:
                return

            # Determine alert type
            if self.type_above.isChecked():
                alert_type = "price_above"
            elif self.type_below.isChecked():
                alert_type = "price_below"
            else:
                alert_type = "price_touch"

            # Determine repeat mode
            repeat_mode = "repeat" if self.mode_repeat.isChecked() else "once"
            cooldown = self.cooldown_spin.value() if repeat_mode == "repeat" else 60

            # Create or update alert
            if self._edit_alert:
                self._alert = PriceAlert(
                    id=self._edit_alert.id,
                    pair=self.pair_combo.currentText(),
                    alert_type=alert_type,
                    target_price=price,
                    repeat_mode=repeat_mode,
                    enabled=self._edit_alert.enabled,
                    cooldown_seconds=cooldown,
                    last_triggered=self._edit_alert.last_triggered,
                    created_at=self._edit_alert.created_at
                )
            else:
                self._alert = PriceAlert(
                    pair=self.pair_combo.currentText(),
                    alert_type=alert_type,
                    target_price=price,
                    repeat_mode=repeat_mode,
                    cooldown_seconds=cooldown
                )

        except ValueError:
            pass

    def get_alert(self) -> Optional[PriceAlert]:
        """Get the created/edited alert, or None if cancelled."""
        return self._alert

    @staticmethod
    def create_alert(
        parent: Optional[QWidget] = None,
        pair: Optional[str] = None,
        current_price: Optional[float] = None,
        available_pairs: Optional[List[str]] = None
    ) -> Optional[PriceAlert]:
        """
        Static method to show dialog and create a new alert.

        Returns:
            The created PriceAlert, or None if cancelled.
        """
        dialog = AlertDialog(
            parent=parent,
            pair=pair,
            current_price=current_price,
            available_pairs=available_pairs
        )
        if dialog.exec():
            return dialog.get_alert()
        return None

    @staticmethod
    def edit_alert(
        alert: PriceAlert,
        parent: Optional[QWidget] = None,
        current_price: Optional[float] = None,
        available_pairs: Optional[List[str]] = None
    ) -> Optional[PriceAlert]:
        """
        Static method to show dialog and edit an existing alert.

        Returns:
            The updated PriceAlert, or None if cancelled.
        """
        dialog = AlertDialog(
            parent=parent,
            pair=alert.pair,
            current_price=current_price,
            available_pairs=available_pairs,
            edit_alert=alert
        )
        if dialog.exec():
            return dialog.get_alert()
        return None
