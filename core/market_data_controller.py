import logging
from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal

from core.exchange_factory import ExchangeFactory
from core.price_tracker import PriceTracker, PriceState
from core.alert_manager import get_alert_manager
from config.settings import get_settings_manager

logger = logging.getLogger(__name__)


class MarketDataController(QObject):
    """
    Controller for managing market data, signals, and alerts.
    Decouples data logic from the UI.
    """

    ticker_updated = pyqtSignal(str, object)  # pair, PriceState
    connection_status_changed = pyqtSignal(bool, str)  # connected, message
    connection_state_changed = pyqtSignal(str, str, int)  # state, message, retry_count
    data_source_changed = pyqtSignal()

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._settings_manager = get_settings_manager()
        self._price_tracker = PriceTracker()
        self._alert_manager = get_alert_manager()
        self._exchange_client = None

        self._init_client()

    def _init_client(self):
        """Initialize or re-initialize the exchange client."""
        # Stop existing client
        if self._exchange_client:
            self._disconnect_signals()
            # Safe cleanup
            old_client = self._exchange_client
            old_client.stopped.connect(old_client.deleteLater)
            old_client.stop()
            self._exchange_client = None

        # Create new client
        self._exchange_client = ExchangeFactory.create_client(self)

        # Connect signals
        self._exchange_client.ticker_updated.connect(self._on_ticker_update)
        self._exchange_client.connection_status.connect(self.connection_status_changed)
        self._exchange_client.connection_state_changed.connect(self.connection_state_changed)

        logger.info(f"Initialized exchange client: {self._exchange_client.__class__.__name__}")

    def _disconnect_signals(self):
        """Disconnect signals from the current client."""
        if self._exchange_client:
            try:
                self._exchange_client.ticker_updated.disconnect(self._on_ticker_update)
                self._exchange_client.connection_status.disconnect(self.connection_status_changed)
                self._exchange_client.connection_state_changed.disconnect(self.connection_state_changed)
            except (TypeError, RuntimeError):
                pass

    def start(self):
        """Start data fetching."""
        self.reload_pairs()

    def stop(self):
        """Stop data fetching."""
        if self._exchange_client:
            self._exchange_client.stop()

    def reload_pairs(self):
        """Reload pairs from settings and subscribe."""
        pairs = self._settings_manager.settings.crypto_pairs
        if self._exchange_client and pairs:
            self._exchange_client.subscribe(pairs)

    def _on_ticker_update(self, pair: str, data: dict):
        """Handle ticker update from exchange."""
        # Update price tracker
        state = self._price_tracker.update_price(pair, data)

        # Check price alerts
        self._alert_manager.check_alerts(pair, state.current_price, state.percentage)

        # Emit signal for UI
        self.ticker_updated.emit(pair, state)

    def set_data_source(self):
        """Handle data source change."""
        logger.info("Data source changed, switching client...")
        self._alert_manager.reset()
        self._init_client()
        self.reload_pairs()
        self.data_source_changed.emit()

    def set_proxy(self):
        """Handle proxy configuration change."""
        if self._exchange_client:
            self._exchange_client.reconnect()

    def get_price_state(self, pair: str) -> Optional[PriceState]:
        """Get current price state for a pair."""
        return self._price_tracker.get_state(pair)

    def clear_pair_data(self, pair: str):
        """Clear data for a specific pair."""
        self._price_tracker.clear_pair(pair)

    def get_current_price(self, pair: str) -> float:
        """Get current price for a pair (for alerts)."""
        state = self._price_tracker.get_state(pair)
        return state.current_price if state else 0.0
