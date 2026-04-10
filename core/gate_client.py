import asyncio
import datetime
import logging
import time
from typing import Any

import aiohttp
import requests
from PyQt6.QtCore import QObject

from core.base_client import BaseExchangeClient
from core.models import TickerData
from core.utils import format_price
from core.utils.network import get_aiohttp_proxy_url, get_proxy_config
from core.websocket_worker import BaseWebSocketWorker
from core.worker_controller import WorkerController

logger = logging.getLogger(__name__)


class GateWebSocketWorker(BaseWebSocketWorker):
    """Gate spot websocket worker for real-time ticker push."""

    WS_URL = "wss://api.gateio.ws/ws/v4/"
    FUTURES_WS_URL = "wss://fx-ws.gateio.ws/v4/ws/usdt"

    def __init__(self, pairs: list[str], parent: QObject | None = None):
        super().__init__(pairs, parent)
        self._session: aiohttp.ClientSession | None = None
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._read_task: asyncio.Task | None = None
        self._pair_map: dict[str, str] = {}
        self._market_type = "spot"
        self._daily_open_prices: dict[str, float] = {}
        self._daily_high_prices: dict[str, str] = {}
        self._daily_low_prices: dict[str, str] = {}

    def set_market_type(self, market_type: str):
        self._market_type = market_type

    def _channel_name(self) -> str:
        return "futures.tickers" if self._market_type == "mark" else "spot.tickers"

    def _ws_url(self) -> str:
        return self.FUTURES_WS_URL if self._market_type == "mark" else self.WS_URL

    @staticmethod
    def _get_price_change_basis() -> str:
        try:
            from config.settings import get_settings_manager

            return get_settings_manager().settings.price_change_basis
        except Exception:
            return "24h_rolling"

    @staticmethod
    def _day_start_unix_seconds(tz_hours: int) -> int:
        tz = datetime.timezone(datetime.timedelta(hours=tz_hours))
        now = datetime.datetime.now(tz)
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return int(day_start.timestamp())

    def _extract_open_from_candle(self, row: object) -> float | None:
        try:
            if isinstance(row, dict):
                return float(row.get("o", 0))

            if isinstance(row, list) and len(row) >= 6:
                if self._market_type == "mark":
                    return float(row[1])
                return float(row[5])
        except Exception:
            return None

        return None

    async def _refresh_daily_open_prices(self, pairs: list[str]):
        basis = self._get_price_change_basis()
        if basis == "24h_rolling" or not pairs:
            return

        proxy_url = get_aiohttp_proxy_url()
        tz_hours = 8 if basis == "utc_8" else 0
        from_ts = self._day_start_unix_seconds(tz_hours)
        to_ts = from_ts + 3600

        if self._market_type == "mark":
            url = "https://api.gateio.ws/api/v4/futures/usdt/candlesticks"
        else:
            url = "https://api.gateio.ws/api/v4/spot/candlesticks"

        async with aiohttp.ClientSession(trust_env=True) as session:
            for pair in pairs:
                symbol = self._normalize_pair(pair)
                try:
                    if self._market_type == "mark":
                        params = {
                            "contract": f"mark_{symbol}",
                            "interval": "1h",
                            "from": from_ts,
                            "to": to_ts,
                        }
                    else:
                        params = {
                            "currency_pair": symbol,
                            "interval": "1h",
                            "from": from_ts,
                            "to": to_ts,
                        }

                    async with session.get(
                        url,
                        params=params,
                        proxy=proxy_url,
                    ) as response:
                        payload = await response.json()

                    if not isinstance(payload, list) or not payload:
                        continue

                    row = payload[0]
                    open_price = self._extract_open_from_candle(row)
                    if open_price is None or open_price <= 0:
                        continue

                    self._daily_open_prices[symbol] = open_price
                    parsed = self._parse_candle_row(row)
                    if parsed:
                        self._daily_high_prices[symbol] = str(parsed.get("high", "0"))
                        self._daily_low_prices[symbol] = str(parsed.get("low", "0"))
                except Exception as e:
                    logger.debug(f"Failed to refresh Gate open price for {symbol}: {e}")

    @staticmethod
    def _normalize_pair(pair: str) -> str:
        return pair.replace("-", "_").upper()

    @staticmethod
    def _display_pair(gate_pair: str) -> str:
        return gate_pair.replace("_", "-").upper()

    def _parse_candle_row(self, row: object) -> dict | None:
        try:
            if isinstance(row, dict):
                return {
                    "timestamp": int(float(row.get("t", 0))) * 1000,
                    "open": float(row.get("o", 0)),
                    "high": float(row.get("h", 0)),
                    "low": float(row.get("l", 0)),
                    "close": float(row.get("c", 0)),
                    "volume": float(row.get("v", 0)),
                }

            if isinstance(row, list) and len(row) >= 6:
                timestamp = int(float(row[0])) * 1000
                if self._market_type == "mark":
                    open_price = float(row[1])
                    close = float(row[2])
                    high = float(row[3])
                    low = float(row[4])
                    volume = float(row[5])
                else:
                    volume = float(row[1])
                    close = float(row[2])
                    high = float(row[3])
                    low = float(row[4])
                    open_price = float(row[5])

                return {
                    "timestamp": timestamp,
                    "open": open_price,
                    "high": high,
                    "low": low,
                    "close": close,
                    "volume": volume,
                }
        except Exception:
            return None

        return None

    async def _send_ping(self):
        if self._ws and not self._ws.closed:
            try:
                await self._ws.ping()
            except Exception as e:
                logger.debug(f"Gate ping failed: {e}")

    async def _connect_and_subscribe(self):
        if self._session:
            await self._session.close()

        proxy_url = get_aiohttp_proxy_url()
        self._session = aiohttp.ClientSession(trust_env=True)
        self._ws = await self._session.ws_connect(self._ws_url(), proxy=proxy_url)
        self._connection_start_time = time.time()

        await self._refresh_daily_open_prices(self.pairs)

        self._read_task = self._loop.create_task(self._read_loop())
        await self._update_subscriptions()

    async def _read_loop(self):
        try:
            while self._running and self._ws and not self._ws.closed:
                try:
                    msg = await self._ws.receive(timeout=1.0)
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        self._handle_message(msg.data)
                    elif msg.type == aiohttp.WSMsgType.PONG:
                        self._last_message_time = time.time()
                    elif msg.type in {
                        aiohttp.WSMsgType.CLOSED,
                        aiohttp.WSMsgType.ERROR,
                    }:
                        break
                except asyncio.TimeoutError:
                    continue
        except Exception as e:
            logger.error(f"Gate read loop error: {e}")
            self._last_error = str(e)

    async def _update_subscriptions(self):
        current_pairs = set(self.pairs)
        new_pairs = current_pairs - self._subscribed_pairs
        removed_pairs = self._subscribed_pairs - current_pairs

        self._pair_map = {self._normalize_pair(p): p for p in self.pairs}

        if not self._ws or self._ws.closed:
            return

        if new_pairs:
            payload = [self._normalize_pair(p) for p in new_pairs]
            if payload:
                await self._ws.send_json(
                    {
                        "time": int(time.time()),
                        "channel": self._channel_name(),
                        "event": "subscribe",
                        "payload": payload,
                    }
                )

            await self._refresh_daily_open_prices(list(new_pairs))

        if removed_pairs:
            payload = [self._normalize_pair(p) for p in removed_pairs]
            if payload:
                await self._ws.send_json(
                    {
                        "time": int(time.time()),
                        "channel": self._channel_name(),
                        "event": "unsubscribe",
                        "payload": payload,
                    }
                )

        self._subscribed_pairs = current_pairs
        self._update_stats()

    @staticmethod
    def _format_percentage(value: str | float | int | None) -> str:
        try:
            pct = float(value or 0)
            return f"+{pct:.2f}%" if pct >= 0 else f"{pct:.2f}%"
        except (TypeError, ValueError):
            return "0.00%"

    def _handle_message(self, message: str):
        import json

        try:
            data = json.loads(message)
            self._last_message_time = time.time()

            if (
                data.get("event") != "update"
                or data.get("channel") != self._channel_name()
            ):
                return

            result = data.get("result")
            if isinstance(result, list):
                tickers = result
            elif isinstance(result, dict):
                tickers = [result]
            else:
                tickers = []

            for ticker in tickers:
                gate_pair = str(ticker.get("currency_pair", "")).upper()
                if not gate_pair:
                    gate_pair = str(ticker.get("contract", "")).upper()
                if not gate_pair:
                    continue

                pair = self._pair_map.get(gate_pair, self._display_pair(gate_pair))
                price_raw = ticker.get("mark_price", ticker.get("last", "0"))
                price = format_price(price_raw)

                basis = self._get_price_change_basis()
                if basis == "24h_rolling":
                    percentage = self._format_percentage(
                        ticker.get("change_percentage", "0")
                    )
                else:
                    try:
                        current = float(price_raw)
                        open_price = self._daily_open_prices.get(gate_pair, 0.0)
                        if open_price > 0:
                            pct = (current - open_price) / open_price * 100
                            percentage = self._format_percentage(pct)
                        else:
                            percentage = "0.00%"
                    except Exception:
                        percentage = "0.00%"

                self.ticker_updated.emit(
                    pair,
                    TickerData(
                        pair=pair,
                        price=price,
                        percentage=percentage,
                        high_24h=(
                            str(ticker.get("high_24h", "0"))
                            if str(ticker.get("high_24h", "0")) not in {"", "0", "0.0"}
                            else self._daily_high_prices.get(gate_pair, "0")
                        ),
                        low_24h=(
                            str(ticker.get("low_24h", "0"))
                            if str(ticker.get("low_24h", "0")) not in {"", "0", "0.0"}
                            else self._daily_low_prices.get(gate_pair, "0")
                        ),
                        quote_volume_24h=str(ticker.get("quote_volume", "0")),
                    ),
                )

            self._update_stats()

        except Exception as e:
            self._last_error = f"Message error: {e}"
            logger.error(f"Error handling Gate message: {e}")

    def stop(self):
        self._running = False
        if self._loop and self._loop.is_running():

            async def cleanup():
                if self._ws:
                    await self._ws.close()
                if self._session:
                    await self._session.close()
                self._cancel_task_safe()

            self._loop.call_soon_threadsafe(lambda: self._loop.create_task(cleanup()))


class GateClient(BaseExchangeClient):
    """Gate spot client with websocket push and REST kline fetch."""

    BASE_URL = "https://api.gateio.ws/api/v4"

    def __init__(self, parent: QObject | None = None, market_type: str = "spot"):
        super().__init__(parent)
        self._worker: GateWebSocketWorker | None = None
        self._pairs: list[str] = []
        self._market_type = market_type

    def _is_mark(self) -> bool:
        return self._market_type == "mark"

    @staticmethod
    def _normalize_pair(pair: str) -> str:
        return pair.replace("-", "_").upper()

    @staticmethod
    def _to_gate_interval(interval: str) -> str:
        normalized = interval.lower()
        if normalized in {
            "10s",
            "1m",
            "5m",
            "15m",
            "30m",
            "1h",
            "4h",
            "8h",
            "1d",
            "7d",
        }:
            return normalized
        return "1h"

    def _parse_candle_row(self, row: object) -> dict | None:
        try:
            if isinstance(row, dict):
                return {
                    "timestamp": int(float(row.get("t", 0))) * 1000,
                    "open": float(row.get("o", 0)),
                    "high": float(row.get("h", 0)),
                    "low": float(row.get("l", 0)),
                    "close": float(row.get("c", 0)),
                    "volume": float(row.get("v", 0)),
                }

            if isinstance(row, list) and len(row) >= 6:
                timestamp = int(float(row[0])) * 1000
                if self._is_mark():
                    open_price = float(row[1])
                    close = float(row[2])
                    high = float(row[3])
                    low = float(row[4])
                    volume = float(row[5])
                else:
                    volume = float(row[1])
                    close = float(row[2])
                    high = float(row[3])
                    low = float(row[4])
                    open_price = float(row[5])

                return {
                    "timestamp": timestamp,
                    "open": open_price,
                    "high": high,
                    "low": low,
                    "close": close,
                    "volume": volume,
                }
        except Exception:
            return None

        return None

    def _detach_and_stop_worker(self, worker: "GateWebSocketWorker"):
        WorkerController.get_instance().stop_worker(worker)

    def subscribe(self, pairs: list[str]):
        pairs = [p.upper() for p in pairs if not p.lower().startswith("chain:")]

        if self._worker is not None and self._worker.isRunning():
            if set(self._worker.pairs) != set(pairs):
                self._worker.pairs = list(pairs)
            self._pairs = list(pairs)
            return

        self._create_worker(pairs)

    def _create_worker(self, pairs: list[str]):
        if self._worker:
            self._detach_and_stop_worker(self._worker)

        self._pairs = list(pairs)
        self._worker = GateWebSocketWorker(self._pairs, self)
        self._worker.set_market_type(self._market_type)
        self._worker.ticker_updated.connect(self.ticker_updated)
        self._worker.connection_status.connect(self.connection_status)
        self._worker.connection_state_changed.connect(self.connection_state_changed)
        self._worker.stats_updated.connect(self.stats_updated)
        self._worker.klines_ready.connect(self.klines_ready)

        WorkerController.get_instance().register_worker(self._worker)
        self._worker.start()

    def stop(self):
        if self._worker:
            self._detach_and_stop_worker(self._worker)
            self._worker = None
        self.stopped.emit()

    def reconnect(self):
        if self._pairs:
            self._create_worker(self._pairs)

    def get_stats(self) -> dict[str, Any] | None:
        if self._worker is not None:
            state = "unknown"
            if hasattr(self._worker, "_connection_state"):
                state = self._worker._connection_state.value
            return {
                "state": state,
                "exchange": "GATE",
                "subscribed_pairs": len(self._pairs),
                "worker_running": self._worker.isRunning(),
            }
        return {
            "state": "disconnected",
            "exchange": "GATE",
            "subscribed_pairs": 0,
            "worker_running": False,
        }

    def request_klines(self, pair: str, interval: str, limit: int = 24):
        if self._worker is not None and self._worker.isRunning():
            self._worker.request_klines(pair, interval, limit)
        else:
            super().request_klines(pair, interval, limit)

    def fetch_klines(self, pair: str, interval: str, limit: int) -> list[dict]:
        if pair.lower().startswith("chain:"):
            return []

        currency_pair = self._normalize_pair(pair)
        gate_interval = self._to_gate_interval(interval)

        if self._is_mark():
            base_url = f"{self.BASE_URL}/futures/usdt/candlesticks"
            params = {
                "contract": f"mark_{currency_pair}",
                "interval": gate_interval,
                "limit": limit,
            }
        else:
            base_url = f"{self.BASE_URL}/spot/candlesticks"
            params = {
                "currency_pair": currency_pair,
                "interval": gate_interval,
                "limit": limit,
            }

        try:
            response = requests.get(
                base_url,
                params=params,
                proxies=get_proxy_config(),
                timeout=10,
            )
            response.raise_for_status()
            payload = response.json()

            klines: list[dict] = []
            for row in payload:
                parsed = self._parse_candle_row(row)
                if not parsed:
                    continue

                klines.append(parsed)

            klines.sort(key=lambda x: x["timestamp"])
            return klines[-limit:]

        except Exception as e:
            logger.error(f"Failed to fetch Gate klines for {pair}: {e}")
            return []

    @property
    def is_connected(self) -> bool:
        if self._worker is None or not self._worker.isRunning():
            return False
        if hasattr(self._worker, "_last_message_time"):
            return (time.time() - self._worker._last_message_time) < 30
        return False
