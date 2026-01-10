import asyncio
import json
import logging
import time
from typing import Any

import aiohttp
from PyQt6.QtCore import QObject

from config.settings import get_settings_manager
from core.base_client import BaseExchangeClient
from core.models import TickerData
from core.utils.network import get_aiohttp_proxy_url, get_proxy_config
from core.websocket_worker import BaseWebSocketWorker
from core.worker_controller import WorkerController

logger = logging.getLogger(__name__)


class BinanceWebSocketWorker(BaseWebSocketWorker):
    """
    Worker thread for Binance WebSocket connection.
    Uses aiohttp for proxy support via environment variables.
    """

    WS_URL = "wss://stream.binance.com:9443/ws"

    def __init__(self, pairs: list[str], parent: QObject | None = None):
        super().__init__(pairs, parent)
        self._symbol_map: dict[str, str] = {}
        self._precision_map: dict[str, int] = {}
        self._session: aiohttp.ClientSession | None = None
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._read_task: asyncio.Task | None = None

    async def _send_ping(self):
        """Send ping to Binance."""
        if self._ws and not self._ws.closed:
            try:
                # Send a standard WebSocket ping frame
                await self._ws.ping()
            except Exception as e:
                logger.debug(f"Binance ping failed: {e}")

    def set_precisions(self, precision_map: dict[str, int]):
        """Update precision map."""
        self._precision_map = precision_map

    async def _connect_and_subscribe(self):
        """Connect to Binance WebSocket and subscribe."""
        # Clean up existing session if any
        if self._session:
            await self._session.close()

        proxy_url = get_aiohttp_proxy_url()

        self._session = aiohttp.ClientSession(trust_env=True)
        self._ws = await self._session.ws_connect(self.WS_URL, proxy=proxy_url)
        self._connection_start_time = time.time()

        # Spawn read loop
        self._read_task = self._loop.create_task(self._read_loop())

        # Subscribe
        await self._update_subscriptions()

    async def fetch_klines_async(self, pair: str, interval: str, limit: int):
        symbol = pair.replace("-", "").upper()
        url = "https://api.binance.com/api/v3/klines"
        params = {"symbol": symbol, "interval": interval, "limit": limit}

        try:
            proxy_url = get_aiohttp_proxy_url()

            if self._session and not self._session.closed:
                async with self._session.get(url, params=params, proxy=proxy_url) as response:
                    data = await response.json()
            else:
                async with aiohttp.ClientSession(trust_env=True) as session:
                    async with session.get(url, params=params, proxy=proxy_url) as response:
                        data = await response.json()

            klines = []
            for item in data:
                klines.append(
                    {
                        "timestamp": item[0],
                        "open": float(item[1]),
                        "high": float(item[2]),
                        "low": float(item[3]),
                        "close": float(item[4]),
                        "volume": float(item[5]),
                    }
                )

            self.klines_ready.emit(pair, klines)

        except Exception as e:
            logger.error(f"Failed to fetch klines async for {pair}: {e}")

    async def _read_loop(self):
        """Read loop to handle incoming messages."""
        try:
            while self._running and self._ws and not self._ws.closed:
                try:
                    # aiohttp handles standard PING frames automatically (autoping=True).
                    msg = await self._ws.receive(timeout=1.0)
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        self._handle_message(msg.data)
                    elif msg.type == aiohttp.WSMsgType.PONG:
                        # Update heartbeat time when we receive a PONG from our manual ping
                        self._last_message_time = time.time()
                    elif msg.type == aiohttp.WSMsgType.CLOSED:
                        break
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        break
                except asyncio.TimeoutError:
                    continue
        except Exception as e:
            logger.error(f"Binance read loop error: {e}")
            self._last_error = str(e)

    async def _update_subscriptions(self):
        """Update subscriptions incrementally."""
        current_pairs = set(self.pairs)
        new_pairs = current_pairs - self._subscribed_pairs
        removed_pairs = self._subscribed_pairs - current_pairs

        if not self._ws or self._ws.closed:
            return

        # Binance streams need lowercase and removed hyphens
        # refresh symbol map
        self._symbol_map = {p.replace("-", "").lower(): p for p in self.pairs}

        # Subscribe to new
        if new_pairs:
            settings = get_settings_manager().settings
            basis = settings.price_change_basis

            if basis == "utc_0":
                streams = [f"{p.replace('-', '').lower()}@kline_1d" for p in new_pairs]
            else:
                streams = [f"{p.replace('-', '').lower()}@ticker" for p in new_pairs]

            if streams:
                subscribe_msg = {
                    "method": "SUBSCRIBE",
                    "params": streams,
                    "id": int(time.time() * 1000),  # Unique ID
                }
                await self._ws.send_json(subscribe_msg)

        # Unsubscribe from removed
        if removed_pairs:
            # Unsubscribe blindly from both possible stream types to be safe
            streams_ticker = [f"{p.replace('-', '').lower()}@ticker" for p in removed_pairs]
            streams_kline = [f"{p.replace('-', '').lower()}@kline_1d" for p in removed_pairs]

            # Combine unsub requests
            streams = streams_ticker + streams_kline

            if streams:
                unsubscribe_msg = {
                    "method": "UNSUBSCRIBE",
                    "params": streams,
                    "id": int(time.time() * 1000) + 1,
                }
                try:
                    await self._ws.send_json(unsubscribe_msg)
                except Exception:
                    pass

        self._subscribed_pairs = current_pairs
        self._update_stats()

    def _handle_message(self, message):
        try:
            self._last_message_time = time.time()
            data = json.loads(message)

            # Handle Ticker Event (24h Rolling)
            if data.get("e") == "24hrTicker":
                symbol = data.get("s", "").lower()
                price_str = data.get("c", "0")
                percent_val = data.get("P", "0")
                high_24h = data.get("h", "0")
                low_24h = data.get("l", "0")
                quote_volume = data.get("q", "0")
                self._process_ticker_data(
                    symbol, price_str, percent_val, high_24h, low_24h, quote_volume
                )

            # Handle Kline Event (UTC-0)
            elif data.get("e") == "kline":
                k = data.get("k", {})
                symbol = data.get("s", "").lower()
                price_str = k.get("c", "0")  # Close price

                # Calculate change % for UTC-0 (Close vs Open)
                open_price_str = k.get("o", "0")
                try:
                    close_float = float(price_str)
                    open_float = float(open_price_str)
                    if open_float > 0:
                        pct = (close_float - open_float) / open_float * 100
                    else:
                        pct = 0.0
                except Exception:
                    pct = 0.0

                percent_val = str(pct)
                high_24h = k.get("h", "0")
                low_24h = k.get("l", "0")
                quote_volume = k.get("q", "0")

                self._process_ticker_data(
                    symbol, price_str, percent_val, high_24h, low_24h, quote_volume
                )

            self._update_stats()

        except Exception as e:
            self._last_error = f"Message error: {e}"

    def _process_ticker_data(self, symbol, price_str, percent_val, high_24h, low_24h, quote_volume):
        try:
            # Format price based on precision
            if symbol in self._precision_map:
                precision = self._precision_map[symbol]
                try:
                    price_float = float(price_str)
                    price = f"{price_float:.{precision}f}"
                except Exception:
                    price = price_str
            else:
                from core.utils import format_price

                price = format_price(price_str)

            original_pair = self._symbol_map.get(symbol)
            if original_pair:
                try:
                    pct = float(percent_val)
                    formatted_pct = f"+{pct:.2f}%" if pct >= 0 else f"{pct:.2f}%"
                except Exception:
                    formatted_pct = "0.00%"

                ticker_obj = TickerData(
                    pair=original_pair,
                    price=price,
                    percentage=formatted_pct,
                    high_24h=high_24h,
                    low_24h=low_24h,
                    quote_volume_24h=quote_volume,
                )

                self.ticker_updated.emit(original_pair, ticker_obj)
        except Exception as e:
            logger.error(f"Error processing ticker data: {e}")

    def stop(self):
        """Stop connection and tasks."""
        self._running = False
        # The base class handles loop-safe cancellation, but we need to ensure session closes
        if self._loop and self._loop.is_running():

            async def cleanup():
                if self._ws:
                    await self._ws.close()
                if self._session:
                    await self._session.close()
                self._cancel_task_safe()

            self._loop.call_soon_threadsafe(lambda: self._loop.create_task(cleanup()))


class BinanceClient(BaseExchangeClient):
    """Binance Client implementation."""

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._worker: BinanceWebSocketWorker | None = None
        self._pairs: list[str] = []
        self._precision_map: dict[str, int] = {}  # pair -> decimals
        self._fetch_precisions()

    def _fetch_precisions(self):
        """Fetch symbol precision rules and validate pairs from Binance API."""
        import threading

        import requests

        def fetch():
            try:
                settings = get_settings_manager().settings
                proxies = {}
                if settings.proxy.enabled:
                    if settings.proxy.type == "http":
                        proxy_url = settings.proxy.get_proxy_url()
                        proxies = {"http": proxy_url, "https": proxy_url}
                    elif settings.proxy.type == "socks5":
                        proxy_url = settings.proxy.get_proxy_url()
                        proxies = {"http": proxy_url, "https": proxy_url}

                response = requests.get(
                    "https://api.binance.com/api/v3/exchangeInfo",
                    proxies=proxies,
                    timeout=10,
                )
                data = response.json()

                new_map = {}
                valid_symbols = set()

                for symbol_info in data.get("symbols", []):
                    symbol = symbol_info.get("symbol", "").lower()
                    valid_symbols.add(symbol)

                    tick_size = "0.01"
                    for filter_item in symbol_info.get("filters", []):
                        if filter_item.get("filterType") == "PRICE_FILTER":
                            tick_size = filter_item.get("tickSize", "0.01")
                            break

                    if "." in str(tick_size):
                        precision = len(str(tick_size).rstrip("0").split(".")[1])
                    else:
                        precision = 0

                    new_map[symbol] = precision

                # Check if client still exists
                try:
                    if hasattr(self, "_stop_requested") and not self._stop_requested:
                        self._precision_map = new_map

                        if self._pairs:
                            invalid_pairs = []
                            for pair in self._pairs:
                                normalized = pair.replace("-", "").lower()
                                if normalized not in valid_symbols:
                                    invalid_pairs.append(pair)

                            if invalid_pairs:
                                logger.warning(
                                    f"⚠️ [Binance Warning] Invalid: {', '.join(invalid_pairs)}"
                                )

                        if self._worker:
                            self._worker.set_precisions(self._precision_map)
                except RuntimeError:
                    pass

            except Exception as e:
                logger.error(f"Failed to fetch Binance precisions: {e}")
            finally:
                try:
                    if hasattr(self, "_fetching_precisions"):
                        self._fetching_precisions = False
                except RuntimeError:
                    pass

        threading.Thread(target=fetch, daemon=True).start()

    def _detach_and_stop_worker(self, worker: "BinanceWebSocketWorker"):
        WorkerController.get_instance().stop_worker(worker)

    def subscribe(self, pairs: list[str]):
        """Subscribe to ticker updates for given pairs with incremental update."""
        pairs = list(pairs)

        # If active worker, update incrementally
        if self._worker is not None and self._worker.isRunning():
            old_pairs = set(self._worker.pairs)
            new_pairs = set(pairs)

            if old_pairs != new_pairs:
                self._worker.pairs = pairs

            self._pairs = pairs
            return

        # No active worker, create one
        self._create_worker(pairs)

    def _create_worker(self, pairs: list[str]):
        if self._worker:
            self._detach_and_stop_worker(self._worker)

        self._pairs = pairs
        self._worker = BinanceWebSocketWorker(pairs, self)
        self._worker.set_precisions(self._precision_map)
        self._worker.ticker_updated.connect(self.ticker_updated)
        self._worker.connection_status.connect(self.connection_status)
        self._worker.connection_state_changed.connect(self.connection_state_changed)
        self._worker.stats_updated.connect(self.stats_updated)
        self._worker.klines_ready.connect(self.klines_ready)

        WorkerController.get_instance().register_worker(self._worker)
        self._worker.start()

    def stop(self):
        self._stop_requested = True
        if self._worker:
            self._detach_and_stop_worker(self._worker)
            self._worker = None
        self.stopped.emit()

    def reconnect(self):
        if self._pairs:
            self._create_worker(self._pairs)

    def get_stats(self) -> dict[str, Any] | None:
        """Get current connection statistics."""
        if self._worker is not None:
            state = "unknown"
            if hasattr(self._worker, "_connection_state"):
                state = self._worker._connection_state.value

            return {
                "state": state,
                "subscribed_pairs": len(self._pairs),
                "worker_running": self._worker.isRunning(),
            }

    def request_klines(self, pair: str, interval: str, limit: int = 24):
        if self._worker is not None and self._worker.isRunning():
            self._worker.request_klines(pair, interval, limit)
        else:
            super().request_klines(pair, interval, limit)

    def fetch_klines(self, pair: str, interval: str, limit: int = 24) -> list[dict]:
        import requests

        symbol = pair.replace("-", "").upper()

        url = "https://api.binance.com/api/v3/klines"
        params = {"symbol": symbol, "interval": interval, "limit": limit}

        try:
            proxies = get_proxy_config()
            response = requests.get(url, params=params, proxies=proxies, timeout=5)
            response.raise_for_status()
            data = response.json()

            klines = []
            for item in data:
                klines.append(
                    {
                        "timestamp": item[0],
                        "open": float(item[1]),
                        "high": float(item[2]),
                        "low": float(item[3]),
                        "close": float(item[4]),
                        "volume": float(item[5]),
                    }
                )
            return klines

        except Exception as e:
            logger.error(f"Failed to fetch klines for {pair}: {e}")
            return []

    @property
    def is_connected(self) -> bool:
        if self._worker is None or not self._worker.isRunning():
            return False
        if hasattr(self._worker, "_last_message_time"):
            import time

            return (time.time() - self._worker._last_message_time) < 30
        return False
