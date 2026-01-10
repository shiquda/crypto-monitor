"""
Pagination management logic.
"""

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from config.settings import SettingsManager
from ui.widgets.pagination import Pagination


class PaginationManager:
    """Manages pagination logic and card display."""

    def __init__(
        self,
        parent_widget: QWidget,
        pagination_widget: Pagination,
        cards_layout: QVBoxLayout,
        settings_manager: SettingsManager,
    ):
        self._parent = parent_widget
        self._pagination = pagination_widget
        self._cards_layout = cards_layout
        self._settings_manager = settings_manager

        self._auto_scroll_timer = QTimer(parent_widget)
        self._auto_scroll_timer.timeout.connect(self._on_auto_scroll_timer)

        # Signal connection
        self._pagination.page_changed.connect(self._on_page_changed)

    def setup_auto_scroll(self):
        """Setup or update auto scroll based on settings."""
        if self._settings_manager.settings.auto_scroll:
            interval_ms = self._settings_manager.settings.scroll_interval * 1000
            self._auto_scroll_timer.start(interval_ms)
        else:
            self._auto_scroll_timer.stop()

    def update_auto_scroll_settings(self, enabled: bool, interval: int):
        """Handle auto scroll settings change."""
        if enabled:
            self._auto_scroll_timer.start(interval * 1000)
        else:
            self._auto_scroll_timer.stop()

    def calculate_total_pages(self, total_items: int) -> int:
        """Calculate total pages."""
        items_per_page = self._settings_manager.settings.display_limit
        return max(1, (total_items + items_per_page - 1) // items_per_page)

    def get_visible_slice(self, items: list) -> list:
        """Get the slice of items for the current page."""
        current_page = self._pagination.current_page()
        items_per_page = self._settings_manager.settings.display_limit

        start = (current_page - 1) * items_per_page
        end = start + items_per_page
        return items[start:end]

    def refresh_pagination_state(self, total_items: int):
        """Update pagination widget visibility and total pages."""
        total_pages = self.calculate_total_pages(total_items)
        self._pagination.set_total_pages(total_pages)
        self._pagination.setVisible(total_pages > 1)

    def handle_wheel_event(self, event) -> bool:
        """
        Handle mouse wheel for page switching.
        Returns True if event was handled.
        """
        delta = event.angleDelta().y()
        if delta != 0:
            current_page = self._pagination.current_page()
            total_pages = self._pagination.total_pages()

            if delta > 0:  # Scroll up -> Prev page
                new_page = max(1, current_page - 1)
            else:  # Scroll down -> Next page
                new_page = min(total_pages, current_page + 1)

            if new_page != current_page:
                self._pagination.set_current_page(new_page)
                # The caller should handle the update callback
                return True
        return False

    def _on_page_changed(self, page: int):
        """Handle page change internally if needed, mostly proxies signal."""
        # This signal is usually connected to the main window's update_cards
        # But we can also emit a custom signal if we make this class a QObject
        pass

    def _on_auto_scroll_timer(self):
        """Handle auto scroll timer timeout."""
        if not self._parent.isVisible():
            return

        next_page = self._pagination.current_page() + 1
        if next_page > self._pagination.total_pages():
            next_page = 1

        self._pagination.set_current_page(next_page)
        # We need to trigger the update. Ideally, we emit a signal.
        # For now, let's assume the main window connects to pagination.page_changed
        # But wait, set_current_page usually emits page_changed?
        # Yes, if implemented correctly in Pagination widget.
