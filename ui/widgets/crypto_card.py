import logging
import os

from PyQt6.QtCore import Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QContextMenuEvent, QDesktopServices, QMouseEvent
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import CardWidget, TransparentToolButton
from qfluentwidgets import FluentIcon as FIF

from core.i18n import _
from ui.widgets.hover_card import HoverCard

logger = logging.getLogger(__name__)


class CryptoCard(CardWidget):
    ticker_updated = pyqtSignal(str, object)
    double_clicked = pyqtSignal(str)
    remove_clicked = pyqtSignal(str)
    add_alert_requested = pyqtSignal(str)
    view_alerts_requested = pyqtSignal(str)
    browser_opened_requested = pyqtSignal(str)

    ICON_URL_TEMPLATE = (
        "https://cdn.jsdelivr.net/gh/vadimmalykhin/binance-icons/crypto/{symbol}.svg"
    )

    def __init__(self, pair: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.pair = pair
        self._edit_mode = False
        self._icon_retry_count = 0
        self._max_retries = 3
        self._current_percentage = "0.00%"
        self._loaded_icon_url = None

        self._hover_data = {"high": "0", "low": "0", "quote_volume": "0"}

        self._chart_cache = {}

        self._setup_ui()
        self._load_icon()

        self.hover_card = HoverCard(parent=None)

        self.hover_card.update_theme(self._theme_mode)

    def update_state(self, state):
        self.update_price(state.current_price, state.trend, state.color)
        self.update_percentage(state.percentage)

        self._hover_data["high"] = state.high_24h
        self._hover_data["low"] = state.low_24h
        self._hover_data["quote_volume"] = state.quote_volume_24h
        self._hover_data["amplitude"] = state.amplitude_24h

        from core.utils import get_display_name

        display_text = get_display_name(self.pair, state.display_name, short=True)
        self.symbol_label.setText(display_text)

        if state.icon_url and state.icon_url != self._loaded_icon_url:
            self._load_icon(state.icon_url)

        if self.hover_card.isVisible():
            self._update_hover_card()

    def enterEvent(self, event):
        from config.settings import get_settings_manager

        settings = get_settings_manager().settings

        if not settings.hover_enabled:
            super().enterEvent(event)
            return

        self.hover_card.set_visibility(settings.hover_show_stats, settings.hover_show_chart)
        self._update_hover_card()

        global_pos = self.mapToGlobal(self.rect().topRight())

        x = global_pos.x() + 5
        y = global_pos.y()

        screen = self.screen()
        if screen:
            screen_geom = screen.availableGeometry()
            if x + self.hover_card.width() > screen_geom.right():
                x = self.mapToGlobal(self.rect().topLeft()).x() - self.hover_card.width() - 5

        self.hover_card.move(x, y)
        self.hover_card.show()

        self._fetch_history_data()

        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hover_card.hide()
        super().leaveEvent(event)

    def _update_hover_card(self):
        parts = self.pair.split("-")
        quote_currency = parts[1] if len(parts) > 1 else ""

        if self.pair.startswith("chain:"):
            quote_currency = "USD"

        self.hover_card.update_data(
            high=self._hover_data["high"],
            low=self._hover_data["low"],
            volume=self._hover_data["quote_volume"],
            quote_currency=quote_currency,
            amplitude=self._hover_data.get("amplitude", "0.00%"),
        )

    def _setup_ui(self):
        self.setBorderRadius(8)
        self.setMinimumWidth(100)

        from config.settings import get_settings_manager

        theme_mode = get_settings_manager().settings.theme_mode
        self._theme_mode = theme_mode

        if theme_mode == "dark":
            text_color = "#FFFFFF"
            secondary_color = "#AAAAAA"
        else:
            text_color = "#333333"
            secondary_color = "#666666"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        self.icon_widget = QSvgWidget()
        self.icon_widget.setFixedSize(16, 16)
        header_layout.addWidget(self.icon_widget)

        self.image_label = QLabel()
        self.image_label.setFixedSize(16, 16)
        self.image_label.setScaledContents(True)
        self.image_label.setVisible(False)
        header_layout.addWidget(self.image_label)

        from core.utils import get_display_name

        symbol = get_display_name(self.pair, short=True)

        self.symbol_label = QLabel(symbol)
        self.symbol_label.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {text_color};")
        header_layout.addWidget(self.symbol_label)

        self.percentage_label = QLabel("0.00%")
        self.percentage_label.setStyleSheet(f"font-size: 11px; color: {secondary_color};")
        header_layout.addWidget(self.percentage_label)

        header_layout.addStretch()

        self.remove_btn = TransparentToolButton(FIF.DELETE, self)
        self.remove_btn.setFixedSize(20, 20)
        self.remove_btn.setVisible(False)
        self.remove_btn.clicked.connect(lambda: self.remove_clicked.emit(self.pair))
        header_layout.addWidget(self.remove_btn)

        layout.addLayout(header_layout)

        self.price_label = QLabel(_("Loading..."))
        self.price_label.setStyleSheet("font-size: 16px; font-weight: 600;")
        self.price_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.price_label)

    def _get_cache_path(self, ext: str = ".svg") -> str:
        from config.settings import get_settings_manager

        settings_manager = get_settings_manager()
        cache_dir = settings_manager.config_dir / "icon_cache"
        cache_dir.mkdir(exist_ok=True)

        if self.pair.startswith("chain:"):
            parts = self.pair.split(":")
            filename = parts[2] if len(parts) >= 3 else "unknown"
            return str(cache_dir / f"{filename}{ext}")

        symbol = self.pair.split("-")[0].lower()
        return str(cache_dir / f"{symbol}{ext}")

    def _load_from_cache(self) -> bool:
        # Try loading from cache with different extensions
        for ext in [".svg", ".png", ".jpg", ".jpeg"]:
            cache_path = self._get_cache_path(ext)
            if os.path.exists(cache_path):
                try:
                    if ext == ".svg":
                        self.icon_widget.load(cache_path)
                        renderer = self.icon_widget.renderer()
                        if renderer and renderer.isValid():
                            self.icon_widget.show()
                            self.image_label.hide()
                            return True
                    else:
                        from PyQt6.QtGui import QPixmap

                        pixmap = QPixmap(cache_path)
                        if not pixmap.isNull():
                            self.image_label.setPixmap(pixmap)
                            self.image_label.show()
                            self.icon_widget.hide()
                            return True
                except Exception:
                    continue
        return False

    def _load_icon(self, url_override: str = None):
        if self.pair.startswith("chain:") and not url_override:
            if self._load_from_cache():
                return
            return

        if not url_override:
            if self._load_from_cache():
                return

        url = url_override
        if not url:
            symbol = self.pair.split("-")[0].lower()
            url = self.ICON_URL_TEMPLATE.format(symbol=symbol)

        self._loaded_icon_url = url

        self._network_manager = QNetworkAccessManager(self)

        from config.settings import get_settings_manager

        settings = get_settings_manager().settings
        if settings.proxy.enabled:
            from PyQt6.QtNetwork import QNetworkProxy

            proxy = QNetworkProxy()
            if settings.proxy.type.lower() == "http":
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
        request.setHeader(QNetworkRequest.KnownHeaders.UserAgentHeader, "Mozilla/5.0")
        self._network_manager.get(request)
        logger.debug(f"Fetching icon for {self.pair}: {url}")

    def _on_icon_loaded(self, reply: QNetworkReply):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = reply.readAll()
            if len(data) > 0:
                data_bytes = bytes(data)
                is_svg = b"<svg" in data_bytes[:100].lower() or b"xml" in data_bytes[:100].lower()

                if is_svg:
                    self.icon_widget.load(data)
                    renderer = self.icon_widget.renderer()
                    if renderer and renderer.isValid():
                        self.icon_widget.show()
                        self.image_label.hide()
                        try:
                            cache_path = self._get_cache_path(".svg")
                            with open(cache_path, "wb") as f:
                                f.write(data_bytes)
                        except Exception:
                            pass
                        self._icon_retry_count = 0
                else:
                    from PyQt6.QtGui import QPixmap

                    pixmap = QPixmap()
                    if pixmap.loadFromData(data_bytes):
                        self.image_label.setPixmap(pixmap)
                        self.image_label.show()
                        self.icon_widget.hide()

                        ext = ".png"
                        if data_bytes.startswith(b"\xff\xd8"):
                            ext = ".jpg"

                        try:
                            cache_path = self._get_cache_path(ext)
                            with open(cache_path, "wb") as f:
                                f.write(data_bytes)
                        except Exception:
                            pass
                        self._icon_retry_count = 0
                    else:
                        logger.warning(
                            f"Failed to load pixmap from data for {self.pair} ({len(data)} bytes)"
                        )
            else:
                self.icon_widget.hide()
                self.image_label.hide()
                logger.warning(f"Empty icon data received for {self.pair}")
        else:
            logger.warning(f"Icon download failed for {self.pair}: {reply.errorString()}")
            if self._icon_retry_count < self._max_retries:
                self._icon_retry_count += 1
                QTimer.singleShot(2000, lambda: self._load_icon(self._loaded_icon_url))
            else:
                self.icon_widget.hide()
                self.image_label.hide()
        reply.deleteLater()

    @property
    def _color_up(self):
        from config.settings import get_settings_manager

        settings = get_settings_manager().settings
        return "#4CAF50" if settings.color_schema == "standard" else "#F44336"

    @property
    def _color_down(self):
        from config.settings import get_settings_manager

        settings = get_settings_manager().settings
        return "#F44336" if settings.color_schema == "standard" else "#4CAF50"

    def update_price(self, price: str, trend: str, color: str):
        display_text = f"{price} {trend}" if trend else price
        self.price_label.setText(display_text)
        self.price_label.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {color};")

    def set_connection_state(self, state: str):
        if state == "connected":
            return

        display_color = "#333333" if self._theme_mode == "light" else "#FFFFFF"

        if self._current_percentage.startswith("+"):
            display_color = self._color_up
        elif self._current_percentage.startswith("-"):
            display_color = self._color_down

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
        from config.settings import get_settings_manager

        settings = get_settings_manager().settings

        if not settings.dynamic_background:
            self.setStyleSheet("")
            return

        try:
            pct_val = float(self._current_percentage.strip("%").replace("+", ""))
        except (ValueError, AttributeError):
            pct_val = 0.0

        if pct_val == 0:
            self.setStyleSheet("")
            return

        is_up = pct_val > 0
        base_color = self._color_up if is_up else self._color_down

        ratio = min(abs(pct_val) / 10.0, 1.0)
        opacity = 0.10 + (ratio * 0.30)

        c = QColor(base_color)
        r, g, b = c.red(), c.green(), c.blue()

        bg_color = f"rgba({r}, {g}, {b}, {opacity:.2f})"

        self.setStyleSheet(
            f"CryptoCard {{ background-color: {bg_color}; "
            f"border: 1px solid rgba(0,0,0,0.05); border-radius: 10px; }}"
        )

    def update_percentage(self, percentage: str):
        self._current_percentage = percentage
        self.percentage_label.setText(percentage)

        if percentage.startswith("+"):
            self.percentage_label.setStyleSheet(f"font-size: 11px; color: {self._color_up};")
        elif percentage.startswith("-"):
            self.percentage_label.setStyleSheet(f"font-size: 11px; color: {self._color_down};")
        else:
            neutral_color = "#333333" if self._theme_mode == "light" else "#FFFFFF"
            self.percentage_label.setStyleSheet(f"font-size: 11px; color: {neutral_color};")

        self.refresh_style()

    def set_edit_mode(self, enabled: bool):
        self._edit_mode = enabled
        self.remove_btn.setVisible(enabled)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.pair.startswith("chain:"):
                parts = self.pair.split(":")
                if len(parts) >= 3:
                    net = parts[1]
                    addr = parts[2]
                    url = f"https://dexscreener.com/{net}/{addr}"
                    QDesktopServices.openUrl(QUrl(url))
            else:
                self.double_clicked.emit(self.pair)
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event: QContextMenuEvent):
        from qfluentwidgets import Action, RoundMenu

        menu = RoundMenu(parent=self)

        add_alert_action = Action(FIF.RINGER, _("Add Alert..."), self)
        add_alert_action.triggered.connect(lambda: self.add_alert_requested.emit(self.pair))
        menu.addAction(add_alert_action)

        view_alerts_action = Action(FIF.VIEW, _("View Alerts"), self)
        view_alerts_action.triggered.connect(lambda: self.view_alerts_requested.emit(self.pair))
        menu.addAction(view_alerts_action)

        menu.addSeparator()

        open_browser_action = Action(FIF.GLOBE, _("Open in Browser"), self)
        open_browser_action.triggered.connect(lambda: self.browser_opened_requested.emit(self.pair))
        menu.addAction(open_browser_action)

        remove_action = Action(FIF.DELETE, _("Remove Pair"), self)
        remove_action.triggered.connect(lambda: self.remove_clicked.emit(self.pair))
        menu.addAction(remove_action)

        menu.exec(event.globalPos())

    def _fetch_history_data(self):
        import time

        from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal

        from config.settings import get_settings_manager

        settings = get_settings_manager().settings
        current_period = settings.kline_period.upper()
        cache_ttl = settings.chart_cache_ttl
        now = time.time()

        if self._chart_cache:
            cached_period = self._chart_cache.get("period", "24H")
            if (now - self._chart_cache.get("timestamp", 0) < cache_ttl) and (
                cached_period == current_period
            ):
                data = self._chart_cache.get("data", [])
                if data:
                    self.hover_card.update_chart(data, current_period)
                    return

        self.hover_card.set_chart_loading()

        if not settings.hover_show_chart:
            return

        exchange = settings.data_source

        class WorkerSignals(QObject):
            data_ready = pyqtSignal(list, str)

        class KlineRunnable(QRunnable):
            def __init__(self, exchange_name, pair):
                super().__init__()
                self.signals = WorkerSignals()
                self.exchange_name = exchange_name
                self.pair = pair

            def run(self):
                client = None
                try:
                    from config.settings import get_settings_manager
                    from core.exchange_factory import ExchangeFactory

                    client = ExchangeFactory.create_client(None)

                    settings = get_settings_manager().settings
                    period_setting = settings.kline_period
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

                    klines = client.fetch_klines(self.pair, interval, limit)

                    if not klines:
                        self.signals.data_ready.emit([], "No data")
                    else:
                        closes = [k["close"] for k in klines]
                        self.signals.data_ready.emit(closes, "")

                except Exception as e:
                    self.signals.data_ready.emit([], str(e))

                finally:
                    if client:
                        try:
                            if hasattr(client, "close"):
                                client.close()
                            if hasattr(client, "stop"):
                                client.stop()
                        except Exception:
                            pass

        runnable = KlineRunnable(exchange, self.pair)
        runnable.signals.data_ready.connect(self._on_kline_data_ready)
        QThreadPool.globalInstance().start(runnable)

    def _on_kline_data_ready(self, data: list, error: str):
        import time

        from config.settings import get_settings_manager

        period = get_settings_manager().settings.kline_period.upper()

        if data and not error:
            self._chart_cache = {
                "timestamp": time.time(),
                "data": data,
                "period": period,
            }
            if self.hover_card.isVisible():
                self.hover_card.update_chart(data, period)
        else:
            if self.hover_card.isVisible():
                self.hover_card.update_chart([], period, error)
