"""
Proxy configuration form widget.
A reusable component for proxy configuration.
Uses generic field components for better reusability.
"""

from typing import Optional
from PyQt6.QtWidgets import QWidget

from .fields import LabeledComboBox, LabeledLineEdit, LabeledSpinBox


class ProxyForm(QWidget):
    """Reusable proxy configuration form widget."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Setup the proxy form UI using generic field components."""
        from .form_section import FormSection

        # 创建表单区域
        section = FormSection("", show_border=False, spacing=15)
        self.setLayout(section.get_container().layout())

        # 创建字段（增加最小宽度到300px）
        self.proxy_type_field = LabeledComboBox("Proxy Type", ["HTTP", "SOCKS5"], min_width=180)
        self.proxy_host_field = LabeledLineEdit("Host", "127.0.0.1", min_width=300)
        self.proxy_port_field = LabeledSpinBox("Port", 1, 65535, 7890, min_width=180)
        self.proxy_username_field = LabeledLineEdit("Username", "(optional)", min_width=300)
        self.proxy_password_field = LabeledLineEdit("Password", "(optional)", is_password=True, min_width=300)

        # 添加到区域
        section.add_field(self.proxy_type_field)
        section.add_field(self.proxy_host_field)
        section.add_field(self.proxy_port_field)
        section.add_field(self.proxy_username_field)
        section.add_field(self.proxy_password_field)
        section.add_stretch()

    def get_values(self) -> dict:
        """Get all form values."""
        return {
            'type': self.proxy_type_field.current_text().lower(),
            'host': self.proxy_host_field.text(),
            'port': self.proxy_port_field.value(),
            'username': self.proxy_username_field.text(),
            'password': self.proxy_password_field.text()
        }

    def set_values(self, values: dict):
        """Set all form values."""
        self.proxy_type_field.set_current_text(values.get('type', 'http').upper())
        self.proxy_host_field.set_text(values.get('host', ''))
        self.proxy_port_field.set_value(values.get('port', 7890))
        self.proxy_username_field.set_text(values.get('username', ''))
        self.proxy_password_field.set_text(values.get('password', ''))

    def setEnabled(self, enabled: bool):
        """重写setEnabled以同时启用/禁用所有子组件"""
        super().setEnabled(enabled)
        self.proxy_type_field.setEnabled(enabled)
        self.proxy_host_field.setEnabled(enabled)
        self.proxy_port_field.setEnabled(enabled)
        self.proxy_username_field.setEnabled(enabled)
        self.proxy_password_field.setEnabled(enabled)

