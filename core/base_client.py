from abc import ABC, abstractmethod
from typing import List, Optional, Any, Dict
from PyQt6.QtCore import QObject, pyqtSignal

class BaseExchangeClient(QObject):
    """
    Abstract base class for crypto exchange clients.
    Defines the standard interface for WebSocket connections and data updates.
    """
    
    # Standard signals that all clients must emit
    ticker_updated = pyqtSignal(str, str, str)  # pair (e.g. BTC-USDT), price, percentage
    connection_status = pyqtSignal(bool, str)   # connected, message
    connection_state_changed = pyqtSignal(str, str, int)  # state, message, retry_count
    stats_updated = pyqtSignal(dict)            # connection statistics
    stopped = pyqtSignal()                      # Emitted when client is fully stopped and safe to delete

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)

    @abstractmethod
    def subscribe(self, pairs: List[str]):
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
    def get_stats(self) -> Optional[Dict[str, Any]]:
        """Get connection statistics."""
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connected."""
        pass
