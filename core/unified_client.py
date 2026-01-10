from PyQt6.QtCore import QObject

from core.base_client import BaseExchangeClient
from core.binance_client import BinanceClient
from core.dex_client import DexScreenerClient
from core.okx_client import OkxClientManager


class UnifiedExchangeClient(BaseExchangeClient):
    def __init__(self, source: str, parent: QObject | None = None):
        super().__init__(parent)

        self._dex_client = DexScreenerClient(self)

        if source.upper() == "BINANCE":
            self._cex_client = BinanceClient(self)
        else:
            self._cex_client = OkxClientManager(self)

        self._connect_signals(self._dex_client)
        self._connect_signals(self._cex_client)

    def _connect_signals(self, client: BaseExchangeClient):
        client.ticker_updated.connect(self.ticker_updated)
        client.connection_status.connect(self.connection_status)
        client.connection_state_changed.connect(self.connection_state_changed)
        client.stats_updated.connect(self.stats_updated)
        client.klines_ready.connect(self.klines_ready)

    def subscribe(self, pairs: list[str]):
        dex_pairs = []
        cex_pairs = []

        for pair in pairs:
            if pair.lower().startswith("chain:"):
                dex_pairs.append(pair)
            else:
                cex_pairs.append(pair)

        self._dex_client.subscribe(dex_pairs)
        self._cex_client.subscribe(cex_pairs)

    def stop(self):
        self._dex_client.stop()
        self._cex_client.stop()
        self.stopped.emit()

    def reconnect(self):
        self._dex_client.reconnect()
        self._cex_client.reconnect()

    def get_stats(self):
        dex_stats = self._dex_client.get_stats() or {}
        cex_stats = self._cex_client.get_stats() or {}
        return {"dex": dex_stats, "cex": cex_stats}

    def fetch_klines(self, pair: str, interval: str, limit: int) -> list[dict]:
        if pair.lower().startswith("chain:"):
            return self._dex_client.fetch_klines(pair, interval, limit)
        return self._cex_client.fetch_klines(pair, interval, limit)

    @property
    def is_connected(self) -> bool:
        return self._cex_client.is_connected or self._dex_client.is_connected
