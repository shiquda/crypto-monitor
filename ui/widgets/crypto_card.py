"""
Crypto card widget for displaying a single cryptocurrency pair using Fluent Design.
"""

from typing import Optional
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QWidget
from PyQt6.QtCore import Qt, pyqtSignal, QByteArray
from PyQt6.QtGui import QPixmap, QMouseEvent, QImage
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt6.QtCore import QUrl
from PyQt6.QtSvgWidgets import QSvgWidget
from qfluentwidgets import CardWidget, TransparentToolButton, FluentIcon as FIF


class CryptoCard(CardWidget):
    """Fluent Design card widget displaying a single crypto pair's information."""

    double_clicked = pyqtSignal(str)  # Emits pair name on double-click
    remove_clicked = pyqtSignal(str)  # Emits pair name when remove button clicked

    # Icon CDN URL
    ICON_URL_TEMPLATE = "https://cdn.jsdelivr.net/gh/vadimmalykhin/binance-icons/crypto/{symbol}.svg"

    def __init__(self, pair: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.pair = pair
        self._edit_mode = False
        self._setup_ui()
        self._load_icon()

    def _setup_ui(self):
        """Setup the widget UI with Fluent Design components."""
        # CardWidget provides rounded corners and elevation automatically
        self.setBorderRadius(8)
        self.setMinimumWidth(100)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Header row: icon + symbol + percentage + remove button
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        # Icon - using QSvgWidget for SVG support
        self.icon_widget = QSvgWidget()
        self.icon_widget.setFixedSize(16, 16)
        header_layout.addWidget(self.icon_widget)

        # Symbol name
        symbol = self.pair.split("-")[0]
        self.symbol_label = QLabel(symbol)
        self.symbol_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #333333;")
        header_layout.addWidget(self.symbol_label)

        # Percentage
        self.percentage_label = QLabel("0.00%")
        self.percentage_label.setStyleSheet("font-size: 11px; color: #666666;")
        header_layout.addWidget(self.percentage_label)

        header_layout.addStretch()

        # Remove button (hidden by default) - using Fluent Icon
        self.remove_btn = TransparentToolButton(FIF.DELETE, self)
        self.remove_btn.setFixedSize(20, 20)
        self.remove_btn.setVisible(False)
        self.remove_btn.clicked.connect(lambda: self.remove_clicked.emit(self.pair))
        header_layout.addWidget(self.remove_btn)

        layout.addLayout(header_layout)

        # Price row
        self.price_label = QLabel("Loading...")
        self.price_label.setStyleSheet("font-size: 16px; font-weight: 600;")  # 增加字体粗细从 500 到 600
        self.price_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.price_label)

    def _load_icon(self):
        """Load crypto icon from CDN."""
        symbol = self.pair.split("-")[0].lower()
        url = self.ICON_URL_TEMPLATE.format(symbol=symbol)

        self._network_manager = QNetworkAccessManager(self)

        # Configure proxy if needed
        from config.settings import get_settings_manager
        settings = get_settings_manager().settings
        if settings.proxy.enabled:
            from PyQt6.QtNetwork import QNetworkProxy
            proxy = QNetworkProxy()
            if settings.proxy.type.lower() == 'http':
                proxy.setType(QNetworkProxy.ProxyType.HttpProxy)
            else:
                proxy.setType(QNetworkProxy.ProxyType.Socks5Proxy)
            proxy.setHostName(settings.proxy.host)
            proxy.setPort(settings.proxy.port)
            if settings.proxy.username:
                proxy.setUser(settings.proxy.username)
            if settings.proxy.password:
                proxy.setPassword(settings.proxy.password)
            self._network_manager.setProxy(proxy)

        self._network_manager.finished.connect(self._on_icon_loaded)

        request = QNetworkRequest(QUrl(url))
        # Set a user agent to avoid being blocked
        request.setHeader(QNetworkRequest.KnownHeaders.UserAgentHeader, "Mozilla/5.0")

        self._network_manager.get(request)

    def _on_icon_loaded(self, reply: QNetworkReply):
        """Handle icon download completion."""
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = reply.readAll()
            # Load SVG data into the QSvgWidget
            if len(data) > 0:
                if not self.icon_widget.load(data):
                    # If SVG loading fails, hide the icon
                    self.icon_widget.hide()
            else:
                self.icon_widget.hide()
        else:
            # If icon fails to load, hide the icon widget
            self.icon_widget.hide()
        reply.deleteLater()

    def update_price(self, price: str, trend: str, color: str):
        """Update the displayed price."""
        display_text = f"{price} {trend}" if trend else price
        self.price_label.setText(display_text)

        # Set color with font size and weight - 增加字体粗细从 500 到 600
        self.price_label.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {color};")

    def update_percentage(self, percentage: str):
        """Update the percentage display."""
        self.percentage_label.setText(percentage)

        # Set color based on positive/negative
        if percentage.startswith('+'):
            self.percentage_label.setStyleSheet("font-size: 11px; color: #4CAF50;")
        elif percentage.startswith('-'):
            self.percentage_label.setStyleSheet("font-size: 11px; color: #F44336;")
        else:
            self.percentage_label.setStyleSheet("font-size: 11px; color: #666666;")

    def set_edit_mode(self, enabled: bool):
        """Enable/disable edit mode (shows remove button)."""
        self._edit_mode = enabled
        self.remove_btn.setVisible(enabled)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """Handle double-click to open OKX page."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.pair)
        super().mouseDoubleClickEvent(event)
