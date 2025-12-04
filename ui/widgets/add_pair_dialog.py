"""
Dialog for adding a new crypto pair.
"""

import re
from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QLabel, QWidget
)
from PyQt6.QtCore import Qt


class AddPairDialog(QDialog):
    """Dialog for adding a new cryptocurrency trading pair."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._pair: Optional[str] = None
        self._setup_ui()

    def _setup_ui(self):
        """Setup dialog UI."""
        self.setWindowTitle("Add Trading Pair")
        self.setMinimumSize(300, 180)
        self.resize(300, 180)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowCloseButtonHint
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Label
        label = QLabel("Enter trading pair (e.g., BTC-USDT):")
        layout.addWidget(label)

        # Input field
        self.input = QLineEdit()
        self.input.setPlaceholderText("BTC-USDT")
        self.input.textChanged.connect(self._validate_input)
        self.input.returnPressed.connect(self._on_confirm)
        layout.addWidget(self.input)

        # Error label - height will be adjusted dynamically
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #FF6666; font-size: 12px;")
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.confirm_btn = QPushButton("Add")
        self.confirm_btn.setDefault(True)
        self.confirm_btn.clicked.connect(self._on_confirm)
        self.confirm_btn.setEnabled(False)
        btn_layout.addWidget(self.confirm_btn)

        layout.addLayout(btn_layout)

        # Style
        self.setStyleSheet("""
            QDialog {
                background-color: #1E2A38;
            }
            QLabel {
                color: #FFFFFF;
            }
            QLineEdit {
                background-color: #2A3A4A;
                border: 1px solid #3A4A5A;
                border-radius: 4px;
                padding: 8px;
                color: #FFFFFF;
            }
            QLineEdit:focus {
                border-color: #5A8A5A;
            }
            QPushButton {
                background-color: #3A4A5A;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                color: #FFFFFF;
            }
            QPushButton:hover {
                background-color: #4A5A6A;
            }
            QPushButton:disabled {
                background-color: #2A3A4A;
                color: #666666;
            }
        """)

    def _validate_input(self, text: str):
        """Validate the input text and adjust window height dynamically."""
        text = text.strip().upper()

        # Pattern: SYMBOL-SYMBOL (e.g., BTC-USDT)
        pattern = r'^[A-Z0-9]+-[A-Z0-9]+$'

        if not text:
            self.error_label.setVisible(False)
            self._adjust_height()
            self.confirm_btn.setEnabled(False)
        elif re.match(pattern, text):
            self.error_label.setVisible(False)
            self._adjust_height()
            self.confirm_btn.setEnabled(True)
        else:
            self.error_label.setText("Invalid format. Use: SYMBOL-SYMBOL")
            self.error_label.setVisible(True)
            self._adjust_height()
            self.confirm_btn.setEnabled(False)

    def _adjust_height(self):
        """Dynamically adjust window height based on error label visibility."""
        base_height = 180
        error_height = 20

        if self.error_label.isVisible():
            new_height = base_height + error_height
        else:
            new_height = base_height

        self.resize(300, new_height)

    def _on_confirm(self):
        """Handle confirm button click."""
        text = self.input.text().strip().upper()
        if re.match(r'^[A-Z0-9]+-[A-Z0-9]+$', text):
            self._pair = text
            self.accept()

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
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.get_pair()
        return None
