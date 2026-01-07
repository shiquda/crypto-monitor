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


from ui.widgets.hover_card import HoverCard

class CryptoCard(CardWidget):
    """Fluent Design card widget displaying a single crypto pair's information."""

    # ... (signals remain same)

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
        
        # Extended data storage
        self._hover_data = {
            "high": "0",
            "low": "0",
            "quote_volume": "0"
        }
        
        # Chart data cache
        # {timestamp: float, data: list}
        self._chart_cache = {}
        self._chart_cache_ttl = 300 # 5 minutes

        
        self._setup_ui()
        self._load_icon()
        
        # Initialize HoverCard (no parent to allow floating)
        self.hover_card = HoverCard(parent=None)
        
        # Apply current theme to hover card
        self.hover_card.update_theme(self._theme_mode)

    # ... (methods _setup_ui to update_price remain same, skip to update_state)


    def update_state(self, state):
        """
        Update the card state with extended data.
        
        Args:
            state: PriceState object containing price, percentage, and extended data.
        """
        self.update_price(state.current_price, state.trend, state.color)
        self.update_percentage(state.percentage)
        
        # Store latest extended data
        self._hover_data["high"] = state.high_24h
        self._hover_data["low"] = state.low_24h
        self._hover_data["quote_volume"] = state.quote_volume_24h
        self._hover_data["amplitude"] = state.amplitude_24h
        
        # Update hover card if visible
        if self.hover_card.isVisible():
            self._update_hover_card()

    def enterEvent(self, event):
        """Show hover card on mouse enter."""
        from config.settings import get_settings_manager
        settings = get_settings_manager().settings
        if not settings.hover_enabled:
            super().enterEvent(event)
            return

        self.hover_card.set_visibility(settings.hover_show_stats, settings.hover_show_chart)
        self._update_hover_card()
        
        # Position the card relative to this widget
        # Calculate global position
        global_pos = self.mapToGlobal(self.rect().topRight())
        
        # default to right side
        x = global_pos.x() + 5
        y = global_pos.y()
        
        # Check if it goes off screen (simple check)
        screen = self.screen()
        if screen:
             screen_geom = screen.availableGeometry()
             if x + self.hover_card.width() > screen_geom.right():
                 # Move to left side
                 x = self.mapToGlobal(self.rect().topLeft()).x() - self.hover_card.width() - 5
        
        self.hover_card.move(x, y)
        self.hover_card.show()
        
        # Trigger chart data fetch
        self._fetch_history_data()
        
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Hide hover card on mouse leave."""
        self.hover_card.hide()
        super().leaveEvent(event)

    def _update_hover_card(self):
        """Update hover card content."""
        parts = self.pair.split('-')
        quote_currency = parts[1] if len(parts) > 1 else ""
        
        self.hover_card.update_data(
            high=self._hover_data["high"],
            low=self._hover_data["low"],
            volume=self._hover_data["quote_volume"],
            quote_currency=quote_currency,
            amplitude=self._hover_data.get("amplitude", "0.00%")
        )

    # ... (keep format_volume and other methods if needed, remove _update_tooltip)



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

    def _fetch_history_data(self):
        """Fetch historical k-line data in background."""
        import time
        from PyQt6.QtCore import QThread, pyqtSignal
        
        # Check cache
        now = time.time()
        from config.settings import get_settings_manager
        current_period = get_settings_manager().settings.kline_period.upper()

        if self._chart_cache:
            # Check TTL and if period matches
            cached_period = self._chart_cache.get("period", "24H") 
            if (now - self._chart_cache.get("timestamp", 0) < self._chart_cache_ttl) and (cached_period == current_period):
                # Cache hit
                data = self._chart_cache.get("data", [])
                if data:
                     self.hover_card.update_chart(data, current_period)
                     return

        # Cache miss or expired
        self.hover_card.set_chart_loading()
        
        # Get client from main window (a bit hacky, but standard way in this app structure)
        # We need access to the active exchange client.
        # This widget is created by MainWindow -> FlowLayout
        # Ideally, we should pass the client or have a global accessor.
        # For now, let's use the settings to determine which client to recreate purely for fetching,
        # OR better, if we can access the single instance.
        
        # Since we are inside a widget, acquiring the main window instance is tricky without passing it.
        # However, we can create a temporary client instance just for REST call, 
        # OR we rely on the fact that we are just doing a REST call which is stateless mostly.
        
        if getattr(self, '_kline_worker', None) and self._kline_worker.isRunning():
            return

        from config.settings import get_settings_manager
        settings = get_settings_manager().settings
        
        if not settings.hover_show_chart:
            # Clear any existing chart? Or just don't fetch new info.
            # If we don't fetch, we should probably hide the chart in the UI.
            # The HoverCard update logic should handle visibility, 
            # but we can save resources by not fetching.
            return

        exchange = settings.data_source
        
        # Define a worker thread class locally or use a generic one
        class KlineWorker(QThread):
            data_ready = pyqtSignal(list, str) # data, error_msg
            
            def __init__(self, exchange_name, pair):
                super().__init__()
                self.exchange_name = exchange_name
                self.pair = pair
                
            def run(self):
                try:
                    # Determine interval and limit based on settings
                    period_setting = settings.kline_period # "1h", "4h", "12h", "24h", "7d"
                    
                    # Default (24h)
                    interval = "30m"
                    limit = 48
                    
                    if period_setting == "1h":
                        interval = "1m"
                        limit = 60
                    elif period_setting == "4h":
                        interval = "5m"
                        limit = 48
                    elif period_setting == "12h":
                        interval = "15m"
                        limit = 48
                    elif period_setting == "24h":
                        interval = "30m"
                        limit = 48
                    elif period_setting == "7d":
                        interval = "4h"
                        limit = 42
                    
                    # Normalize exchange name to lowercase for comparison
                    exchange_lower = self.exchange_name.lower()
                    
                    klines = []
                    
                    if exchange_lower == "binance":
                        from core.binance_client import BinanceClient
                        try:
                            client = BinanceClient(None)
                            klines = client.fetch_klines(self.pair, interval, limit)
                            # Verify result
                            if not klines:
                                self.data_ready.emit([], "Empty response from Binance")
                                client.deleteLater()
                                return
                            client.deleteLater()
                        except Exception as e:
                            self.data_ready.emit([], f"Binance Client Error: {str(e)}")
                            return
                        
                    elif exchange_lower == "okx":
                        from core.okx_client import OkxClientManager
                        try:
                            client = OkxClientManager(None)
                            klines = client.fetch_klines(self.pair, interval, limit)
                            if not klines:
                                self.data_ready.emit([], "Empty response from OKX")
                                client.deleteLater()
                                return
                            client.deleteLater()
                        except Exception as e:
                            self.data_ready.emit([], f"OKX Client Error: {str(e)}")
                            return
                    
                    # Extract close prices for sparkline
                    closes = [k["close"] for k in klines]
                    self.data_ready.emit(closes, "")
                    
                except Exception as e:
                    print(f"Error fetching klines: {e}")
                    self.data_ready.emit([], str(e))

        self._kline_worker = KlineWorker(exchange, self.pair)
        self._kline_worker.data_ready.connect(self._on_kline_data_ready)
        self._kline_worker.start()

    def _on_kline_data_ready(self, data: list, error: str):
        """Handle kline data ready."""
        import time
        from config.settings import get_settings_manager
        period = get_settings_manager().settings.kline_period.upper()
        
        # Identify the worker that emitted this signal
        sender_worker = self.sender()
        
        if data and not error:
            # Update cache
            self._chart_cache = {
                "timestamp": time.time(),
                "data": data,
                "period": period # Cache period too, if settings change we shouldn't use old cache ideally?
            }
            # Update UI
            # Verify hover card is still visible before updating to avoid weird states
            if self.hover_card.isVisible():
                 self.hover_card.update_chart(data, period)
        else:
            # Handle error/empty
             if self.hover_card.isVisible():
                self.hover_card.update_chart([], period, error)
        
        # Clean up the specific worker that finished
        if sender_worker:
            sender_worker.deleteLater()
            
        # If this was the current active worker, clear the reference
        if getattr(self, '_kline_worker', None) == sender_worker:
            self._kline_worker = None
