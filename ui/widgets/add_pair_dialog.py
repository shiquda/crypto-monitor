"""
Dialog for adding a new crypto pair using Fluent Design with search autocomplete.
"""

import re
from typing import Optional, List
from PyQt6.QtWidgets import (
    QVBoxLayout, QWidget, QLabel, QListWidget, 
    QListWidgetItem, QHBoxLayout, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from qfluentwidgets import Dialog, SearchLineEdit, ProgressRing, isDarkTheme

from core.i18n import _
from core.symbol_search import get_symbol_search_service, SymbolInfo


class AddPairDialog(Dialog):
    """Fluent Design dialog for adding a new cryptocurrency trading pair with search."""

    def __init__(self, data_source: str = "OKX", parent: Optional[QWidget] = None):
        super().__init__(
            title=_("Add Trading Pair"),
            content="",
            parent=parent
        )
        self._pair: Optional[str] = None
        self._data_source = data_source
        self._search_service = get_symbol_search_service()
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._do_search)
        self._updating_from_selection = False  # Flag to prevent search loop
        
        self._setup_content()

        # Set dialog size - taller to accommodate results list
        self.setFixedSize(450, 400)

        # Make sure it's a top-level window
        flags = Qt.WindowType.Dialog | Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowCloseButtonHint
        if parent and (parent.windowFlags() & Qt.WindowType.WindowStaysOnTopHint):
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

        self._drag_pos = None
        
        # Connect to search service signals
        self._search_service.symbols_loaded.connect(self._on_symbols_loaded)
        self._search_service.loading_started.connect(self._on_loading_started)
        self._search_service.loading_error.connect(self._on_loading_error)
        
        # Start loading symbols
        self._search_service.load_symbols(self._data_source)

    def _setup_content(self):
        """Setup dialog content with search input and results list."""
        content_layout = QVBoxLayout()
        content_layout.setSpacing(12)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # Label
        label = QLabel(_("Search trading pairs:"))
        label.setStyleSheet("font-size: 14px;")
        content_layout.addWidget(label)

        # Search input with loading indicator
        search_row = QHBoxLayout()
        search_row.setSpacing(8)
        
        self.search_input = SearchLineEdit()
        self.search_input.setPlaceholderText(_("Enter symbol (e.g., BTC, ETH-USDT)..."))
        self.search_input.setFixedHeight(36)
        self.search_input.textChanged.connect(self._on_search_text_changed)
        self.search_input.returnPressed.connect(self._on_return_pressed)
        search_row.addWidget(self.search_input)
        
        # Loading spinner
        self.loading_spinner = ProgressRing()
        self.loading_spinner.setFixedSize(24, 24)
        self.loading_spinner.setVisible(False)
        search_row.addWidget(self.loading_spinner)
        
        content_layout.addLayout(search_row)

        # Results list
        self.results_list = QListWidget()
        self.results_list.setFixedHeight(200)
        self.results_list.itemClicked.connect(self._on_item_clicked)
        self.results_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self._style_results_list()
        content_layout.addWidget(self.results_list)

        # Status label (for messages like "Loading..." or "No results")
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #888; font-size: 12px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(self.status_label)

        # Error/info label
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #D13438; font-size: 12px;")
        self.error_label.setVisible(False)
        content_layout.addWidget(self.error_label)
        
        # Add stretch to push buttons down
        content_layout.addStretch()

        # Add the content layout to the dialog's text layout
        self.textLayout.addLayout(content_layout)

        # Customize the built-in buttons
        self.yesButton.setText(_("Add"))
        self.yesButton.setEnabled(False)
        self.cancelButton.setText(_("Cancel"))

        # Connect the built-in yes button
        self.yesButton.clicked.connect(self._on_confirm)

    def _style_results_list(self):
        """Apply styles to the results list."""
        is_dark = isDarkTheme()
        
        bg_color = "#2d2d2d" if is_dark else "#ffffff"
        text_color = "#ffffff" if is_dark else "#1a1a1a"
        hover_bg = "#3d3d3d" if is_dark else "#f0f0f0"
        selected_bg = "#0078d4" if is_dark else "#0078d4"
        border_color = "#404040" if is_dark else "#e0e0e0"
        
        self.results_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 6px;
                padding: 4px;
                outline: none;
            }}
            QListWidget::item {{
                color: {text_color};
                padding: 8px 12px;
                border-radius: 4px;
                margin: 2px 0;
            }}
            QListWidget::item:hover {{
                background-color: {hover_bg};
            }}
            QListWidget::item:selected {{
                background-color: {selected_bg};
                color: white;
            }}
        """)

    def _on_loading_started(self):
        """Handle loading started."""
        self.loading_spinner.setVisible(True)
        self.status_label.setText(_("Loading symbols..."))
        self.results_list.clear()

    def _on_symbols_loaded(self, symbols: List[SymbolInfo]):
        """Handle symbols loaded."""
        self.loading_spinner.setVisible(False)
        self.status_label.setText(
            _("{count} symbols available").format(count=len(symbols))
        )
        # Trigger initial search with current text
        self._do_search()

    def _on_loading_error(self, error: str):
        """Handle loading error."""
        self.loading_spinner.setVisible(False)
        self.status_label.setText(_("Failed to load symbols"))
        self.error_label.setText(error)
        self.error_label.setVisible(True)

    def _on_search_text_changed(self, text: str):
        """Handle search text change with debounce."""
        # Skip if this change was triggered programmatically (from selection)
        if self._updating_from_selection:
            return
        
        # Clear current selection
        self._pair = None
        self.yesButton.setEnabled(False)
        self.error_label.setVisible(False)
        
        # Debounce search - wait 200ms after typing stops
        self._search_timer.stop()
        self._search_timer.start(200)

    def _do_search(self):
        """Perform the actual search."""
        query = self.search_input.text().strip()
        
        # Search for matching symbols
        results = self._search_service.search(query, limit=50)
        
        self.results_list.clear()
        
        if not results:
            if query:
                self.status_label.setText(_("No matching pairs found"))
                # Allow manual input if format is valid
                if self._is_valid_format(query):
                    self._pair = query.upper()
                    self.yesButton.setEnabled(True)
                    self.status_label.setText(
                        _("No match found. Add '{pair}' anyway?").format(pair=self._pair)
                    )
            else:
                self.status_label.setText(_("Enter a symbol to search"))
            return
        
        # Populate results
        for symbol_info in results:
            item = QListWidgetItem(symbol_info.symbol)
            item.setData(Qt.ItemDataRole.UserRole, symbol_info)
            self.results_list.addItem(item)
        
        self.status_label.setText(
            _("Found {count} matches").format(count=len(results))
        )

    def _is_valid_format(self, text: str) -> bool:
        """Check if text is a valid trading pair format."""
        text = text.strip().upper()
        # Pattern: SYMBOL-SYMBOL (e.g., BTC-USDT)
        pattern = r'^[A-Z0-9]+-[A-Z0-9]+$'
        return bool(re.match(pattern, text))

    def _on_item_clicked(self, item: QListWidgetItem):
        """Handle item click - select the pair."""
        symbol_info: SymbolInfo = item.data(Qt.ItemDataRole.UserRole)
        if symbol_info:
            self._pair = symbol_info.symbol
            # Block signals to prevent triggering a new search
            self._updating_from_selection = True
            self.search_input.setText(symbol_info.symbol)
            self._updating_from_selection = False
            self.yesButton.setEnabled(True)
            self.error_label.setVisible(False)

    def _on_item_double_clicked(self, item: QListWidgetItem):
        """Handle item double-click - select and confirm."""
        self._on_item_clicked(item)
        self._on_confirm()

    def _on_return_pressed(self):
        """Handle Enter key press."""
        # If there's a selected item in the list, use it
        selected_items = self.results_list.selectedItems()
        if selected_items:
            self._on_item_clicked(selected_items[0])
            self._on_confirm()
            return
        
        # If there's exactly one result, use it
        if self.results_list.count() == 1:
            item = self.results_list.item(0)
            self._on_item_clicked(item)
            self._on_confirm()
            return
        
        # Otherwise, check if current text is a valid manual entry
        text = self.search_input.text().strip().upper()
        if self._is_valid_format(text):
            self._pair = text
            self._on_confirm()

    def _on_confirm(self):
        """Handle confirm button click."""
        if self._pair:
            self.accept()

    def get_pair(self) -> Optional[str]:
        """Get the entered pair, or None if cancelled."""
        return self._pair

    def keyPressEvent(self, event):
        """Handle keyboard navigation."""
        key = event.key()
        
        if key == Qt.Key.Key_Down:
            # Move selection down in results list
            current = self.results_list.currentRow()
            if current < self.results_list.count() - 1:
                self.results_list.setCurrentRow(current + 1)
            elif current == -1 and self.results_list.count() > 0:
                self.results_list.setCurrentRow(0)
            event.accept()
            return
        
        elif key == Qt.Key.Key_Up:
            # Move selection up in results list
            current = self.results_list.currentRow()
            if current > 0:
                self.results_list.setCurrentRow(current - 1)
            event.accept()
            return
        
        super().keyPressEvent(event)

    @staticmethod
    def get_new_pair(data_source: str = "OKX", parent: Optional[QWidget] = None) -> Optional[str]:
        """
        Static method to show dialog and get a new pair.

        Args:
            data_source: Current data source ("OKX" or "Binance")
            parent: Parent widget

        Returns:
            The entered pair string, or None if cancelled.
        """
        dialog = AddPairDialog(data_source, parent)
        if dialog.exec():
            return dialog.get_pair()
        return None
