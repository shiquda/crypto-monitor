"""
Pagination widget for navigating between pages.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget


class Pagination(QWidget):
    """Pagination control widget."""

    page_changed = pyqtSignal(int)  # Emits new page number (1-indexed)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._current_page = 1
        self._total_pages = 1
        self._setup_ui()

    def _setup_ui(self):
        """Setup pagination UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.setSpacing(10)

        layout.addStretch()

        # Previous button
        self.prev_btn = QPushButton("◀")
        self.prev_btn.setObjectName("pageButton")
        self.prev_btn.setFixedSize(24, 24)
        self.prev_btn.clicked.connect(self._go_prev)
        self.prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.prev_btn)

        # Page info
        self.page_label = QLabel("1 / 1")
        self.page_label.setObjectName("pageLabel")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_label.setMinimumWidth(50)
        layout.addWidget(self.page_label)

        # Next button
        self.next_btn = QPushButton("▶")
        self.next_btn.setObjectName("pageButton")
        self.next_btn.setFixedSize(24, 24)
        self.next_btn.clicked.connect(self._go_next)
        self.next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.next_btn)

        layout.addStretch()

        # Apply theme-aware styles
        from config.settings import get_settings_manager

        theme_mode = get_settings_manager().settings.theme_mode

        if theme_mode == "dark":
            style = """
                QPushButton#pageButton {
                    background: transparent;
                    border: 1px solid #555555;
                    border-radius: 4px;
                    color: #EEEEEE;
                    font-size: 12px;
                }
                QPushButton#pageButton:hover {
                    background: rgba(255, 255, 255, 0.1);
                    border-color: #888888;
                }
                QPushButton#pageButton:disabled {
                    color: #555555;
                    border-color: #444444;
                }
                QLabel#pageLabel {
                    color: #EEEEEE;
                    font-size: 12px;
                }
            """
        else:
            style = """
                QPushButton#pageButton {
                    background: transparent;
                    border: 1px solid #CCCCCC;
                    border-radius: 4px;
                    color: #333333;
                    font-size: 12px;
                }
                QPushButton#pageButton:hover {
                    background: rgba(0, 0, 0, 0.05);
                    border-color: #999999;
                }
                QPushButton#pageButton:disabled {
                    color: #CCCCCC;
                    border-color: #E0E0E0;
                }
                QLabel#pageLabel {
                    color: #333333;
                    font-size: 12px;
                }
            """
        self.setStyleSheet(style)
        self._update_ui()

    def _go_prev(self):
        """Go to previous page."""
        if self._current_page > 1:
            self._current_page -= 1
            self._update_ui()
            self.page_changed.emit(self._current_page)

    def _go_next(self):
        """Go to next page."""
        if self._current_page < self._total_pages:
            self._current_page += 1
            self._update_ui()
            self.page_changed.emit(self._current_page)

    def _update_ui(self):
        """Update UI state."""
        self.page_label.setText(f"{self._current_page} / {self._total_pages}")
        self.prev_btn.setEnabled(self._current_page > 1)
        self.next_btn.setEnabled(self._current_page < self._total_pages)

    def set_total_pages(self, total: int):
        """Set total number of pages."""
        self._total_pages = max(1, total)
        if self._current_page > self._total_pages:
            self._current_page = self._total_pages
        self._update_ui()

    def set_current_page(self, page: int):
        """Set current page."""
        self._current_page = max(1, min(page, self._total_pages))
        self._update_ui()

    def current_page(self) -> int:
        """Get current page number."""
        return self._current_page

    def total_pages(self) -> int:
        """Get total pages."""
        return self._total_pages
