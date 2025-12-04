"""
Settings window - independent window for configuration.
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QCheckBox, QPushButton, QListWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon

from ui.styles.theme import get_stylesheet
from ui.widgets.add_pair_dialog import AddPairDialog
from ui.widgets.proxy_form import ProxyForm
from config.settings import SettingsManager, ProxyConfig


class SettingsWindow(QMainWindow):
    """Independent settings window."""

    proxy_changed = pyqtSignal()  # Emitted when proxy settings change
    pairs_changed = pyqtSignal()  # Emitted when crypto pairs change

    def __init__(self, settings_manager: SettingsManager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._settings_manager = settings_manager
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        """Setup the settings window UI."""
        self.setWindowTitle("Settings")
        self.setMinimumSize(650, 600)
        self.resize(650, 600)
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

        # Proxy form
        self.proxy_form = ProxyForm()
        proxy_layout.addWidget(self.proxy_form)

        # Test connection button
        self.test_btn = QPushButton("Test Connection")
        self.test_btn.setObjectName("testButton")
        self.test_btn.clicked.connect(self._test_connection)
        proxy_layout.addWidget(self.test_btn)

        # Status label - height will be adjusted dynamically
        self.status_label = QLabel()
        self.status_label.setObjectName("statusLabel")
        self.status_label.setVisible(False)
        self.status_label.setWordWrap(True)
        proxy_layout.addWidget(self.status_label)

        layout.addWidget(proxy_group)

        # Crypto pairs management group
        pairs_group = QGroupBox("Crypto Pairs Management")
        pairs_layout = QHBoxLayout(pairs_group)

        # Crypto pairs list
        self.pairs_list = QListWidget()
        self.pairs_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.pairs_list.itemSelectionChanged.connect(self._on_pair_selection_changed)
        pairs_layout.addWidget(self.pairs_list, 1)

        # Control buttons container
        btn_container = QWidget()
        btn_container_layout = QVBoxLayout(btn_container)

        # Buttons
        self.add_pair_btn = QPushButton("Add")
        self.add_pair_btn.setObjectName("pairButton")
        self.add_pair_btn.clicked.connect(self._add_pair)
        btn_container_layout.addWidget(self.add_pair_btn)

        self.remove_pair_btn = QPushButton("Delete")
        self.remove_pair_btn.setObjectName("pairButton")
        self.remove_pair_btn.setEnabled(False)
        self.remove_pair_btn.clicked.connect(self._remove_pair)
        btn_container_layout.addWidget(self.remove_pair_btn)

        btn_container_layout.addSpacing(10)

        self.move_up_btn = QPushButton("↑ Up")
        self.move_up_btn.setObjectName("pairButton")
        self.move_up_btn.setEnabled(False)
        self.move_up_btn.clicked.connect(self._move_pair_up)
        btn_container_layout.addWidget(self.move_up_btn)

        self.move_down_btn = QPushButton("↓ Down")
        self.move_down_btn.setObjectName("pairButton")
        self.move_down_btn.setEnabled(False)
        self.move_down_btn.clicked.connect(self._move_pair_down)
        btn_container_layout.addWidget(self.move_down_btn)

        btn_container_layout.addStretch()

        pairs_layout.addWidget(btn_container, 0)

        layout.addWidget(pairs_group)

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

        # Use proxy form to set values
        self.proxy_form.set_values({
            'type': proxy.type,
            'host': proxy.host,
            'port': proxy.port,
            'username': proxy.username,
            'password': proxy.password
        })

        self._on_proxy_enabled_changed(proxy.enabled)

        # Load crypto pairs
        self._load_pairs_list()

    def _on_proxy_enabled_changed(self, state):
        """Handle proxy enabled checkbox change."""
        enabled = bool(state)
        self.proxy_form.setEnabled(enabled)
        self.test_btn.setEnabled(enabled)

    def _save_settings(self):
        """Save settings."""
        proxy_values = self.proxy_form.get_values()

        proxy = ProxyConfig(
            enabled=self.proxy_enabled.isChecked(),
            type=proxy_values['type'],
            host=proxy_values['host'] or "127.0.0.1",
            port=proxy_values['port'],
            username=proxy_values['username'],
            password=proxy_values['password']
        )

        self._settings_manager.update_proxy(proxy)

        # Save crypto pairs
        self._save_pairs_list()

        self._show_status("Settings saved", "success")
        self.proxy_changed.emit()
        self.pairs_changed.emit()

    def _reset_settings(self):
        """Reset settings to defaults."""
        default_proxy = ProxyConfig()

        self.proxy_enabled.setChecked(default_proxy.enabled)

        # Use proxy form to set values
        self.proxy_form.set_values({
            'type': default_proxy.type,
            'host': default_proxy.host,
            'port': default_proxy.port,
            'username': default_proxy.username,
            'password': default_proxy.password
        })

        self._settings_manager.update_proxy(default_proxy)
        self._show_status("Settings reset to defaults", "info")
        self.proxy_changed.emit()

    def _test_connection(self):
        """Test proxy connection."""
        self._show_status("Testing connection...", "info")

        # Build proxy config
        proxy_values = self.proxy_form.get_values()
        proxy = ProxyConfig(
            enabled=True,
            type=proxy_values['type'],
            host=proxy_values['host'] or "127.0.0.1",
            port=proxy_values['port'],
            username=proxy_values['username'],
            password=proxy_values['password']
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
        """Show status message and adjust window height dynamically."""
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

        # Dynamically adjust window height
        self._adjust_height()

    def _adjust_height(self):
        """Dynamically adjust window height based on status label visibility."""
        base_height = 600
        status_height = 50  # Account for padding and multi-line text

        if self.status_label.isVisible():
            new_height = base_height + status_height
        else:
            new_height = base_height

        self.resize(650, new_height)

    def _load_pairs_list(self):
        """Load crypto pairs into the list."""
        self.pairs_list.clear()
        pairs = self._settings_manager.settings.crypto_pairs
        for pair in pairs:
            self.pairs_list.addItem(pair)

    def _save_pairs_list(self):
        """Save crypto pairs from the list."""
        pairs = []
        for i in range(self.pairs_list.count()):
            pairs.append(self.pairs_list.item(i).text())
        self._settings_manager.update_pairs(pairs)

    def _on_pair_selection_changed(self):
        """Handle selection change in pairs list."""
        has_selection = self.pairs_list.currentItem() is not None
        self.remove_pair_btn.setEnabled(has_selection)
        self.move_up_btn.setEnabled(has_selection)
        self.move_down_btn.setEnabled(has_selection)

    def _add_pair(self):
        """Add a new crypto pair."""
        pair = AddPairDialog.get_new_pair(self)
        if pair:
            self.pairs_list.addItem(pair)

    def _remove_pair(self):
        """Remove the selected crypto pair."""
        current_row = self.pairs_list.currentRow()
        if current_row >= 0:
            self.pairs_list.takeItem(current_row)

    def _move_pair_up(self):
        """Move selected pair up."""
        current_row = self.pairs_list.currentRow()
        if current_row > 0:
            item = self.pairs_list.takeItem(current_row)
            self.pairs_list.insertItem(current_row - 1, item)
            self.pairs_list.setCurrentRow(current_row - 1)

    def _move_pair_down(self):
        """Move selected pair down."""
        current_row = self.pairs_list.currentRow()
        if current_row >= 0 and current_row < self.pairs_list.count() - 1:
            item = self.pairs_list.takeItem(current_row)
            self.pairs_list.insertItem(current_row + 1, item)
            self.pairs_list.setCurrentRow(current_row + 1)
