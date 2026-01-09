"""
Dialog for adding/editing price alerts using Fluent Design.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    ComboBox,
    Dialog,
    LineEdit,
    RadioButton,
    SpinBox,
)

from config.settings import PriceAlert, get_settings_manager
from core.i18n import _


class AlertDialog(Dialog):
    """Fluent Design dialog for adding/editing a price alert."""

    def __init__(
        self,
        parent: QWidget | None = None,
        pair: str | None = None,
        current_price: float | None = None,
        available_pairs: list[str] | None = None,
        edit_alert: PriceAlert | None = None,
    ):
        """Initialize the alert dialog."""
        title = _("Edit Price Alert") if edit_alert else _("Add Price Alert")
        super().__init__(title=title, content="", parent=parent)

        self._alert: PriceAlert | None = None
        self._edit_alert = edit_alert
        self._pair = pair
        self._current_price = current_price
        self._available_pairs = available_pairs or get_settings_manager().settings.crypto_pairs

        self._setup_content()
        self._load_edit_values()

        # Set dialog size - Increased height to accommodate new radio buttons
        self.setFixedSize(420, 520)
        # Set window flags
        flags = (
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowCloseButtonHint
        )

        # Inherit AlwaysOnTop from parent if present
        if parent and (parent.windowFlags() & Qt.WindowType.WindowStaysOnTopHint):
            flags |= Qt.WindowType.WindowStaysOnTopHint

        self.setWindowFlags(flags)

        self._drag_pos = None

    # ... mouse events ...

    def _setup_content(self):
        """Setup dialog content."""
        content_layout = QVBoxLayout()
        content_layout.setSpacing(16)

        # Trading pair selection
        pair_layout = QHBoxLayout()
        pair_label = BodyLabel(_("Trading Pair:"))
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
            price_ref = BodyLabel(f"{_('Current price:')} ${self._current_price:,.2f}")
            theme_mode = get_settings_manager().settings.theme_mode
            ref_color = "#CCCCCC" if theme_mode == "dark" else "#666666"
            price_ref.setStyleSheet(f"color: {ref_color}; font-size: 12px;")
            content_layout.addWidget(price_ref)

        # Alert type selection
        type_label = BodyLabel(_("Alert Type:"))
        content_layout.addWidget(type_label)

        type_container = QWidget()
        type_layout = QVBoxLayout(type_container)
        type_layout.setContentsMargins(20, 0, 0, 0)
        type_layout.setSpacing(8)

        self.type_above = RadioButton(_("Price rises above target"))
        self.type_below = RadioButton(_("Price falls below target"))
        self.type_touch = RadioButton(_("Price touches target"))
        self.type_multiple = RadioButton(_("Price hits multiple of (Step)"))
        self.type_change = RadioButton(_("24h Change hits multiple of (Step %)"))

        self.type_above.setChecked(True)
        self.type_above.toggled.connect(self._on_type_changed)
        self.type_below.toggled.connect(self._on_type_changed)
        self.type_touch.toggled.connect(self._on_type_changed)
        self.type_multiple.toggled.connect(self._on_type_changed)
        self.type_change.toggled.connect(self._on_type_changed)

        type_layout.addWidget(self.type_above)
        type_layout.addWidget(self.type_below)
        type_layout.addWidget(self.type_touch)
        type_layout.addWidget(self.type_multiple)
        type_layout.addWidget(self.type_change)
        content_layout.addWidget(type_container)

        # Target price input
        price_layout = QHBoxLayout()
        self.price_label = BodyLabel(_("Target Price:"))
        self.price_label.setFixedWidth(100)
        self.price_input = LineEdit()
        self.price_input.setPlaceholderText("0.00")
        if self._current_price is not None:
            self.price_input.setText(f"{self._current_price:.2f}")
        self.price_input.textChanged.connect(self._validate_input)
        price_layout.addWidget(self.price_label)
        price_layout.addWidget(self.price_input, 1)
        content_layout.addLayout(price_layout)

        # Repeat mode selection
        mode_label = BodyLabel(_("Reminder Mode:"))
        content_layout.addWidget(mode_label)

        mode_container = QWidget()
        mode_layout = QVBoxLayout(mode_container)
        mode_layout.setContentsMargins(20, 0, 0, 0)
        mode_layout.setSpacing(8)

        self.mode_once = RadioButton(_("Once (disable after triggered)"))
        self.mode_repeat = RadioButton(_("Repeat (with cooldown)"))
        self.mode_repeat.setChecked(True)  # Default to Repeat
        self.mode_repeat.toggled.connect(self._on_repeat_toggled)

        mode_layout.addWidget(self.mode_once)

        # Repeat mode with cooldown spinner
        repeat_layout = QHBoxLayout()
        repeat_layout.setSpacing(8)
        repeat_layout.addWidget(self.mode_repeat)

        self.cooldown_spin = SpinBox()
        self.cooldown_spin.setRange(10, 3600)
        self.cooldown_spin.setValue(300)
        self.cooldown_spin.setSuffix(f" {_('sec')}")
        self.cooldown_spin.setFixedWidth(150)
        self.cooldown_spin.setEnabled(True)  # Enabled by default for Repeat
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
        self.yesButton.setText(_("Save") if self._edit_alert else _("Add"))
        self.yesButton.setEnabled(False)
        self.cancelButton.setText(_("Cancel"))
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
        elif self._edit_alert.alert_type == "price_multiple":
            self.type_multiple.setChecked(True)
        elif self._edit_alert.alert_type == "price_change_pct":
            self.type_change.setChecked(True)
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

    def _on_type_changed(self):
        """Handle alert type change to update UI hints."""
        if self.type_multiple.isChecked():
            self.price_label.setText(_("Step Value:"))
            self.price_input.setPlaceholderText(_("e.g. 1000"))
        elif self.type_change.isChecked():
            self.price_label.setText(_("Step %:"))
            self.price_input.setPlaceholderText(_("e.g. 2.0"))
        else:
            self.price_label.setText(_("Target Price:"))
            self.price_input.setPlaceholderText("0.00")

        self._validate_input()

    def _validate_input(self, text: str = None):
        """Validate the price input."""
        try:
            price_text = self.price_input.text().strip()
            if not price_text:
                self.error_label.setVisible(False)
                self.yesButton.setEnabled(False)
                return

            price = float(price_text.replace(",", ""))

            # Additional validation logic could go here
            if price <= 0:
                self.error_label.setText(_("Value must be greater than 0"))
                self.error_label.setVisible(True)
                self.yesButton.setEnabled(False)
            else:
                self.error_label.setVisible(False)
                self.yesButton.setEnabled(True)
        except ValueError:
            self.error_label.setText(_("Invalid format"))
            self.error_label.setVisible(True)
            self.yesButton.setEnabled(False)

    def _on_confirm(self):
        """Handle confirm button click."""
        try:
            price = float(self.price_input.text().strip().replace(",", ""))
            if price <= 0:
                return

            # Determine alert type
            if self.type_above.isChecked():
                alert_type = "price_above"
            elif self.type_below.isChecked():
                alert_type = "price_below"
            elif self.type_multiple.isChecked():
                alert_type = "price_multiple"
            elif self.type_change.isChecked():
                alert_type = "price_change_pct"
            else:
                alert_type = "price_touch"

            # Determine repeat mode
            repeat_mode = "repeat" if self.mode_repeat.isChecked() else "once"
            cooldown = self.cooldown_spin.value() if repeat_mode == "repeat" else 300

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
                    created_at=self._edit_alert.created_at,
                )
            else:
                self._alert = PriceAlert(
                    pair=self.pair_combo.currentText(),
                    alert_type=alert_type,
                    target_price=price,
                    repeat_mode=repeat_mode,
                    cooldown_seconds=cooldown,
                )

        except ValueError:
            pass

    def get_alert(self) -> PriceAlert | None:
        """Get the created/edited alert, or None if cancelled."""
        return self._alert

    @staticmethod
    def create_alert(
        parent: QWidget | None = None,
        pair: str | None = None,
        current_price: float | None = None,
        available_pairs: list[str] | None = None,
    ) -> PriceAlert | None:
        """
        Static method to show dialog and create a new alert.

        Returns:
            The created PriceAlert, or None if cancelled.
        """
        dialog = AlertDialog(
            parent=parent,
            pair=pair,
            current_price=current_price,
            available_pairs=available_pairs,
        )
        if dialog.exec():
            return dialog.get_alert()
        return None

    @staticmethod
    def edit_alert(
        alert: PriceAlert,
        parent: QWidget | None = None,
        current_price: float | None = None,
        available_pairs: list[str] | None = None,
    ) -> PriceAlert | None:
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
            edit_alert=alert,
        )
        if dialog.exec():
            return dialog.get_alert()
        return None
