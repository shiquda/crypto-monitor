import json
import logging
import re

from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkProxy, QNetworkReply, QNetworkRequest
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import Dialog, ProgressRing, SearchLineEdit, SegmentedWidget, isDarkTheme

from config.settings import get_settings_manager
from core.i18n import _
from core.symbol_search import SymbolInfo, get_symbol_search_service

logger = logging.getLogger(__name__)


class AddPairDialog(Dialog):
    def __init__(self, data_source: str = "OKX", parent: QWidget | None = None):
        super().__init__(title=_("Add Trading Pair"), content="", parent=parent)
        self._pair: str | None = None
        self._data_source = data_source
        self._search_service = get_symbol_search_service()
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._do_search)
        self._updating_from_selection = False

        self._dex_manager = QNetworkAccessManager(self)
        self._dex_manager.finished.connect(self._on_dex_response)

        self._configure_proxy()

        self.setFixedSize(500, 600)

        flags = (
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        if parent and (parent.windowFlags() & Qt.WindowType.WindowStaysOnTopHint):
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

        self._setup_ui()

        self._search_service.symbols_loaded.connect(self._on_symbols_loaded)
        self._search_service.loading_started.connect(self._on_loading_started)
        self._search_service.loading_error.connect(self._on_loading_error)

        self._search_service.load_symbols(self._data_source)

    def _configure_proxy(self):
        settings = get_settings_manager().settings
        if settings.proxy.enabled:
            logger.debug(
                f"Configuring proxy for DexSearch: {settings.proxy.host}:{settings.proxy.port}"
            )
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

            self._dex_manager.setProxy(proxy)
        else:
            self._dex_manager.setProxy(QNetworkProxy(QNetworkProxy.ProxyType.NoProxy))

    def _setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(12)

        self.segment = SegmentedWidget()
        self.segment.addItem("cex", _("Exchange (CEX)"))
        self.segment.addItem("dex", _("On-Chain (DEX)"))
        self.segment.setCurrentItem("cex")
        self.segment.currentItemChanged.connect(self._on_tab_changed)
        main_layout.addWidget(self.segment)

        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)

        self.cex_widget = QWidget()
        self._setup_cex_tab(self.cex_widget)
        self.stack.addWidget(self.cex_widget)

        self.dex_widget = QWidget()
        self._setup_dex_tab(self.dex_widget)
        self.stack.addWidget(self.dex_widget)

        self.textLayout.addLayout(main_layout)

        self.yesButton.setText(_("Add"))
        self.yesButton.setEnabled(False)
        self.cancelButton.setText(_("Cancel"))
        self.yesButton.clicked.connect(self._on_confirm)

    def _on_tab_changed(self, key: str):
        self.stack.setCurrentIndex(0 if key == "cex" else 1)
        self.yesButton.setEnabled(False)
        self._pair = None

    def _setup_cex_tab(self, parent_widget):
        layout = QVBoxLayout(parent_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        label = QLabel(_("Search trading pairs:"))
        label.setStyleSheet("font-size: 14px;")
        layout.addWidget(label)

        search_row = QHBoxLayout()
        search_row.setSpacing(8)

        self.search_input = SearchLineEdit()
        self.search_input.setPlaceholderText(_("Enter symbol (e.g., BTC, ETH-USDT)..."))
        self.search_input.setFixedHeight(36)
        self.search_input.textChanged.connect(self._on_search_text_changed)
        self.search_input.returnPressed.connect(self._on_return_pressed)
        search_row.addWidget(self.search_input)

        self.loading_spinner = ProgressRing()
        self.loading_spinner.setFixedSize(24, 24)
        self.loading_spinner.setVisible(False)
        search_row.addWidget(self.loading_spinner)

        layout.addLayout(search_row)

        self.results_list = QListWidget()
        self.results_list.setFixedHeight(200)
        self.results_list.itemClicked.connect(self._on_item_clicked)
        self.results_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self._style_list_widget(self.results_list)
        layout.addWidget(self.results_list)

        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #888; font-size: 12px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #D13438; font-size: 12px;")
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)

        layout.addStretch()

    def _setup_dex_tab(self, parent_widget):
        layout = QVBoxLayout(parent_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        label = QLabel(_("Search by Name or Address:"))
        label.setStyleSheet("font-size: 14px;")
        layout.addWidget(label)

        input_row = QHBoxLayout()
        self.dex_input = SearchLineEdit()
        self.dex_input.setPlaceholderText(_("Enter token name (e.g., PEPE) or address"))
        self.dex_input.setFixedHeight(36)
        self.dex_input.textChanged.connect(self._on_dex_text_changed)
        self.dex_input.returnPressed.connect(self._do_dex_search)
        self.dex_input.searchButton.clicked.connect(self._do_dex_search)
        input_row.addWidget(self.dex_input)

        self.dex_spinner = ProgressRing()
        self.dex_spinner.setFixedSize(24, 24)
        self.dex_spinner.setVisible(False)
        input_row.addWidget(self.dex_spinner)

        layout.addLayout(input_row)

        self.dex_results = QListWidget()
        self.dex_results.setFixedHeight(200)
        self.dex_results.itemClicked.connect(self._on_dex_item_clicked)
        self.dex_results.itemDoubleClicked.connect(self._on_item_double_clicked)
        self._style_list_widget(self.dex_results)
        layout.addWidget(self.dex_results)

        self.dex_status = QLabel(_("Enter token name or paste address to search"))
        self.dex_status.setStyleSheet("color: #888; font-size: 12px;")
        self.dex_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.dex_status)

        layout.addStretch()

    def _style_list_widget(self, widget: QListWidget):
        is_dark = isDarkTheme()
        bg_color = "#2d2d2d" if is_dark else "#ffffff"
        text_color = "#ffffff" if is_dark else "#1a1a1a"
        hover_bg = "#3d3d3d" if is_dark else "#f0f0f0"
        selected_bg = "#0078d4" if is_dark else "#0078d4"
        border_color = "#404040" if is_dark else "#e0e0e0"

        widget.setStyleSheet(f"""
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
        self.loading_spinner.setVisible(True)
        self.status_label.setText(_("Loading symbols..."))
        self.results_list.clear()

    def _on_symbols_loaded(self, symbols: list[SymbolInfo]):
        self.loading_spinner.setVisible(False)
        self.status_label.setText(_("{count} symbols available").format(count=len(symbols)))
        self._do_search()

    def _on_loading_error(self, error: str):
        self.loading_spinner.setVisible(False)
        self.status_label.setText(_("Failed to load symbols"))
        self.error_label.setText(error)
        self.error_label.setVisible(True)

    def _on_search_text_changed(self, text: str):
        if self._updating_from_selection:
            return
        self._pair = None
        self.yesButton.setEnabled(False)
        self.error_label.setVisible(False)
        self._search_timer.stop()
        self._search_timer.start(200)

    def _do_search(self):
        query = self.search_input.text().strip()
        results = self._search_service.search(query, limit=50)
        self.results_list.clear()

        if not results:
            if query:
                self.status_label.setText(_("No matching pairs found"))
                if self._is_valid_format(query):
                    self._pair = query.upper()
                    self.yesButton.setEnabled(True)
                    self.status_label.setText(
                        _("No match found. Add '{pair}' anyway?").format(pair=self._pair)
                    )
            else:
                self.status_label.setText(_("Enter a symbol to search"))
            return

        for symbol_info in results:
            item = QListWidgetItem(symbol_info.symbol)
            item.setData(Qt.ItemDataRole.UserRole, symbol_info)
            self.results_list.addItem(item)

        self.status_label.setText(_("Found {count} matches").format(count=len(results)))

    def _on_dex_text_changed(self, text: str):
        """Handle DEX input text changes for auto-search"""
        self._pair = None
        self.yesButton.setEnabled(False)

    def _is_contract_address(self, text: str) -> bool:
        """Check if the input looks like a contract address"""
        text = text.strip()
        # Ethereum-like address (0x...)
        if text.startswith("0x") and len(text) == 42:
            return True
        # Solana address (base58, typically 32-44 chars)
        if len(text) >= 32 and not text.startswith("0x"):
            return True
        return False

    def _do_dex_search(self):
        query = self.dex_input.text().strip()
        if not query:
            return

        logger.debug(f"Starting DEX search for: {query}")
        self.dex_spinner.setVisible(True)
        self.dex_results.clear()
        self.dex_status.setText(_("Searching..."))

        # Determine if it's an address or name search
        if self._is_contract_address(query):
            # Address search - use /tokens endpoint
            url = f"https://api.dexscreener.com/latest/dex/tokens/{query}"
            logger.debug(f"Address search: {url}")
        else:
            # Name search - use /search endpoint
            url = f"https://api.dexscreener.com/latest/dex/search?q={query}"
            logger.debug(f"Name search: {url}")

        req = QNetworkRequest(QUrl(url))
        req.setHeader(QNetworkRequest.KnownHeaders.UserAgentHeader, "Mozilla/5.0")
        self._dex_manager.get(req)

    def _on_dex_response(self, reply: QNetworkReply):
        self.dex_spinner.setVisible(False)

        err = reply.error()
        if err != QNetworkReply.NetworkError.NoError:
            error_str = reply.errorString()
            logger.error(f"DEX Search Network Error: {err} - {error_str}")
            self.dex_status.setText(f"Network Error: {error_str}")
            reply.deleteLater()
            return

        try:
            raw_data = bytes(reply.readAll())
            data = json.loads(raw_data)

            # Handle both /tokens and /search API responses
            pairs = data.get("pairs", [])

            if not pairs:
                logger.debug("No pairs found in response")
                self.dex_status.setText(
                    _("No tokens found matching '{query}'").format(
                        query=self.dex_input.text().strip()
                    )
                )
                return

            seen_keys = set()
            display_items = []

            # Sort by liquidity (highest first)
            pairs.sort(key=lambda x: float(x.get("liquidity", {}).get("usd", 0) or 0), reverse=True)

            for p in pairs:
                chain = p.get("chainId")
                base = p.get("baseToken", {}).get("symbol")
                base_name = p.get("baseToken", {}).get("name", "")
                quote = p.get("quoteToken", {}).get("symbol")
                addr = p.get("baseToken", {}).get("address")
                liquidity = float(p.get("liquidity", {}).get("usd", 0) or 0)

                # Create unique key to avoid duplicates
                key = f"{chain}:{base}:{addr}"
                if key in seen_keys:
                    continue
                seen_keys.add(key)

                # Format display string with name, chain, and liquidity
                if liquidity >= 1000000:
                    liq_str = f"${liquidity / 1000000:.1f}M"
                elif liquidity >= 1000:
                    liq_str = f"${liquidity / 1000:.1f}K"
                else:
                    liq_str = f"${liquidity:.0f}"

                display = f"{base}/{quote} - {base_name} ({chain}) [{liq_str}]"
                item_id = f"chain:{chain}:{addr}:{base}"

                display_items.append((display, item_id))

                # Limit to 30 results to avoid overwhelming the UI
                if len(display_items) >= 30:
                    break

            for display, pid in display_items:
                item = QListWidgetItem(display)
                item.setData(Qt.ItemDataRole.UserRole, pid)
                self.dex_results.addItem(item)

            count = len(display_items)
            logger.debug(f"Found {count} pairs")
            self.dex_status.setText(_("Found {count} pairs").format(count=count))

        except Exception as e:
            logger.error(f"Error parsing DEX response: {e}", exc_info=True)
            self.dex_status.setText(f"Error: {str(e)}")

        reply.deleteLater()

    def _is_valid_format(self, text: str) -> bool:
        text = text.strip().upper()
        pattern = r"^[A-Z0-9]+-[A-Z0-9]+$"
        return bool(re.match(pattern, text))

    def _on_item_clicked(self, item: QListWidgetItem):
        symbol_info: SymbolInfo = item.data(Qt.ItemDataRole.UserRole)
        if symbol_info:
            self._pair = symbol_info.symbol
            self._updating_from_selection = True
            self.search_input.setText(symbol_info.symbol)
            self._updating_from_selection = False
            self.yesButton.setEnabled(True)
            self.error_label.setVisible(False)

    def _on_dex_item_clicked(self, item: QListWidgetItem):
        pair_id = item.data(Qt.ItemDataRole.UserRole)
        if pair_id:
            self._pair = pair_id
            self.yesButton.setEnabled(True)

    def _on_item_double_clicked(self, item: QListWidgetItem):
        if self.segment.currentItem() == "cex":
            self._on_item_clicked(item)
        else:
            self._on_dex_item_clicked(item)
        self._on_confirm()

    def _on_return_pressed(self):
        if self.segment.currentItem() == "dex":
            self._do_dex_search()
            return

        selected_items = self.results_list.selectedItems()
        if selected_items:
            self._on_item_clicked(selected_items[0])
            self._on_confirm()
            return

        if self.results_list.count() == 1:
            item = self.results_list.item(0)
            self._on_item_clicked(item)
            self._on_confirm()
            return

        text = self.search_input.text().strip().upper()
        if self._is_valid_format(text):
            self._pair = text
            self._on_confirm()

    def _on_confirm(self):
        if self._pair:
            self.accept()

    def get_pair(self) -> str | None:
        return self._pair

    def keyPressEvent(self, event):
        key = event.key()
        active_list = self.results_list if self.segment.currentItem() == "cex" else self.dex_results

        if key == Qt.Key.Key_Down:
            current = active_list.currentRow()
            if current < active_list.count() - 1:
                active_list.setCurrentRow(current + 1)
            elif current == -1 and active_list.count() > 0:
                active_list.setCurrentRow(0)
            event.accept()
            return

        elif key == Qt.Key.Key_Up:
            current = active_list.currentRow()
            if current > 0:
                active_list.setCurrentRow(current - 1)
            event.accept()
            return

        super().keyPressEvent(event)

    @staticmethod
    def get_new_pair(data_source: str = "OKX", parent: QWidget | None = None) -> str | None:
        dialog = AddPairDialog(data_source, parent)
        if dialog.exec():
            return dialog.get_pair()
        return None
