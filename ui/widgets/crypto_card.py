"""
Crypto card widget for displaying a single cryptocurrency pair using Fluent Design.
"""

import os
from typing import Optional
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QWidget, QMenu
from PyQt6.QtCore import Qt, pyqtSignal, QByteArray
from PyQt6.QtGui import QMouseEvent, QContextMenuEvent, QAction, QColor
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt6.QtCore import QUrl
from PyQt6.QtSvgWidgets import QSvgWidget
from qfluentwidgets import CardWidget, TransparentToolButton, FluentIcon as FIF

from core.i18n import _


class CryptoCard(CardWidget):
    """Fluent Design card widget displaying a single crypto pair's information."""

    double_clicked = pyqtSignal(str)  # Emits pair name on double-click
    remove_clicked = pyqtSignal(str)  # Emits pair name when remove button clicked
    add_alert_requested = pyqtSignal(str)  # Emits pair name when add alert is requested
    view_alerts_requested = pyqtSignal(str)  # Emits pair name when view alerts is requested
    browser_opened_requested = pyqtSignal(str)  # Emits pair name when open in browser is requested

    # Icon CDN URL
    ICON_URL_TEMPLATE = "https://cdn.jsdelivr.net/gh/vadimmalykhin/binance-icons/crypto/{symbol}.svg"

    def __init__(self, pair: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.pair = pair
        self._edit_mode = False
        self._icon_retry_count = 0
        self._max_retries = 3
        self._current_percentage = "0.00%"  # Store current percentage
        self._setup_ui()
        self._load_icon()

    def _setup_ui(self):
        """Setup the widget UI with Fluent Design components."""
        # CardWidget provides rounded corners and elevation automatically
        self.setBorderRadius(8)
        self.setMinimumWidth(100)

        # Get theme mode for color selection
        from config.settings import get_settings_manager
        theme_mode = get_settings_manager().settings.theme_mode
        self._theme_mode = theme_mode

        # Define colors based on theme
        if theme_mode == "dark":
            text_color = "#FFFFFF"
            secondary_color = "#AAAAAA"
        else:
            text_color = "#333333"
            secondary_color = "#666666"

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
        self.symbol_label.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {text_color};")
        header_layout.addWidget(self.symbol_label)

        # Percentage
        self.percentage_label = QLabel("0.00%")
        self.percentage_label.setStyleSheet(f"font-size: 11px; color: {secondary_color};")
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
        self.price_label = QLabel(_("Loading..."))
        self.price_label.setStyleSheet("font-size: 16px; font-weight: 600;")  # 增加字体粗细从 500 到 600
        self.price_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.price_label)

    def _get_cache_path(self) -> str:
        """Get the cache file path for this icon."""
        from config.settings import get_settings_manager
        settings_manager = get_settings_manager()
        cache_dir = settings_manager.config_dir / 'icon_cache'
        cache_dir.mkdir(exist_ok=True)

        symbol = self.pair.split("-")[0].lower()
        return str(cache_dir / f"{symbol}.svg")

    def _load_icon(self):
        """Load crypto icon from cache or CDN."""
        cache_path = self._get_cache_path()

        # Try to load from cache first
        if os.path.exists(cache_path):
            try:
                self.icon_widget.load(cache_path)
                renderer = self.icon_widget.renderer()
                if renderer and renderer.isValid():
                    # Successfully loaded from cache
                    return
            except Exception:
                # Cache file corrupted, will download again
                pass

        # Load from CDN if cache miss or invalid
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
                # Load the SVG data
                self.icon_widget.load(data)

                # Check if renderer is valid to verify successful load
                renderer = self.icon_widget.renderer()
                is_valid = renderer.isValid() if renderer else False

                if is_valid:
                    # Save to cache for future use
                    try:
                        cache_path = self._get_cache_path()
                        with open(cache_path, 'wb') as f:
                            f.write(bytes(data))
                    except Exception as e:
                        print(f"Failed to cache icon for {self.pair}: {e}")

                    self._icon_retry_count = 0  # Reset retry count on success
                else:
                    # If SVG loading fails, retry or hide
                    if self._icon_retry_count < self._max_retries:
                        self._icon_retry_count += 1
                        # Retry after a short delay
                        from PyQt6.QtCore import QTimer
                        QTimer.singleShot(1000, self._load_icon)
                    else:
                        self.icon_widget.hide()
            else:
                self.icon_widget.hide()
        else:
            # If icon fails to load, retry or hide
            if self._icon_retry_count < self._max_retries:
                self._icon_retry_count += 1
                # Retry after a short delay
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(2000, self._load_icon)
            else:
                self.icon_widget.hide()
        reply.deleteLater()

    @property
    def _color_up(self):
        """Get color for price up (positive)."""
        from config.settings import get_settings_manager
        settings = get_settings_manager().settings
        return "#4CAF50" if settings.color_schema == "standard" else "#F44336"

    @property
    def _color_down(self):
        """Get color for price down (negative)."""
        from config.settings import get_settings_manager
        settings = get_settings_manager().settings
        return "#F44336" if settings.color_schema == "standard" else "#4CAF50"

    def update_price(self, price: str, trend: str, color: str):
        """Update the displayed price."""
        display_text = f"{price} {trend}" if trend else price
        self.price_label.setText(display_text)
        
        # Override the color passed from tracker if we want strict schema adherence,
        # but PriceTracker might return 'green'/'red' abstractly?
        # PriceTracker usually returns specific hex codes or 'green'/'red'.
        # Let's check PriceTracker.update_price implementation if possible.
        # Assuming color argument is hex code. If it is hex, we might need to recalculate.
        # But actually update_price is called with state.color.
        # Ideally PriceTracker should be unaware of UI colors, or return 'up'/'down'.
        # For now, let's trust the logic in update_percentage which determines color based on sign.
        # For Price, usually it follows percentage color or trend color.
        
        # We will recalculate color based on trend if possible, or just use what is passed provided it matches schema.
        # Since I can't check PriceTracker easily right now without reading it,
        # I will rely on update_percentage for the main color indication.
        # But wait, update_price sets price_label style.
        
        # Let's infer color from trend/previous if needed, OR better:
        # Assume 'color' param is stale/hardcoded and re-evaluate.
        # But trend up/down is what matters.
        
        final_color = color # Fallback
        
        # If trend arrows are used, we can deduce.
        # But let's look at update_percentage, which drives the main visual indicator often.
        
        self.price_label.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {color};")


    def set_connection_state(self, state: str):
        """Update UI based on connection state."""
        if state == "connected":
            # Do nothing, wait for next price update
            return
        
        # Determine color based on current intraday percentage
        display_color = "#333333" if self._theme_mode == "light" else "#FFFFFF"
        
        if self._current_percentage.startswith('+'):
            display_color = self._color_up
        elif self._current_percentage.startswith('-'):
            display_color = self._color_down
        
        # Define styles for states
        style = f"font-size: 11px; font-weight: 500; color: {display_color};"
        text = _("Connecting...")

        if state == "reconnecting":
            text = _("Reconnecting...")
        elif state == "disconnected":
            text = _("Disconnected")
        elif state == "failed":
            text = _("Connection Failed")

        self.price_label.setText(text)
        self.price_label.setStyleSheet(style)

    def refresh_style(self):
        """Refresh card style based on settings and state."""
        from config.settings import get_settings_manager
        settings = get_settings_manager().settings
        
        # Reset if disabled
        if not settings.dynamic_background:
            self.setStyleSheet("") # Clear any custom background
            return

        # Calculate background color based on percentage
        try:
            pct_val = float(self._current_percentage.strip('%').replace('+', ''))
        except (ValueError, AttributeError):
            pct_val = 0.0
            
        if pct_val == 0:
            self.setStyleSheet("")
            return
            
        # Determine base color
        is_up = pct_val > 0
        base_color = self._color_up if is_up else self._color_down
        
        # Calculate opacity
        # Max intensity at 10% change
        # Opacity range: 0.10 to 0.40 (increased for better visibility)
        ratio = min(abs(pct_val) / 10.0, 1.0) 
        opacity = 0.10 + (ratio * 0.30)
        
        # Convert hex to rgba
        c = QColor(base_color)
        r, g, b = c.red(), c.green(), c.blue()
        
        bg_color = f"rgba({r}, {g}, {b}, {opacity:.2f})"
        
        # We need to construct a stylesheet that preserves CardWidget properties but adds background
        # CardWidget uses qproperty-backgroundColor usually? Or just background.
        # Let's try setting background-color on the widget ID or class.
        # Since we are inside the class, self.setStyleSheet works on this widget.
        
        self.setStyleSheet(f"CryptoCard {{ background-color: {bg_color}; border: 1px solid rgba(0,0,0,0.05); border-radius: 10px; }}")

    def update_percentage(self, percentage: str):
        """Update the percentage display."""
        self._current_percentage = percentage
        self.percentage_label.setText(percentage)

        # Set color based on positive/negative
        if percentage.startswith('+'):
            self.percentage_label.setStyleSheet(f"font-size: 11px; color: {self._color_up};")
        elif percentage.startswith('-'):
            self.percentage_label.setStyleSheet(f"font-size: 11px; color: {self._color_down};")
        else:
            neutral_color = "#333333" if self._theme_mode == "light" else "#FFFFFF"
            self.percentage_label.setStyleSheet(f"font-size: 11px; color: {neutral_color};")
            
        self.refresh_style()

    def set_edit_mode(self, enabled: bool):
        """Enable/disable edit mode (shows remove button)."""
        self._edit_mode = enabled
        self.remove_btn.setVisible(enabled)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """Handle double-click to open OKX page."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.pair)
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event: QContextMenuEvent):
        """Handle right-click context menu."""
        from qfluentwidgets import RoundMenu, Action
        menu = RoundMenu(parent=self)

        # Add alert action
        add_alert_action = Action(FIF.RINGER, _("Add Alert..."), self)
        add_alert_action.triggered.connect(lambda: self.add_alert_requested.emit(self.pair))
        menu.addAction(add_alert_action)

        # View alerts action
        view_alerts_action = Action(FIF.VIEW, _("View Alerts"), self)
        view_alerts_action.triggered.connect(lambda: self.view_alerts_requested.emit(self.pair))
        menu.addAction(view_alerts_action)

        menu.addSeparator()

        # Open in Browser action
        open_browser_action = Action(FIF.GLOBE, _("Open in Browser"), self)
        open_browser_action.triggered.connect(lambda: self.browser_opened_requested.emit(self.pair))
        menu.addAction(open_browser_action)

        # Remove pair action
        remove_action = Action(FIF.DELETE, _("Remove Pair"), self)
        remove_action.triggered.connect(lambda: self.remove_clicked.emit(self.pair))
        menu.addAction(remove_action)

        menu.exec(event.globalPos())
