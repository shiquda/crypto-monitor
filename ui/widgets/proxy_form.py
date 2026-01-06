"""
Proxy configuration form widget.
A reusable component for proxy configuration.
Uses generic field components for better reusability.
"""

from typing import Optional
from PyQt6.QtWidgets import QWidget

from .fields import LabeledComboBox, LabeledLineEdit, LabeledSpinBox


from core.i18n import _

class ProxyForm(QWidget):
    """Reusable proxy configuration form widget."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Setup the proxy form UI using generic field components."""
        from PyQt6.QtWidgets import QVBoxLayout
        from .fields import LabeledComboBox, LabeledLineEdit, LabeledSpinBox
        from PyQt6.QtCore import Qt

        # 创建布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(16)

        # 创建字段
        self.proxy_type_field = LabeledComboBox(_("Proxy Type"), ["HTTP", "SOCKS5"], min_width=180)
        self.proxy_host_field = LabeledLineEdit(_("Host"), "127.0.0.1", min_width=300)
        self.proxy_port_field = LabeledSpinBox(_("Port"), 1, 65535, 7890, min_width=180)
        self.proxy_username_field = LabeledLineEdit(_("Username"), _("(optional)"), min_width=300)
        self.proxy_password_field = LabeledLineEdit(_("Password"), _("(optional)"), is_password=True, min_width=300)

        # QFluentWidgets 组件已经有默认样式，不需要额外设置

        # 添加到布局
        layout.addWidget(self.proxy_type_field)
        layout.addWidget(self.proxy_host_field)
        layout.addWidget(self.proxy_port_field)
        layout.addWidget(self.proxy_username_field)
        layout.addWidget(self.proxy_password_field)
        # 不添加stretch，让高度紧凑但完整显示

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

