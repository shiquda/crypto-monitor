"""
Main application window.
"""

import webbrowser
from typing import Optional, Dict
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QScrollArea,
    QApplication
)
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QMouseEvent, QIcon

from ui.widgets.toolbar import Toolbar
from ui.widgets.crypto_card import CryptoCard
from ui.widgets.pagination import Pagination
from ui.widgets.add_pair_dialog import AddPairDialog
from ui.settings_window import SettingsWindow
from ui.styles.theme import get_stylesheet

from core.okx_client import OkxClientManager
from core.price_tracker import PriceTracker
from config.settings import get_settings_manager


class MainWindow(QMainWindow):
    """Main application window."""

    ITEMS_PER_PAGE = 3

    def __init__(self):
        super().__init__()
        self._drag_pos: Optional[QPoint] = None
        self._settings_window: Optional[SettingsWindow] = None
        self._cards: Dict[str, CryptoCard] = {}
        self._edit_mode = False

        # Core components
        self._settings_manager = get_settings_manager()
        self._okx_client = OkxClientManager(self)
        self._price_tracker = PriceTracker()

        self._setup_ui()
        self._connect_signals()
        self._load_pairs()

    def _setup_ui(self):
        """Setup the main window UI."""
        # Window flags: frameless, stay on top optional
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint if self._settings_manager.settings.always_on_top
            else Qt.WindowType.FramelessWindowHint
        )

        # Window size
        self.setFixedSize(160, 360)
        self.setStyleSheet(get_stylesheet("main_window"))

        # Set window icon for taskbar
        self.setWindowIcon(QIcon("assets/icons/crypto-monitor.png"))

        # Move to saved position
        self.move(
            self._settings_manager.settings.window_x,
            self._settings_manager.settings.window_y
        )

        # Central widget
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(5, 5, 5, 5)
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
        self.cards_layout.setSpacing(5)
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

        # OKX client signals
        self._okx_client.ticker_updated.connect(self._on_ticker_update)
        self._okx_client.connection_status.connect(self._on_connection_status)

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
            self._okx_client.subscribe(pairs)

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
                card.double_clicked.connect(self._on_card_double_click)
                card.remove_clicked.connect(self._remove_pair)
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

    def _on_connection_status(self, connected: bool, message: str):
        """Handle connection status change."""
        print(f"Connection status: {connected}, {message}")

    def _open_settings(self):
        """Open settings window."""
        if self._settings_window is None or not self._settings_window.isVisible():
            self._settings_window = SettingsWindow(self._settings_manager)
            self._settings_window.proxy_changed.connect(self._on_proxy_changed)
            self._settings_window.pairs_changed.connect(self._on_pairs_changed)
            self._settings_window.show()
        else:
            self._settings_window.activateWindow()
            self._settings_window.raise_()

    def _on_proxy_changed(self):
        """Handle proxy configuration change."""
        # Reconnect with new proxy settings
        self._okx_client.reconnect()

    def _on_pairs_changed(self):
        """Handle crypto pairs change."""
        # Reload pairs and resubscribe
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

    def _on_card_double_click(self, pair: str):
        """Handle double-click on card to open OKX page."""
        formatted_pair = pair.lower()
        url = f"https://www.okx.com/trade-spot/{formatted_pair}"
        webbrowser.open(url)

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

        # Stop OKX client
        self._okx_client.stop()

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
