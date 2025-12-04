"""
Proxy configuration form widget.
A reusable component for proxy configuration.
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QSpinBox, QComboBox
)


class ProxyForm(QWidget):
    """Reusable proxy configuration form widget."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Setup the proxy form UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Proxy Type
        type_layout = self._create_labeled_widget("Proxy Type", self._create_combo_box(["HTTP", "SOCKS5"]))
        layout.addLayout(type_layout)

        # Host
        host_layout = self._create_labeled_widget("Host", self._create_line_edit("127.0.0.1"))
        layout.addLayout(host_layout)

        # Port
        port_layout = self._create_labeled_widget("Port", self._create_spin_box(1, 65535, 7890))
        layout.addLayout(port_layout)

        # Username (optional)
        username_layout = self._create_labeled_widget("Username", self._create_line_edit("(optional)"))
        layout.addLayout(username_layout)

        # Password (optional)
        password_layout = self._create_labeled_widget("Password", self._create_line_edit("(optional)", is_password=True))
        layout.addLayout(password_layout)

        layout.addStretch()

    def _create_labeled_widget(self, label: str, widget: QWidget) -> QHBoxLayout:
        """
        Create a labeled widget with horizontal layout.

        Args:
            label: The label text
            widget: The widget to add

        Returns:
            Horizontal layout with label and widget
        """
        layout = QHBoxLayout()
        label_widget = QLabel(f"{label}:")
        label_widget.setMinimumWidth(80)

        layout.addWidget(label_widget, 0)
        layout.addWidget(widget, 1)

        return layout

    def _create_combo_box(self, items: list) -> QComboBox:
        """Create a styled combo box."""
        combo = QComboBox()
        combo.addItems(items)
        combo.setMinimumWidth(200)
        return combo

    def _create_line_edit(self, placeholder: str = "", is_password: bool = False) -> QLineEdit:
        """Create a styled line edit."""
        edit = QLineEdit()
        edit.setPlaceholderText(placeholder)
        if is_password:
            edit.setEchoMode(QLineEdit.EchoMode.Password)
        edit.setMinimumWidth(250)
        return edit

    def _create_spin_box(self, min_val: int, max_val: int, default: int) -> QSpinBox:
        """Create a styled spin box."""
        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(default)
        spin.setMinimumWidth(200)
        return spin

    def get_values(self) -> dict:
        """Get all form values."""
        layouts = [self.layout().itemAt(i).layout() for i in range(self.layout().count() - 1)]

        return {
            'type': layouts[0].itemAt(1).widget().currentText().lower(),
            'host': layouts[1].itemAt(1).widget().text(),
            'port': layouts[2].itemAt(1).widget().value(),
            'username': layouts[3].itemAt(1).widget().text(),
            'password': layouts[4].itemAt(1).widget().text()
        }

    def set_values(self, values: dict):
        """Set all form values."""
        layouts = [self.layout().itemAt(i).layout() for i in range(self.layout().count() - 1)]

        # Proxy type
        layouts[0].itemAt(1).widget().setCurrentText(values.get('type', 'http').upper())

        # Host
        layouts[1].itemAt(1).widget().setText(values.get('host', ''))

        # Port
        layouts[2].itemAt(1).widget().setValue(values.get('port', 7890))

        # Username
        layouts[3].itemAt(1).widget().setText(values.get('username', ''))

        # Password
        layouts[4].itemAt(1).widget().setText(values.get('password', ''))
