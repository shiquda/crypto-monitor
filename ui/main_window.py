"""
Main application window using Fluent Design.
"""

import webbrowser
from typing import Optional, Dict
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QScrollArea,
    QApplication
)
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QIcon, QMouseEvent
from qfluentwidgets import setTheme, Theme

from ui.widgets.toolbar import Toolbar
from ui.widgets.crypto_card import CryptoCard
from ui.widgets.pagination import Pagination
from ui.widgets.add_pair_dialog import AddPairDialog
from ui.widgets.alert_dialog import AlertDialog
from ui.widgets.alert_list_dialog import AlertListDialog
from ui.settings_window import SettingsWindow

from core.i18n import _
from core.okx_client import OkxClientManager
from core.exchange_factory import ExchangeFactory
from core.price_tracker import PriceTracker
from core.alert_manager import get_alert_manager
from config.settings import get_settings_manager


class MainWindow(QMainWindow):
    """Main application window with Fluent Design components."""

    ITEMS_PER_PAGE = 3

    def __init__(self):
        super().__init__()

        self._drag_pos: Optional[QPoint] = None
        self._settings_window: Optional[SettingsWindow] = None
        self._cards: Dict[str, CryptoCard] = {}
        self._edit_mode = False

        # Core components
        self._settings_manager = get_settings_manager()
        self._exchange_client = ExchangeFactory.create_client(self)
        self._price_tracker = PriceTracker()
        self._alert_manager = get_alert_manager()

        # Apply theme based on settings
        theme_mode = self._settings_manager.settings.theme_mode
        setTheme(Theme.DARK if theme_mode == "dark" else Theme.LIGHT)

        self._setup_ui()
        self._connect_signals()
        self._load_pairs()

    def _setup_ui(self):
        """Setup the main window UI with Fluent Design components."""
        # Window flags: frameless, stay on top optional
        flags = Qt.WindowType.FramelessWindowHint
        if self._settings_manager.settings.always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

        # Enable translucent background for rounded corners
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Window size and icon - 降低高度从 360 到 320
        self.setFixedSize(160, 320)
        self.setWindowIcon(QIcon("assets/icons/crypto-monitor.png"))
        self.setWindowTitle(_("Crypto Monitor"))


        # Move to saved position


        # Move to saved position
        self.move(
            self._settings_manager.settings.window_x,
            self._settings_manager.settings.window_y
        )

        # Central widget with rounded corners
        central = QWidget()
        # Apply theme-based background color
        theme_mode = self._settings_manager.settings.theme_mode
        bg_color = "#1B2636" if theme_mode == "dark" else "#FAFAFA"
        central.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color};
                border-radius: 8px;
            }}
        """)
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 8, 10, 8)  # 增加左右留白从 5 到 10
        layout.setSpacing(5)

        # Toolbar
        self.toolbar = Toolbar()
        layout.addWidget(self.toolbar)

        # Cards container (scrollable)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(8)  # 增加卡片间距从 5 到 8
        self.cards_layout.addStretch()

        self.scroll_area.setWidget(self.cards_container)
        layout.addWidget(self.scroll_area, 1)

        # Pagination
        self.pagination = Pagination()
        layout.addWidget(self.pagination)

    def _connect_signals(self):
        """Connect signals to slots."""
        # Toolbar signals
        self.toolbar.settings_clicked.connect(self._open_settings)
        self.toolbar.add_clicked.connect(self._toggle_edit_mode)
        self.toolbar.minimize_clicked.connect(self.showMinimized)
        self.toolbar.pin_clicked.connect(self._toggle_always_on_top)
        self.toolbar.close_clicked.connect(self._close_app)

        # Pagination
        self.pagination.page_changed.connect(self._on_page_changed)

        # Exchange client signals
        self._exchange_client.ticker_updated.connect(self._on_ticker_update)
        self._exchange_client.connection_status.connect(self._on_connection_status)
        self._exchange_client.connection_state_changed.connect(self._on_connection_state_changed)

    def _load_pairs(self):
        """Load pairs from settings and subscribe."""
        pairs = self._settings_manager.settings.crypto_pairs

        # Calculate pagination
        total_pages = max(1, (len(pairs) + self.ITEMS_PER_PAGE - 1) // self.ITEMS_PER_PAGE)
        self.pagination.set_total_pages(total_pages)
        self.pagination.setVisible(total_pages > 1)

        # Create cards for current page
        self._update_cards_display()

        # Subscribe to all pairs
        if pairs:
            self._exchange_client.subscribe(pairs)

    def _update_cards_display(self):
        """Update the displayed cards based on current page."""
        pairs = self._settings_manager.settings.crypto_pairs
        current_page = self.pagination.current_page()

        # Calculate slice for current page
        start = (current_page - 1) * self.ITEMS_PER_PAGE
        end = start + self.ITEMS_PER_PAGE
        visible_pairs = pairs[start:end]

        # Clear existing cards from layout (but keep them cached)
        while self.cards_layout.count() > 1:  # Keep the stretch
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        # Add cards for visible pairs
        for pair in visible_pairs:
            if pair not in self._cards:
                card = CryptoCard(pair)
                card.double_clicked.connect(self._open_pair_in_browser)
                card.browser_opened_requested.connect(self._open_pair_in_browser)
                card.remove_clicked.connect(self._remove_pair)
                card.add_alert_requested.connect(self._on_add_alert_requested)
                card.view_alerts_requested.connect(self._on_view_alerts_requested)
                self._cards[pair] = card

            card = self._cards[pair]
            card.set_edit_mode(self._edit_mode)
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)

    def _on_page_changed(self, page: int):
        """Handle page change."""
        self._update_cards_display()

    def _on_ticker_update(self, pair: str, price: str, percentage: str):
        """Handle ticker update from OKX."""
        # Update price tracker
        state = self._price_tracker.update_price(pair, price, percentage)

        # Update card if visible
        if pair in self._cards:
            self._cards[pair].update_price(price, state.trend, state.color)
            self._cards[pair].update_percentage(percentage)

        # Check price alerts
        self._alert_manager.check_alerts(pair, price, percentage)

    def _on_connection_status(self, connected: bool, message: str):
        """Handle connection status change."""
        print(f"Connection status: {connected}, {message}")

    def _on_connection_state_changed(self, state: str, message: str, retry_count: int):
        """
        Handle detailed connection state change.
        Updates UI to reflect connecting/reconnecting status.
        """
        print(f"Connection state: {state} ({message}) - Retry: {retry_count}")
        
        # Update all cards with connection state
        for card in self._cards.values():
            card.set_connection_state(state)

    def _open_settings(self):
        """Open settings window."""
        if self._settings_window is None or not self._settings_window.isVisible():
            self._settings_window = SettingsWindow(self._settings_manager)
            self._settings_window.proxy_changed.connect(self._on_proxy_changed)
            self._settings_window.pairs_changed.connect(self._on_pairs_changed)
            self._settings_window.theme_changed.connect(self._on_theme_changed)
            self._settings_window.data_source_changed.connect(self._on_data_source_changed)
            self._settings_window.show()
        else:
            self._settings_window.activateWindow()
            self._settings_window.raise_()

    def _on_proxy_changed(self):
        """Handle proxy configuration change."""
        # Reconnect with new proxy settings
        self._exchange_client.reconnect()

    def _on_pairs_changed(self):
        """Handle crypto pairs change."""
        # Reload pairs and resubscribe
        self._load_pairs()

    def _on_theme_changed(self):
        """Handle theme change."""
        # Theme change requires application restart
        pass

    def _on_data_source_changed(self):
        """Handle data source change."""
        print("Data source changed, switching client...")
        
        # Reset alert manager state to prevent false alerts due to price differences
        self._alert_manager.reset()
        
        # Stop existing client
        if self._exchange_client:
            # Safe cleanup: wait for client to fully stop before checking for deletion
            old_client = self._exchange_client
            
            # CRITICAL: Disconnect all signals from the old client to the main window
            # This prevents ticker updates or state changes from reaching this window
            # while the new client is being set up.
            try:
                old_client.ticker_updated.disconnect(self._on_ticker_update)
                old_client.connection_status.disconnect(self._on_connection_status)
                old_client.connection_state_changed.disconnect(self._on_connection_state_changed)
            except (TypeError, RuntimeError):
                # Signals might already be disconnected
                pass
                
            # Connect the stopped signal to deleteLater on the old client object
            old_client.stopped.connect(old_client.deleteLater)
            old_client.stop()
            # Clean reference immediately so new client can assume control
            self._exchange_client = None
            
        # Create new client
        self._exchange_client = ExchangeFactory.create_client(self)
        
        # Connect signals
        self._exchange_client.ticker_updated.connect(self._on_ticker_update)
        self._exchange_client.connection_status.connect(self._on_connection_status)
        self._exchange_client.connection_state_changed.connect(self._on_connection_state_changed)
        
        # Resubscribe
        self._load_pairs()

    def _toggle_edit_mode(self):
        """Toggle edit mode (add/remove pairs)."""
        if self._edit_mode:
            # Exit edit mode
            self._edit_mode = False
            for card in self._cards.values():
                card.set_edit_mode(False)
        else:
            # Show add pair dialog
            pair = AddPairDialog.get_new_pair(self)
            if pair:
                self._add_pair(pair)

    def _add_pair(self, pair: str):
        """Add a new trading pair."""
        if self._settings_manager.add_pair(pair):
            self._load_pairs()

    def _remove_pair(self, pair: str):
        """Remove a trading pair."""
        if self._settings_manager.remove_pair(pair):
            # Remove card
            if pair in self._cards:
                self._cards[pair].deleteLater()
                del self._cards[pair]
            self._price_tracker.clear_pair(pair)
            self._load_pairs()

    def _open_pair_in_browser(self, pair: str):
        """Open the trading pair in the browser based on the current data source."""
        source = self._settings_manager.settings.data_source
        lang = self._settings_manager.settings.language
        
        if source.lower() == "binance":
            # Binance format: BTC_USDT
            formatted_pair = pair.replace("-", "_").upper()
            # Determine locale prefix
            # Map zh_CN to zh-CN, others default to en (or we could map more if needed)
            locale_prefix = "zh-CN" if lang == "zh_CN" else "en"
            url = f"https://www.binance.com/{locale_prefix}/trade/{formatted_pair}"
        else:
            # OKX format: btc-usdt
            formatted_pair = pair.lower()
            # OKX uses zh-hans for Simplified Chinese
            if lang == "zh_CN":
                url = f"https://www.okx.com/zh-hans/trade-spot/{formatted_pair}"
            else:
                url = f"https://www.okx.com/trade-spot/{formatted_pair}"

        webbrowser.open(url)

    def _on_add_alert_requested(self, pair: str):
        """Handle add alert request from card context menu."""
        current_price = self._alert_manager.get_current_price(pair)
        alert = AlertDialog.create_alert(
            parent=self,
            pair=pair,
            current_price=current_price,
            available_pairs=self._settings_manager.settings.crypto_pairs
        )
        if alert:
            self._settings_manager.add_alert(alert)

    def _on_view_alerts_requested(self, pair: str):
        """Handle view alerts request from card context menu."""
        # Open alert list dialog for the specific pair
        dialog = AlertListDialog(pair, parent=self)
        dialog.exec()

    def _toggle_always_on_top(self, pinned: bool):
        """Toggle always-on-top mode."""
        self._settings_manager.settings.always_on_top = pinned
        self._settings_manager.save()

        flags = self.windowFlags()
        if pinned:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint

        self.setWindowFlags(flags)
        self.show()

    def _close_app(self):
        """Close the application."""
        # Save window position
        pos = self.pos()
        self._settings_manager.settings.window_x = pos.x()
        self._settings_manager.settings.window_y = pos.y()
        self._settings_manager.save()

        # Stop exchange client
        self._exchange_client.stop()

        # Close application
        QApplication.quit()

    # Window dragging
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press for window dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move for window dragging."""
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release."""
        self._drag_pos = None
        super().mouseReleaseEvent(event)

