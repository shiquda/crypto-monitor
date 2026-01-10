from PyQt6.QtCore import QObject

from config.settings import get_settings_manager
from core.base_client import BaseExchangeClient
from core.unified_client import UnifiedExchangeClient


class ExchangeFactory:
    @staticmethod
    def create_client(parent: QObject | None = None) -> BaseExchangeClient:
        settings = get_settings_manager().settings
        source = settings.data_source.upper()

        return UnifiedExchangeClient(source, parent)
