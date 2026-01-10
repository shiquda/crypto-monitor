"""
Main application window using Fluent Design.
"""

import logging
import webbrowser

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QMouseEvent
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import Theme, setTheme

from config.settings import get_settings_manager
from core.i18n import _
from core.market_data_controller import MarketDataController

# New components
from ui.behaviors.window_behavior import DraggableWindowBehavior
from ui.managers.pagination_manager import PaginationManager
from ui.managers.view_manager import ViewManager
from ui.settings_window import SettingsWindow
from ui.widgets.add_pair_dialog import AddPairDialog
from ui.widgets.alert_dialog import AlertDialog
from ui.widgets.alert_list_dialog import AlertListDialog
from ui.widgets.crypto_card import CryptoCard
from ui.widgets.pagination import Pagination
from ui.widgets.toolbar import Toolbar

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window with Fluent Design components."""

    def __init__(self):
        super().__init__()

        self._settings_window: SettingsWindow | None = None
        self._cards: dict[str, CryptoCard] = {}
        self._edit_mode = False

        # Core components
        self._settings_manager = get_settings_manager()
        self._market_controller = MarketDataController(self)

        # Initialize Managers and Behaviors
        self._window_behavior = DraggableWindowBehavior(self)
        self._view_manager = ViewManager(self, self._settings_manager)

        # Apply theme based on settings
        theme_mode = self._settings_manager.settings.theme_mode
        setTheme(Theme.DARK if theme_mode == "dark" else Theme.LIGHT)

        self._setup_ui()

        # Pagination Manager requires UI components to be initialized
        self._pagination_manager = PaginationManager(
            self, self.pagination, self.cards_layout, self._settings_manager
        )

        self._view_manager.setup_animations(self.toolbar, self.pagination)
        self._connect_signals()

        # Start data controller
        self._load_pairs()
        self._pagination_manager.setup_auto_scroll()
        self._market_controller.start()

        # Initial size adjustment
        QTimer.singleShot(100, self._view_manager.adjust_window_height)

    def _setup_ui(self):
        """Setup the main window UI with Fluent Design components."""
        flags = Qt.WindowType.FramelessWindowHint
        if self._settings_manager.settings.always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowIcon(QIcon("assets/icons/crypto-monitor.png"))
        self.setWindowTitle(_("Crypto Monitor"))

        # Move to saved position
        self.move(
            self._settings_manager.settings.window_x,
            self._settings_manager.settings.window_y,
        )

        central = QWidget()
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
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(5)

        self.toolbar = Toolbar()
        layout.addWidget(self.toolbar)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(8)
        self.cards_layout.addStretch()

        self.scroll_area.setWidget(self.cards_container)
        layout.addWidget(self.scroll_area, 1)

        self.pagination = Pagination()
        layout.addWidget(self.pagination)

    def _connect_signals(self):
        """Connect signals to slots."""
        self.toolbar.settings_clicked.connect(self._open_settings)
        self.toolbar.add_clicked.connect(self._toggle_edit_mode)
        self.toolbar.minimize_clicked.connect(self.showMinimized)
        self.toolbar.pin_clicked.connect(self._toggle_always_on_top)
        self.toolbar.close_clicked.connect(self._close_app)

        self.pagination.page_changed.connect(self._on_page_changed)

        self._market_controller.ticker_updated.connect(self._on_ticker_update)
        self._market_controller.connection_status_changed.connect(self._on_connection_status)
        self._market_controller.connection_state_changed.connect(self._on_connection_state_changed)
        self._market_controller.data_source_changed.connect(self._on_data_source_changed_complete)

    def _load_pairs(self):
        """Load pairs from settings and subscribe."""
        pairs = self._settings_manager.settings.crypto_pairs
        self._pagination_manager.refresh_pagination_state(len(pairs))
        self._update_cards_display()
        self._market_controller.reload_pairs()

    def _update_cards_display(self):
        """Update the displayed cards based on current page."""
        pairs = self._settings_manager.settings.crypto_pairs
        visible_pairs = self._pagination_manager.get_visible_slice(pairs)

        # Clear existing cards from layout (but keep them cached)
        while self.cards_layout.count() > 1:
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

        self._view_manager.adjust_window_height()

    def _open_settings(self):
        """Open settings window."""
        if self._settings_window is None or not self._settings_window.isVisible():
            self._settings_window = SettingsWindow(self._settings_manager)
            self._settings_window.proxy_changed.connect(self._on_proxy_changed)
            self._settings_window.pairs_changed.connect(self._on_pairs_changed)
            self._settings_window.theme_changed.connect(self._on_theme_changed)
            self._settings_window.data_source_changed.connect(self._on_data_source_changed)
            self._settings_window.display_changed.connect(self._on_display_changed)
            self._settings_window.auto_scroll_changed.connect(self._on_auto_scroll_changed)
            self._settings_window.display_limit_changed.connect(self._on_display_limit_changed)
            self._settings_window.minimalist_view_changed.connect(self._on_minimalist_view_changed)
            self._settings_window.price_change_basis_changed.connect(self._on_data_source_changed)
            self._settings_window.show()
        else:
            self._settings_window.raise_()

    def _on_page_changed(self, page: int):
        """Handle page change."""
        self._update_cards_display()

    def _on_ticker_update(self, pair: str, state: object):
        if pair in self._cards:
            self._cards[pair].update_state(state)

    def _on_connection_status(self, connected: bool, message: str):
        logger.debug(f"Connection status: {connected}, {message}")

    def _on_connection_state_changed(self, state: str, message: str, retry_count: int):
        for card in self._cards.values():
            card.set_connection_state(state)

    def _on_proxy_changed(self):
        self._market_controller.set_proxy()

    def _on_pairs_changed(self):
        self._load_pairs()

    def _on_theme_changed(self):
        pass

    def _on_display_changed(self):
        for card in self._cards.values():
            card.refresh_style()

    def _on_display_limit_changed(self, limit: int):
        self._load_pairs()
        self._view_manager.adjust_window_height(limit)

    def _on_minimalist_view_changed(self, enabled: bool):
        self._settings_manager.update_minimalist_view(enabled)
        self._view_manager.reset_state()
        self._view_manager.adjust_window_height()
        self._update_cards_display()

    def _on_auto_scroll_changed(self, enabled: bool, interval: int):
        self._pagination_manager.update_auto_scroll_settings(enabled, interval)

    def _on_data_source_changed(self):
        self._market_controller.set_data_source()

    def _on_data_source_changed_complete(self):
        pass

    def _toggle_edit_mode(self):
        if self._edit_mode:
            self._edit_mode = False
            for card in self._cards.values():
                card.set_edit_mode(False)
        else:
            data_source = self._settings_manager.settings.data_source
            pair = AddPairDialog.get_new_pair(data_source, self)
            if pair:
                self._add_pair(pair)

    def _add_pair(self, pair: str):
        if self._settings_manager.add_pair(pair):
            self._load_pairs()

    def _remove_pair(self, pair: str):
        if self._settings_manager.remove_pair(pair):
            if pair in self._cards:
                self._cards[pair].deleteLater()
                del self._cards[pair]
            self._market_controller.clear_pair_data(pair)
            self._load_pairs()

    def _open_pair_in_browser(self, pair: str):
        source = self._settings_manager.settings.data_source
        lang = self._settings_manager.settings.language
        if source.lower() == "binance":
            formatted_pair = pair.replace("-", "_").upper()
            locale_prefix = "zh-CN" if lang == "zh_CN" else "en"
            url = f"https://www.binance.com/{locale_prefix}/trade/{formatted_pair}"
        else:
            formatted_pair = pair.lower()
            url_prefix = "zh-hans/" if lang == "zh_CN" else ""
            url = f"https://www.okx.com/{url_prefix}trade-spot/{formatted_pair}"
        webbrowser.open(url)

    def _on_add_alert_requested(self, pair: str):
        current_price = self._market_controller.get_current_price(pair)
        alert = AlertDialog.create_alert(
            parent=self,
            pair=pair,
            current_price=current_price,
            available_pairs=self._settings_manager.settings.crypto_pairs,
        )
        if alert:
            self._settings_manager.add_alert(alert)

    def _on_view_alerts_requested(self, pair: str):
        dialog = AlertListDialog(pair, parent=self)
        dialog.exec()

    def _toggle_always_on_top(self, pinned: bool):
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
        pos = self.pos()
        self._settings_manager.settings.window_x = pos.x()
        self._settings_manager.settings.window_y = pos.y()
        self._settings_manager.save()
        if self._market_controller:
            self._market_controller.stop()
        QApplication.quit()

    # Events delegated to Managers/Behaviors
    def wheelEvent(self, event):
        if self._pagination_manager.handle_wheel_event(event):
            self._update_cards_display()
        super().wheelEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        self._window_behavior.mouse_press_event(event)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        self._window_behavior.mouse_move_event(event)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._window_behavior.mouse_release_event(event)
        super().mouseReleaseEvent(event)

    def enterEvent(self, event):
        self._view_manager.handle_enter_event()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._view_manager.handle_leave_event()
        super().leaveEvent(event)
