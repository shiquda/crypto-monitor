"""
Crypto card widget for displaying a single cryptocurrency pair.
"""

from typing import Optional
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QColor, QPalette, QMouseEvent
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt6.QtCore import QUrl

from ui.styles.theme import get_stylesheet


class CryptoCard(QWidget):
    """Widget displaying a single crypto pair's information."""

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
        """Setup the widget UI."""
        self.setObjectName("cryptoCard")
        self.setMinimumWidth(100)
        self.setStyleSheet(get_stylesheet("crypto_card"))

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Header row: icon + symbol + percentage
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        # Icon
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(16, 16)
        self.icon_label.setScaledContents(True)
        header_layout.addWidget(self.icon_label)

        # Symbol name
        symbol = self.pair.split("-")[0]
        self.symbol_label = QLabel(symbol)
        self.symbol_label.setObjectName("symbolLabel")
        header_layout.addWidget(self.symbol_label)

        # Percentage
        self.percentage_label = QLabel("0.00%")
        self.percentage_label.setObjectName("percentageLabel")
        header_layout.addWidget(self.percentage_label)

        header_layout.addStretch()

        # Remove button (hidden by default)
        self.remove_btn = QLabel("✕")
        self.remove_btn.setObjectName("removeButton")
        self.remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.remove_btn.setVisible(False)
        self.remove_btn.mousePressEvent = lambda e: self.remove_clicked.emit(self.pair)
        header_layout.addWidget(self.remove_btn)

        layout.addLayout(header_layout)

        # Price row
        self.price_label = QLabel("Loading...")
        self.price_label.setObjectName("priceLabel")
        self.price_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.price_label)

    def _load_icon(self):
        """Load crypto icon from CDN."""
        symbol = self.pair.split("-")[0].lower()
        url = self.ICON_URL_TEMPLATE.format(symbol=symbol)

        self._network_manager = QNetworkAccessManager(self)
        self._network_manager.finished.connect(self._on_icon_loaded)

        request = QNetworkRequest(QUrl(url))
        self._network_manager.get(request)

    def _on_icon_loaded(self, reply: QNetworkReply):
        """Handle icon download completion."""
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = reply.readAll()
            pixmap = QPixmap()
            if pixmap.loadFromData(data):
                self.icon_label.setPixmap(pixmap.scaled(
                    16, 16,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                ))
        reply.deleteLater()

    def update_price(self, price: str, trend: str, color: str):
        """Update the displayed price."""
        display_text = f"{price} {trend}" if trend else price
        self.price_label.setText(display_text)

        # Set color
        if color.startswith("hsl"):
            self.price_label.setStyleSheet(f"color: {color};")
        else:
            self.price_label.setStyleSheet(f"color: {color};")

    def update_percentage(self, percentage: str):
        """Update the percentage display."""
        self.percentage_label.setText(percentage)

        # Set color based on positive/negative
        if percentage.startswith('+'):
            self.percentage_label.setStyleSheet("color: #99FF99;")
        elif percentage.startswith('-'):
            self.percentage_label.setStyleSheet("color: #FF9999;")
        else:
            self.percentage_label.setStyleSheet("color: #FFFFFF;")

    def set_edit_mode(self, enabled: bool):
        """Enable/disable edit mode (shows remove button)."""
        self._edit_mode = enabled
        self.remove_btn.setVisible(enabled)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """Handle double-click to open OKX page."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.pair)
        super().mouseDoubleClickEvent(event)
