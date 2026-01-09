from PyQt6.QtCore import QObject

from config.settings import get_settings_manager
from core.base_client import BaseExchangeClient
from core.binance_client import BinanceClient
from core.okx_client import OkxClientManager


class ExchangeFactory:
    """Factory for creating crypto exchange clients."""

    @staticmethod
    def create_client(parent: QObject | None = None) -> BaseExchangeClient:
        """Create a client instance based on global settings."""
        settings = get_settings_manager().settings
        source = settings.data_source.upper()

        if source == "BINANCE":
            return BinanceClient(parent)
        else:
            # Default to OKX
            return OkxClientManager(parent)
