from abc import abstractmethod
from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal

from core.models import TickerData


class BaseExchangeClient(QObject):
    """
    Abstract base class for crypto exchange clients.
    Defines the standard interface for WebSocket connections and data updates.
    """

    # Standard signals that all clients must emit
    ticker_updated = pyqtSignal(str, TickerData)
    connection_status = pyqtSignal(bool, str)  # connected, message
    connection_state_changed = pyqtSignal(str, str, int)  # state, message, retry_count
    stats_updated = pyqtSignal(dict)  # connection statistics
    klines_ready = pyqtSignal(str, list)
    stopped = pyqtSignal()

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
        Fetch historical kline/candlestick data (Synchronous/Blocking).
        Returns a list of dicts with at least:
        timestamp (ms), open, high, low, close, volume
        """
        pass

    def request_klines(self, pair: str, interval: str, limit: int = 24):
        """
        Request kline data asynchronously.
        Should emit klines_ready signal when data is available.
        """
        import threading

        def _fetch():
            data = self.fetch_klines(pair, interval, limit)
            self.klines_ready.emit(pair, data)

        threading.Thread(target=_fetch, daemon=True).start()

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connected."""
        pass
