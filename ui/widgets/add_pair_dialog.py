"""
Dialog for adding a new crypto pair using Fluent Design.
"""

import re
from typing import Optional
from PyQt6.QtWidgets import QVBoxLayout, QWidget, QLabel
from PyQt6.QtCore import Qt
from qfluentwidgets import Dialog, LineEdit


class AddPairDialog(Dialog):
    """Fluent Design dialog for adding a new cryptocurrency trading pair."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(
            title="Add Trading Pair",
            content="",
            parent=parent
        )
        self._pair: Optional[str] = None
        self._setup_content()

        # Set dialog size
        self.setFixedSize(400, 200)

        # Make sure it's a top-level window
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowCloseButtonHint)

    def _setup_content(self):
        """Setup dialog content with input field."""
        # Create container layout for the content
        content_layout = QVBoxLayout()
        content_layout.setSpacing(12)

        # Label
        label = QLabel("Enter trading pair (e.g., BTC-USDT):")
        label.setStyleSheet("font-size: 14px;")
        content_layout.addWidget(label)

        # Input field - using Fluent LineEdit
        self.input = LineEdit()
        self.input.setPlaceholderText("BTC-USDT")
        self.input.setFixedHeight(36)
        self.input.textChanged.connect(self._validate_input)
        self.input.returnPressed.connect(self._on_confirm)
        content_layout.addWidget(self.input)

        # Error label
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #D13438; font-size: 12px;")
        self.error_label.setVisible(False)
        content_layout.addWidget(self.error_label)

        # Add the content layout to the dialog's text layout
        self.textLayout.addLayout(content_layout)

        # Customize the built-in buttons
        self.yesButton.setText("Add")
        self.yesButton.setEnabled(False)
        self.cancelButton.setText("Cancel")

        # Connect the built-in yes button
        self.yesButton.clicked.connect(self._on_confirm)

    def _validate_input(self, text: str):
        """Validate the input text."""
        text = text.strip().upper()

        # Pattern: SYMBOL-SYMBOL (e.g., BTC-USDT)
        pattern = r'^[A-Z0-9]+-[A-Z0-9]+$'

        if not text:
            self.error_label.setVisible(False)
            self.yesButton.setEnabled(False)
        elif re.match(pattern, text):
            self.error_label.setVisible(False)
            self.yesButton.setEnabled(True)
        else:
            self.error_label.setText("Invalid format. Use: SYMBOL-SYMBOL")
            self.error_label.setVisible(True)
            self.yesButton.setEnabled(False)

    def _on_confirm(self):
        """Handle confirm button click."""
        text = self.input.text().strip().upper()
        if re.match(r'^[A-Z0-9]+-[A-Z0-9]+$', text):
            self._pair = text

    def get_pair(self) -> Optional[str]:
        """Get the entered pair, or None if cancelled."""
        return self._pair

    @staticmethod
    def get_new_pair(parent: Optional[QWidget] = None) -> Optional[str]:
        """
        Static method to show dialog and get a new pair.

        Returns:
            The entered pair string, or None if cancelled.
        """
        dialog = AddPairDialog(parent)
        if dialog.exec():
            return dialog.get_pair()
        return None
