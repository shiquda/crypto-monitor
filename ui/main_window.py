"""
Main application window using Fluent Design.
"""

import webbrowser
from typing import Optional, Dict
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QScrollArea,
    QApplication, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, QPoint, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QIcon, QMouseEvent, QWheelEvent
from qfluentwidgets import setTheme, Theme

from ui.widgets.toolbar import Toolbar
from ui.widgets.crypto_card import CryptoCard
from ui.widgets.pagination import Pagination
from ui.widgets.compact_controls import CompactControls
from ui.settings_window import SettingsWindow

from core.okx_client import OkxClientManager
from core.price_tracker import PriceTracker
from config.settings import get_settings_manager


class MainWindow(QMainWindow):
    """Main application window with Fluent Design components."""

    ITEMS_PER_PAGE = 3
    COMPACT_WIDTH = 160
    COMPACT_HEIGHT_MINIMAL = 85   # Compact mode without toolbar
    COMPACT_HEIGHT_EXPANDED = 170  # Compact mode with toolbar

    def __init__(self):
        super().__init__()

        self._drag_pos: Optional[QPoint] = None
        self._settings_window: Optional[SettingsWindow] = None
        self._cards: Dict[str, CryptoCard] = {}
        self._edit_mode = False

        # Compact mode state
        self._compact_mode = False
        self._current_compact_index = 0
        self._auto_scroll_timer = QTimer(self)
        self._auto_scroll_timer.timeout.connect(self._auto_scroll_next)
        self._fade_animation = None

        # Core components
        self._settings_manager = get_settings_manager()
        self._okx_client = OkxClientManager(self)
        self._price_tracker = PriceTracker()

        # Apply theme based on settings
        theme_mode = self._settings_manager.settings.theme_mode
        setTheme(Theme.DARK if theme_mode == "dark" else Theme.LIGHT)

        self._setup_ui()
        self._connect_signals()
        self._load_pairs()

        # Apply initial mode based on settings
        if self._settings_manager.settings.compact_mode:
            self._switch_to_compact_mode()
        else:
            self._switch_to_normal_mode()

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
        self.setWindowTitle("Crypto Monitor")

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

        # Compact controls (hidden by default)
        self.compact_controls = CompactControls()
        self.compact_controls.setVisible(False)
        layout.addWidget(self.compact_controls)

    def _connect_signals(self):
        """Connect signals to slots."""
        # Toolbar signals
        self.toolbar.settings_clicked.connect(self._open_settings)
        self.toolbar.pin_clicked.connect(self._toggle_always_on_top)
        self.toolbar.close_clicked.connect(self._close_app)
        self.toolbar.compact_mode_toggled.connect(self._on_toolbar_mode_toggled)

        # Pagination
        self.pagination.page_changed.connect(self._on_page_changed)

        # Compact controls
        self.compact_controls.prev_clicked.connect(self._show_prev_pair)
        self.compact_controls.next_clicked.connect(self._show_next_pair)

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
            self._settings_window.theme_changed.connect(self._on_theme_changed)
            self._settings_window.compact_mode_changed.connect(self._on_compact_mode_changed)
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

    def _on_theme_changed(self):
        """Handle theme change."""
        # Theme change requires application restart
        # This is just a placeholder for future enhancements
        pass

    def _on_compact_mode_changed(self):
        """Handle compact mode change from settings."""
        if self._settings_manager.settings.compact_mode:
            self._switch_to_compact_mode()
        else:
            self._switch_to_normal_mode()

    def _on_toolbar_mode_toggled(self, to_compact: bool):
        """Handle mode toggle from toolbar button."""
        # Update settings
        self._settings_manager.settings.compact_mode = to_compact
        self._settings_manager.save()

        # Switch mode
        if to_compact:
            self._switch_to_compact_mode()
        else:
            self._switch_to_normal_mode()

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

    # Compact mode methods
    def _switch_to_compact_mode(self):
        """Switch to compact mode."""
        self._compact_mode = True

        # Save current window position (normal mode)
        if not self._settings_manager.settings.compact_mode:
            pos = self.pos()
            self._settings_manager.settings.window_x = pos.x()
            self._settings_manager.settings.window_y = pos.y()

        # Hide toolbar and pagination by default (minimal state)
        self.toolbar.hide()
        self.toolbar.set_compact_mode(True)
        self.pagination.hide()

        # Hide compact controls initially
        self.compact_controls.hide()

        # Adjust window size to minimal
        self.setFixedSize(self.COMPACT_WIDTH, self.COMPACT_HEIGHT_MINIMAL)

        # Move to compact mode position
        self.move(
            self._settings_manager.settings.compact_window_x,
            self._settings_manager.settings.compact_window_y
        )

        # Clear all cards from layout first
        while self.cards_layout.count() > 1:  # Keep the stretch
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        # Display first pair
        self._current_compact_index = 0
        self._update_compact_display()

        # Start auto-scroll if enabled
        self._start_auto_scroll()

    def _switch_to_normal_mode(self):
        """Switch to normal mode."""
        self._compact_mode = False

        # Save current window position (compact mode)
        if self._settings_manager.settings.compact_mode:
            pos = self.pos()
            self._settings_manager.settings.compact_window_x = pos.x()
            self._settings_manager.settings.compact_window_y = pos.y()

        # Stop auto-scroll
        self._stop_auto_scroll()

        # Hide compact controls
        self.compact_controls.hide()

        # Show components
        self.toolbar.show()
        self.toolbar.set_compact_mode(False)
        if self.pagination.total_pages() > 1:
            self.pagination.show()

        # Adjust window size
        self.setFixedSize(160, 320)

        # Move to normal mode position
        self.move(
            self._settings_manager.settings.window_x,
            self._settings_manager.settings.window_y
        )

        # Update cards display
        self._update_cards_display()

    def _update_compact_display(self):
        """Update the displayed card in compact mode (no animation)."""
        pairs = self._settings_manager.settings.crypto_pairs
        if not pairs:
            return

        # Ensure index is valid
        self._current_compact_index = max(0, min(self._current_compact_index, len(pairs) - 1))

        # Clear existing cards from layout
        while self.cards_layout.count() > 1:  # Keep the stretch
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        # Show only the current pair
        pair = pairs[self._current_compact_index]
        if pair not in self._cards:
            card = CryptoCard(pair)
            card.double_clicked.connect(self._on_card_double_click)
            self._cards[pair] = card

        card = self._cards[pair]
        self.cards_layout.insertWidget(0, card)

    def _update_compact_display_with_animation(self):
        """Update the displayed card in compact mode with fade animation."""
        pairs = self._settings_manager.settings.crypto_pairs
        if not pairs:
            return

        # Ensure index is valid
        self._current_compact_index = max(0, min(self._current_compact_index, len(pairs) - 1))

        # Clear existing cards from layout
        while self.cards_layout.count() > 1:  # Keep the stretch
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        # Show only the current pair
        pair = pairs[self._current_compact_index]
        if pair not in self._cards:
            card = CryptoCard(pair)
            card.double_clicked.connect(self._on_card_double_click)
            self._cards[pair] = card

        card = self._cards[pair]
        self.cards_layout.insertWidget(0, card)

        # Apply fade animation
        self._apply_fade_animation(card)

    def _apply_fade_animation(self, widget):
        """Apply fade in/out animation to a widget."""
        # Create opacity effect
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)

        # Create fade out animation
        self._fade_animation = QPropertyAnimation(effect, b"opacity")
        self._fade_animation.setDuration(150)
        self._fade_animation.setStartValue(1.0)
        self._fade_animation.setEndValue(0.0)
        self._fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Create fade in animation
        fade_in = QPropertyAnimation(effect, b"opacity")
        fade_in.setDuration(150)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Chain animations: fade out -> fade in
        self._fade_animation.finished.connect(lambda: fade_in.start())
        fade_in.finished.connect(lambda: widget.setGraphicsEffect(None))

        # Start fade out
        self._fade_animation.start()

    def _show_prev_pair(self):
        """Show previous pair in compact mode with fade animation."""
        pairs = self._settings_manager.settings.crypto_pairs
        if not pairs:
            return

        self._current_compact_index = (self._current_compact_index - 1) % len(pairs)
        self._update_compact_display_with_animation()

    def _show_next_pair(self):
        """Show next pair in compact mode with fade animation."""
        pairs = self._settings_manager.settings.crypto_pairs
        if not pairs:
            return

        self._current_compact_index = (self._current_compact_index + 1) % len(pairs)
        self._update_compact_display_with_animation()

    def _auto_scroll_next(self):
        """Auto-scroll to next pair."""
        self._show_next_pair()

    def _start_auto_scroll(self):
        """Start auto-scroll timer."""
        if self._settings_manager.settings.compact_auto_scroll:
            interval = self._settings_manager.settings.compact_scroll_interval * 1000
            self._auto_scroll_timer.start(interval)

    def _stop_auto_scroll(self):
        """Stop auto-scroll timer."""
        self._auto_scroll_timer.stop()

    def wheelEvent(self, event: QWheelEvent):
        """Handle mouse wheel for pair switching in compact mode."""
        if self._compact_mode:
            delta = event.angleDelta().y()
            if delta > 0:
                self._show_prev_pair()
            elif delta < 0:
                self._show_next_pair()
            # Accept the event to prevent it from propagating to parent widgets
            event.accept()
            return
        super().wheelEvent(event)

    def enterEvent(self, event):
        """Pause auto-scroll and show controls when mouse enters window."""
        if self._compact_mode:
            # Pause auto-scroll
            self._stop_auto_scroll()
            # Expand to show toolbar and controls
            self.setFixedSize(self.COMPACT_WIDTH, self.COMPACT_HEIGHT_EXPANDED)
            self.toolbar.show()
            self.compact_controls.show()
            self.compact_controls.show_controls()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Resume auto-scroll and hide controls when mouse leaves window."""
        if self._compact_mode:
            # Resume auto-scroll
            self._start_auto_scroll()
            # Collapse to minimal state
            self.toolbar.hide()
            self.compact_controls.hide()
            self.compact_controls.hide_controls()
            self.setFixedSize(self.COMPACT_WIDTH, self.COMPACT_HEIGHT_MINIMAL)
        super().leaveEvent(event)
