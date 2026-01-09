from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QVBoxLayout, QWidget
from qfluentwidgets import ScrollArea, SettingCardGroup

from core.i18n import _
from ui.widgets.data_source_setting_card import DataSourceSettingCard
from ui.widgets.setting_cards import ProxySettingCard


class ProxyPage(QWidget):
    """Network settings page."""

    proxy_changed = pyqtSignal()
    data_source_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Scroll Area
        self.scroll = ScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(30, 30, 30, 30)
        self.scroll_layout.setSpacing(20)

        # Network Group
        self.proxy_group = SettingCardGroup(_("Network Configuration"), self.scroll_content)

        # Data Source
        self.data_source_card = DataSourceSettingCard(self.proxy_group)
        self.proxy_group.addSettingCard(self.data_source_card)

        # Proxy
        self.proxy_card = ProxySettingCard(self.proxy_group)
        self.proxy_card.test_requested.connect(self._test_connection)
        self.proxy_group.addSettingCard(self.proxy_card)

        self.scroll_layout.addWidget(self.proxy_group)
        self.scroll_layout.addStretch(1)

        self.scroll.setWidget(self.scroll_content)
        self.layout.addWidget(self.scroll)

    def _test_connection(self):
        """Test proxy connection."""
        # Get current proxy config
        proxy = self.proxy_card.get_proxy_config()

        import socket

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            # Create a localized temporary connection logic or rely on helper
            # To keep it simple and self-contained, using basic socket logic as in original
            result = sock.connect_ex((proxy.host, proxy.port))
            sock.close()

            if result == 0:
                self.proxy_card.show_test_result(True, _("Proxy server is reachable"))
            else:
                self.proxy_card.show_test_result(
                    False, f"{_('Connection failed')} ({_('error code')}: {result})"
                )
        except OSError as e:
            self.proxy_card.show_test_result(False, f"{_('Socket error')}: {str(e)}")
        except Exception as e:
            self.proxy_card.show_test_result(False, f"{_('Unexpected error')}: {str(e)}")

    def set_data_source(self, source):
        self.data_source_card.set_data_source(source)

    def get_data_source(self):
        return self.data_source_card.get_data_source()

    def set_proxy_config(self, config):
        self.proxy_card.set_proxy_config(config)

    def get_proxy_config(self):
        return self.proxy_card.get_proxy_config()
