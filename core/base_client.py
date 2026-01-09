from abc import abstractmethod
from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal


class BaseExchangeClient(QObject):
    """
    Abstract base class for crypto exchange clients.
    Defines the standard interface for WebSocket connections and data updates.
    """

    # Standard signals that all clients must emit
    # Signal emits: pair, data_dict
    # data_dict keys: price, percentage, high_24h, low_24h, volume_24h, quote_volume_24h
    ticker_updated = pyqtSignal(str, dict)
    connection_status = pyqtSignal(bool, str)  # connected, message
    connection_state_changed = pyqtSignal(str, str, int)  # state, message, retry_count
    stats_updated = pyqtSignal(dict)  # connection statistics
    stopped = pyqtSignal()  # Emitted when client is fully stopped and safe to delete

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)

    @abstractmethod
    def subscribe(self, pairs: list[str]):
        """Subscribe to a list of trading pairs."""
        pass

    @abstractmethod
    def stop(self):
        """Stop the connection."""
        pass

    @abstractmethod
    def reconnect(self):
        """Force reconnection."""
        pass

    @abstractmethod
    def get_stats(self) -> dict[str, Any] | None:
        """Get connection statistics."""
        pass

    @abstractmethod
    def fetch_klines(self, pair: str, interval: str, limit: int) -> list[dict]:
        """
        Fetch historical kline/candlestick data.
        Returns a list of dicts with at least:
        timestamp (ms), open, high, low, close, volume
        """
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connected."""
        pass
