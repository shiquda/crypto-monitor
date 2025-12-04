"""
Settings window - independent window for configuration.
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QLineEdit, QSpinBox, QComboBox,
    QCheckBox, QPushButton, QFormLayout
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon

from ui.styles.theme import get_stylesheet
from config.settings import SettingsManager, ProxyConfig


class SettingsWindow(QMainWindow):
    """Independent settings window."""

    proxy_changed = pyqtSignal()  # Emitted when proxy settings change

    def __init__(self, settings_manager: SettingsManager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._settings_manager = settings_manager
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        """Setup the settings window UI."""
        self.setWindowTitle("Settings")
        self.setFixedSize(400, 450)
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowCloseButtonHint
        )
        self.setStyleSheet(get_stylesheet("settings_window"))
        self.setWindowIcon(QIcon("assets/icons/crypto-monitor.png"))

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title
        title = QLabel("Settings")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        # Proxy configuration group
        proxy_group = QGroupBox("Proxy Configuration")
        proxy_layout = QVBoxLayout(proxy_group)

        # Enable proxy checkbox
        self.proxy_enabled = QCheckBox("Enable Proxy")
        self.proxy_enabled.stateChanged.connect(self._on_proxy_enabled_changed)
        proxy_layout.addWidget(self.proxy_enabled)

        # Proxy fields container
        self.proxy_fields = QWidget()
        proxy_fields_layout = QFormLayout(self.proxy_fields)
        proxy_fields_layout.setContentsMargins(0, 10, 0, 0)

        # Proxy type
        self.proxy_type = QComboBox()
        self.proxy_type.addItems(["HTTP", "SOCKS5"])
        proxy_fields_layout.addRow("Proxy Type:", self.proxy_type)

        # Host
        self.proxy_host = QLineEdit()
        self.proxy_host.setPlaceholderText("127.0.0.1")
        proxy_fields_layout.addRow("Host:", self.proxy_host)

        # Port
        self.proxy_port = QSpinBox()
        self.proxy_port.setRange(1, 65535)
        self.proxy_port.setValue(7890)
        proxy_fields_layout.addRow("Port:", self.proxy_port)

        # Username (optional)
        self.proxy_username = QLineEdit()
        self.proxy_username.setPlaceholderText("(optional)")
        proxy_fields_layout.addRow("Username:", self.proxy_username)

        # Password (optional)
        self.proxy_password = QLineEdit()
        self.proxy_password.setPlaceholderText("(optional)")
        self.proxy_password.setEchoMode(QLineEdit.EchoMode.Password)
        proxy_fields_layout.addRow("Password:", self.proxy_password)

        proxy_layout.addWidget(self.proxy_fields)

        # Test connection button
        self.test_btn = QPushButton("Test Connection")
        self.test_btn.setObjectName("testButton")
        self.test_btn.clicked.connect(self._test_connection)
        proxy_layout.addWidget(self.test_btn)

        # Status label
        self.status_label = QLabel()
        self.status_label.setObjectName("statusLabel")
        self.status_label.setVisible(False)
        self.status_label.setWordWrap(True)
        proxy_layout.addWidget(self.status_label)

        layout.addWidget(proxy_group)

        # Spacer
        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()

        self.reset_btn = QPushButton("Reset to Defaults")
        self.reset_btn.setObjectName("resetButton")
        self.reset_btn.clicked.connect(self._reset_settings)
        btn_layout.addWidget(self.reset_btn)

        btn_layout.addStretch()

        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(self.save_btn)

        layout.addLayout(btn_layout)

    def _load_settings(self):
        """Load current settings into UI."""
        proxy = self._settings_manager.settings.proxy

        self.proxy_enabled.setChecked(proxy.enabled)
        self.proxy_type.setCurrentText(proxy.type.upper())
        self.proxy_host.setText(proxy.host)
        self.proxy_port.setValue(proxy.port)
        self.proxy_username.setText(proxy.username)
        self.proxy_password.setText(proxy.password)

        self._on_proxy_enabled_changed(proxy.enabled)

    def _on_proxy_enabled_changed(self, state):
        """Handle proxy enabled checkbox change."""
        enabled = bool(state)
        self.proxy_fields.setEnabled(enabled)
        self.test_btn.setEnabled(enabled)

    def _save_settings(self):
        """Save settings."""
        proxy = ProxyConfig(
            enabled=self.proxy_enabled.isChecked(),
            type=self.proxy_type.currentText().lower(),
            host=self.proxy_host.text() or "127.0.0.1",
            port=self.proxy_port.value(),
            username=self.proxy_username.text(),
            password=self.proxy_password.text()
        )

        self._settings_manager.update_proxy(proxy)

        self._show_status("Settings saved", "success")
        self.proxy_changed.emit()

    def _reset_settings(self):
        """Reset settings to defaults."""
        default_proxy = ProxyConfig()

        self.proxy_enabled.setChecked(default_proxy.enabled)
        self.proxy_type.setCurrentText(default_proxy.type.upper())
        self.proxy_host.setText(default_proxy.host)
        self.proxy_port.setValue(default_proxy.port)
        self.proxy_username.setText(default_proxy.username)
        self.proxy_password.setText(default_proxy.password)

        self._settings_manager.update_proxy(default_proxy)
        self._show_status("Settings reset to defaults", "info")
        self.proxy_changed.emit()

    def _test_connection(self):
        """Test proxy connection."""
        self._show_status("Testing connection...", "info")

        # Build proxy config
        proxy = ProxyConfig(
            enabled=True,
            type=self.proxy_type.currentText().lower(),
            host=self.proxy_host.text() or "127.0.0.1",
            port=self.proxy_port.value(),
            username=self.proxy_username.text(),
            password=self.proxy_password.text()
        )

        # Test connection (simple check)
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((proxy.host, proxy.port))
            sock.close()

            if result == 0:
                self._show_status("Connection successful!", "success")
            else:
                self._show_status(f"Connection failed (error code: {result})", "error")
        except socket.error as e:
            self._show_status(f"Connection failed: {e}", "error")
        except Exception as e:
            self._show_status(f"Error: {e}", "error")

    def _show_status(self, message: str, status_type: str):
        """Show status message."""
        self.status_label.setText(message)
        self.status_label.setVisible(True)

        # Set style based on type
        if status_type == "success":
            self.status_label.setStyleSheet(
                "background-color: #E8F5E9; color: #2E7D32; padding: 10px; border-radius: 4px;"
            )
        elif status_type == "error":
            self.status_label.setStyleSheet(
                "background-color: #FFEBEE; color: #C62828; padding: 10px; border-radius: 4px;"
            )
        else:  # info
            self.status_label.setStyleSheet(
                "background-color: #E3F2FD; color: #1976D2; padding: 10px; border-radius: 4px;"
            )
