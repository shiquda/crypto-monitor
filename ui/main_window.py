"""
Main application window using Fluent Design.
"""

import webbrowser
import logging
from typing import Optional, Dict
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QScrollArea,
    QApplication, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, QPoint, QTimer, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import QIcon, QMouseEvent, QCursor
from qfluentwidgets import setTheme, Theme

from ui.widgets.toolbar import Toolbar
from ui.widgets.crypto_card import CryptoCard
from ui.widgets.pagination import Pagination
from ui.widgets.add_pair_dialog import AddPairDialog
from ui.widgets.alert_dialog import AlertDialog
from ui.widgets.alert_list_dialog import AlertListDialog
from ui.settings_window import SettingsWindow

from core.i18n import _
from core.market_data_controller import MarketDataController
from config.settings import get_settings_manager



logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window with Fluent Design components."""

    # ITEMS_PER_PAGE = 3  <-- Removed constant

    def __init__(self):
        super().__init__()

        self._drag_pos: Optional[QPoint] = None
        self._settings_window: Optional[SettingsWindow] = None
        self._cards: Dict[str, CryptoCard] = {}
        self._edit_mode = False

        # Core components
        self._settings_manager = get_settings_manager()
        self._market_controller = MarketDataController(self)
        
        # Minimalist view state (must be initialized before _setup_ui)
        self._minimalist_collapsed = False
        self._is_adjusting_height = False
        self._last_state_change_time = 0

        # Apply theme based on settings
        theme_mode = self._settings_manager.settings.theme_mode
        setTheme(Theme.DARK if theme_mode == "dark" else Theme.LIGHT)

        self._setup_ui()
        self._connect_signals()
        
        # Debounce timer for minimalist view collapse
        self._collapse_timer = QTimer(self)
        self._collapse_timer.setSingleShot(True)
        self._collapse_timer.timeout.connect(self._check_and_collapse)

        # Polling timer for hover detection (more stable than enter/leave during resize)
        self._hover_polling_timer = QTimer(self)
        self._hover_polling_timer.setInterval(200)
        self._hover_polling_timer.timeout.connect(self._poll_minimalist_hover)
        self._hover_polling_timer.start()
        
        # Auto scroll timer
        self._auto_scroll_timer = QTimer(self)
        self._auto_scroll_timer.timeout.connect(self._on_auto_scroll_timer)
        self._setup_auto_scroll()
        
        # Start data controller
        self._load_pairs()
        self._market_controller.start()


    def _setup_ui(self):
        """Setup the main window UI with Fluent Design components."""
        # ... (flags and attributes)
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
            self._settings_manager.settings.window_y
        )

        # ... (rest of UI setup)
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

        # Initialize animations before first resize
        self._setup_animations()

        # Initial size adjustment - use timer to allow layout to initialize
        QTimer.singleShot(100, self._adjust_window_height)

    def _setup_animations(self):
        """Setup animations for minimalist view mode."""
        # Opacity effect for toolbar
        self.toolbar_opacity = QGraphicsOpacityEffect(self.toolbar)
        self.toolbar_opacity.setOpacity(1.0)
        self.toolbar.setGraphicsEffect(self.toolbar_opacity)
        
        self.toolbar_anim = QPropertyAnimation(self.toolbar_opacity, b"opacity")
        self.toolbar_anim.setDuration(250)
        self.toolbar_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        # Opacity effect for pagination
        self.pagination_opacity = QGraphicsOpacityEffect(self.pagination)
        self.pagination_opacity.setOpacity(1.0)
        self.pagination.setGraphicsEffect(self.pagination_opacity)
        
        self.pagination_anim = QPropertyAnimation(self.pagination_opacity, b"opacity")
        self.pagination_anim.setDuration(250)
        self.pagination_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        # Window height animation
        # We animate the 'geometry' of the window to change height
        self.window_anim = QPropertyAnimation(self, b"geometry")
        self.window_anim.setDuration(250)
        self.window_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        # Initial state
        if self._settings_manager.settings.minimalist_view:
            self.toolbar_opacity.setOpacity(0.0)
            self.pagination_opacity.setOpacity(0.0)
            # We will trigger the first resize in _adjust_window_height

    def _adjust_window_height(self, limit: int = None, collapsed: bool = None):
        """Adjust window height with state locking and precise visibility management."""
        if self._is_adjusting_height:
            return
        
        if limit is None:
            limit = self._settings_manager.settings.display_limit
        
        is_minimalist = self._settings_manager.settings.minimalist_view
        if collapsed is None:
            pos = QCursor.pos()
            collapsed = is_minimalist and not self.geometry().contains(pos)

        # Skip logic with state verification
        if hasattr(self, '_last_collapsed') and self._last_collapsed == collapsed and limit == self._last_limit:
            # If we are expanded, ensure the toolbar hasn't drifted to hidden
            if not collapsed and self.toolbar.isHidden():
                 pass # Continue to fix it
            else:
                 return
        
        self._is_adjusting_height = True
        try:
            self._last_collapsed = collapsed
            self._last_limit = limit

            # Precise dimensions
            # Reverting to explicit calculation as sizeHint is unreliable during rapid layout changes
            CARD_H = 67 # Tighter fit to reduce whitespace
            CARD_SPACING = 8
            content_height = (limit * CARD_H) + (max(0, limit - 1) * CARD_SPACING)
            
            top_margin, bottom_margin = 7, 8
            layout_spacing = 5
            # Corrected actual heights based on widget layout (margin 5+5 + icon 24 = 34)
            toolbar_h, pagination_h = 34, 34
            
            EXPANDED_TOP_GAP = top_margin + toolbar_h + layout_spacing
            EXPANDED_BOTTOM_GAP = layout_spacing + pagination_h + bottom_margin
            COLLAPSED_GAP = 8 # Balanced padding
            
            # Use explicit calculation for reliable alignment
            
            current_geom = self.geometry()
            target_w = 160
            
            if collapsed:
                target_h = content_height + (COLLAPSED_GAP * 2)
                
                # Shifting logic (Stable Cards)
                if not self.toolbar.isHidden():
                    dy = EXPANDED_TOP_GAP - COLLAPSED_GAP
                    new_y = current_geom.y() + dy
                else:
                    new_y = current_geom.y()

                self.toolbar.hide()
                self.pagination.hide()
                self.centralWidget().layout().setContentsMargins(10, COLLAPSED_GAP, 10, COLLAPSED_GAP)
                self.centralWidget().layout().setSpacing(0)
                
                if hasattr(self, 'toolbar_opacity'):
                    self.toolbar_anim.stop()
                    self.toolbar_opacity.setOpacity(0.0)
                if hasattr(self, 'pagination_opacity'):
                    self.pagination_anim.stop()
                    self.pagination_opacity.setOpacity(0.0)
            else:
                target_h = content_height + EXPANDED_TOP_GAP + EXPANDED_BOTTOM_GAP
                
                # Expand upwards
                if self.toolbar.isHidden():
                    dy = EXPANDED_TOP_GAP - COLLAPSED_GAP
                    new_y = current_geom.y() - dy
                else:
                    new_y = current_geom.y()
                    
                # FORCE VISIBILITY: Order matters
                self.toolbar.show()
                self.pagination.show()
                
                # Reset opacity effect IMMEDIATELY before layout updates
                if hasattr(self, 'toolbar_opacity'):
                    self.toolbar_anim.stop()
                    self.toolbar_opacity.setOpacity(1.0)
                if hasattr(self, 'pagination_opacity'):
                    self.pagination_anim.stop()
                    self.pagination_opacity.setOpacity(1.0)

                self.centralWidget().layout().setContentsMargins(10, top_margin, 10, bottom_margin)
                self.centralWidget().layout().setSpacing(layout_spacing)
                
                # Ensure they are at top of stacking order
                self.toolbar.raise_()
                self.pagination.raise_()

            logger.info(f"Setting window state: Collapsed={collapsed}, Limit={limit}, TotalH={target_h}")
            
            # Atomic update of geometry
            if self.height() != int(target_h) or self.y() != int(new_y):
                self.setFixedSize(target_w, int(target_h))
                self.move(current_geom.x(), int(new_y))
                import time
                self._last_state_change_time = time.time()
            
            self.update() # Force repaint
            QApplication.processEvents() # Let internal layout sync
        finally:
            self._is_adjusting_height = False

    def _poll_minimalist_hover(self):
        """Unified poll for minimalist state (highly stable)."""
        if not self._settings_manager.settings.minimalist_view:
            return
        
        if self._is_adjusting_height:
            return

        import time
        # Reduced cooldown for polling transitions
        if time.time() - self._last_state_change_time < 0.2:
            return

        pos = QCursor.pos()
        is_hovering = self.geometry().contains(pos)
        
        if is_hovering and self.toolbar.isHidden():
            # Mouse is inside but window is collapsed -> EXPAND
            self._collapse_timer.stop()
            self._adjust_window_height(collapsed=False)
        elif not is_hovering and not self.toolbar.isHidden():
            # Mouse is outside but window is expanded -> COLLAPSE (with debounce)
            # Use the hysteresis rect for collapse to avoid edge flickering
            hysteresis_rect = self.geometry().adjusted(-5, -5, 5, 5)
            if not hysteresis_rect.contains(pos):
                if not self._collapse_timer.isActive():
                    self._collapse_timer.start(300)

    def _check_and_collapse(self):
        """Final check before collapsing window."""
        if not self._settings_manager.settings.minimalist_view:
            return
            
        pos = QCursor.pos()
        # Use a slightly more aggressive check for final collapse
        if not self.geometry().contains(pos):
             self._adjust_window_height(collapsed=True)
        
    def _on_display_limit_changed(self, limit: int):
        """Handle display limit change."""
        logger.info(f"Display limit changed to {limit}, resizing window...")
        # Reload pairs to refresh pagination
        self._load_pairs()
        # Adjust window size
        self._adjust_window_height(limit)

    def _on_minimalist_view_changed(self, enabled: bool):
        """Handle minimalist view toggle."""
        logger.info(f"Minimalist view changed to {enabled}")
        self._settings_manager.update_minimalist_view(enabled)
        # Clear state to force resize
        if hasattr(self, '_last_collapsed'):
            delattr(self, '_last_collapsed')
        # Trigger immediate adjustment
        self._adjust_window_height()

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
            
            self._settings_window.show()
        else:
            self._settings_window.raise_()

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
        # Market controller signals
        self._market_controller.ticker_updated.connect(self._on_ticker_update)
        self._market_controller.connection_status_changed.connect(self._on_connection_status)
        self._market_controller.connection_state_changed.connect(self._on_connection_state_changed)
        self._market_controller.data_source_changed.connect(self._on_data_source_changed_complete)


    def _load_pairs(self):
        """Load pairs from settings and subscribe."""
        pairs = self._settings_manager.settings.crypto_pairs
        items_per_page = self._settings_manager.settings.display_limit

        # Calculate pagination
        total_pages = max(1, (len(pairs) + items_per_page - 1) // items_per_page)
        self.pagination.set_total_pages(total_pages)
        self.pagination.setVisible(total_pages > 1)

        # Create cards for current page
        self._update_cards_display()

        # Subscribe to all pairs
        # Subscribe via controller
        self._market_controller.reload_pairs()


    def _update_cards_display(self):
        """Update the displayed cards based on current page."""
        pairs = self._settings_manager.settings.crypto_pairs
        current_page = self.pagination.current_page()
        items_per_page = self._settings_manager.settings.display_limit

        # Calculate slice for current page
        start = (current_page - 1) * items_per_page
        end = start + items_per_page
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
            
        # Ensure window height is correct for newly added cards
        self._adjust_window_height()

    def _on_page_changed(self, page: int):
        """Handle page change."""
        self._update_cards_display()

    def _on_ticker_update(self, pair: str, state: object):
        """Handle ticker update from controller."""
        # Update card if visible
        if pair in self._cards:
            self._cards[pair].update_state(state)



    def _on_connection_status(self, connected: bool, message: str):
        """Handle connection status change."""
        logger.debug(f"Connection status: {connected}, {message}")

    def _on_connection_state_changed(self, state: str, message: str, retry_count: int):
        """
        Handle detailed connection state change.
        Updates UI to reflect connecting/reconnecting status.
        """
        logger.debug(f"Connection state: {state} ({message}) - Retry: {retry_count}")
        
        # Update all cards with connection state
        for card in self._cards.values():
            card.set_connection_state(state)

    def _on_proxy_changed(self):
        """Handle proxy configuration change."""
        self._market_controller.set_proxy()


    def _on_pairs_changed(self):
        """Handle crypto pairs change."""
        # Reload pairs and resubscribe
        self._load_pairs()

    def _on_theme_changed(self):
        """Handle theme change."""
        # Theme change requires application restart
        pass

    def _on_display_changed(self):
        """Handle display settings change (dynamic background)."""
        # Force update all cards
        for card in self._cards.values():
            card.refresh_style()

    def _setup_auto_scroll(self):
        """Setup or update auto scroll based on settings."""
        if self._settings_manager.settings.auto_scroll:
            interval_ms = self._settings_manager.settings.scroll_interval * 1000
            self._auto_scroll_timer.start(interval_ms)
        else:
            self._auto_scroll_timer.stop()

    def _on_auto_scroll_changed(self, enabled: bool, interval: int):
        """Handle auto scroll settings change."""
        if enabled:
            self._auto_scroll_timer.start(interval * 1000)
        else:
            self._auto_scroll_timer.stop()

    def _on_minimalist_view_changed(self):
        """Handle minimalist view mode change."""
        enabled = self._settings_manager.settings.minimalist_view
        if enabled:
            # If not hovered, hide immediately
            if not self.underMouse():
                self.toolbar_opacity.setOpacity(0.0)
                self.pagination_opacity.setOpacity(0.0)
        else:
            # Show everything
            self.toolbar_opacity.setOpacity(1.0)
            self.pagination_opacity.setOpacity(1.0)
            
        self._adjust_window_height()
        # Update cards
        self._update_cards_display()

    def _on_auto_scroll_timer(self):
        """Handle auto scroll timer timeout."""
        if not self.isVisible():
            return
            
        next_page = self.pagination.current_page() + 1
        if next_page > self.pagination.total_pages():
            next_page = 1
        
        self.pagination.set_current_page(next_page)
        self._update_cards_display()

    def _on_data_source_changed(self):
        """Handle data source change request."""
        # This triggers re-initialization in the controller
        self._market_controller.set_data_source()
        
    def _on_data_source_changed_complete(self):
        """Handle completion of data source change."""
        # Auto scroll timer reset if needed, or just ensure UI is consistent
        # In the original code, it was recreating the timer.
        # But here the timer is owned by MainWindow, so we don't strictly need to recreate it unless we want to reset it.
        # We can just ensure pairs are reloaded (which set_data_source does)
        pass


    def _toggle_edit_mode(self):
        """Toggle edit mode (add/remove pairs)."""
        if self._edit_mode:
            # Exit edit mode
            self._edit_mode = False
            for card in self._cards.values():
                card.set_edit_mode(False)
        else:
            # Show add pair dialog with current data source
            data_source = self._settings_manager.settings.data_source
            pair = AddPairDialog.get_new_pair(data_source, self)
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
            self._market_controller.clear_pair_data(pair)
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
        current_price = self._market_controller.get_current_price(pair)

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

        # Stop market controller
        if self._market_controller:
            self._market_controller.stop()


        # Close application
        QApplication.quit()

    # Window dragging
    def wheelEvent(self, event):
        """Handle mouse wheel for page switching."""
        delta = event.angleDelta().y()
        if delta != 0:
            current_page = self.pagination.current_page()
            total_pages = self.pagination.total_pages()
            
            if delta > 0: # Scroll up -> Prev page
                new_page = max(1, current_page - 1)
            else: # Scroll down -> Next page
                new_page = min(total_pages, current_page + 1)
                
            if new_page != current_page:
                self.pagination.set_current_page(new_page)
                self._update_cards_display()
                
        super().wheelEvent(event)

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

    def enterEvent(self, event):
        """Handle mouse enter for minimalist view."""
        if self._settings_manager.settings.minimalist_view:
            self._collapse_timer.stop()
            if self.toolbar.isHidden():
                # Immediate expansion on enter event for better responsiveness
                self._adjust_window_height(collapsed=False)
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Handle mouse leave for minimalist view."""
        if self._settings_manager.settings.minimalist_view:
            # We rely on the polling timer and _check_and_collapse for stable transitions.
            # But we can start the fade out here for immediate visual feedback.
            pos = QCursor.pos()
            if not self.geometry().contains(pos):
                if not self._collapse_timer.isActive():
                    self._collapse_timer.start(300)
                
                if not self.toolbar.isHidden():
                    self.toolbar_anim.stop()
                    self.toolbar_anim.setEndValue(0.0)
                    self.toolbar_anim.start()
                    self.pagination_anim.stop()
                    self.pagination_anim.setEndValue(0.0)
                    self.pagination_anim.start()
        super().leaveEvent(event)

