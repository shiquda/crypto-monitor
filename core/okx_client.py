"""
OKX WebSocket client for real-time ticker data.
Uses python-okx library with PyQt signal integration.
Enhanced with automatic reconnection and incremental subscription.
"""

import json
import logging
import time
from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal

try:
    from okx.websocket.WsPublicAsync import WsPublicAsync
except ImportError:
    WsPublicAsync = None

# Module-level list to keep dying workers alive until they finish
_dying_workers = []

logger = logging.getLogger(__name__)

from core.base_client import BaseExchangeClient
from core.websocket_worker import BaseWebSocketWorker


class TickerData:
    """Ticker data container."""

    def __init__(self, pair: str, price: str, percentage: str):
        self.pair = pair
        self.price = price
        self.percentage = percentage


class OkxWebSocketWorker(BaseWebSocketWorker):
    """
    Worker thread for OKX WebSocket connection.
    Runs asyncio event loop in a separate thread.
    Enhanced with automatic reconnection and incremental subscription.
    """

    # OKX WebSocket URL
    WS_PUBLIC_URL = "wss://ws.okx.com:8443/ws/v5/public"

    def __init__(self, pairs: list[str], parent: QObject | None = None):
        super().__init__(pairs, parent)
        self._ws_client: WsPublicAsync | None = None
        self._heartbeat_interval = 30  # seconds

    async def _connect_and_subscribe(self):
        """Connect to OKX WebSocket and subscribe to ticker channels."""
        if WsPublicAsync is None:
            # Fallback: use simple websocket implementation
            await self._simple_websocket_subscribe()
            return

        try:
            self._ws_client = WsPublicAsync(self.WS_PUBLIC_URL)
            await self._ws_client.start()
            self._connection_start_time = time.time()

            # Subscribe to current pairs
            await self._update_subscriptions()

        except Exception as e:
            self._last_error = str(e)
            raise

    async def _update_subscriptions(self):
        """Update subscriptions incrementally (only changed pairs)."""
        current_pairs = set(self.pairs)
        new_pairs = current_pairs - self._subscribed_pairs
        removed_pairs = self._subscribed_pairs - current_pairs

        if WsPublicAsync is None:
            # Simple websocket implementation
            if new_pairs or not self._subscribed_pairs:
                subscribe_msg = {
                    "op": "subscribe",
                    "args": [{"channel": "tickers", "instId": pair} for pair in current_pairs],
                }
                if self._ws_client:  # Should be valid in simple mode too? distinct var?
                    # In simple mode we don't have self._ws_client as WsPublicAsync
                    # logic in _simple_websocket_subscribe handles subscription sending.
                    pass
            return

        # Subscribe to new pairs
        if new_pairs:
            args = [{"channel": "tickers", "instId": pair} for pair in new_pairs]
            await self._ws_client.subscribe(args, self._handle_message)

        # Unsubscribe from removed pairs
        if removed_pairs:
            args = [{"channel": "tickers", "instId": pair} for pair in removed_pairs]
            try:
                await self._ws_client.unsubscribe(args)
            except:
                # If unsubscribe fails, just ignore - will be cleaned up on reconnect
                pass

        # Update tracking
        self._subscribed_pairs = current_pairs
        self._update_stats()

    async def _simple_websocket_subscribe(self):
        """Simple WebSocket implementation without python-okx dependency."""
        import websockets

        try:
            async with websockets.connect(self.WS_PUBLIC_URL) as ws:
                self.connection_status.emit(True, "Connected to OKX")

                # We need to expose ws for update_subscriptions?
                # The original simplified implementation didn't support incremental updates fully inside simple mode gracefully
                # or it re-sent list.
                # Original logic:
                # subscribe_msg = ...
                # await ws.send(...)
                # while self._running: ...

                # To support incremental updates here we'd need more complex logic.
                # For refactoring, I should preserve original behavior.
                # Original behavior:
                # Just subscribed once at start.

                subscribe_msg = {
                    "op": "subscribe",
                    "args": [{"channel": "tickers", "instId": pair} for pair in self.pairs],
                }
                await ws.send(json.dumps(subscribe_msg))

                # Listen for messages
                while self._running:
                    try:
                        message = await asyncio.wait_for(ws.recv(), timeout=1.0)
                        self._handle_message(message)
                    except asyncio.TimeoutError:
                        continue
                    except websockets.exceptions.ConnectionClosed:
                        self.connection_status.emit(False, "Connection closed")
                        break

        except Exception as e:
            self.connection_status.emit(False, f"WebSocket error: {e}")

    def _handle_message(self, message):
        """Handle incoming WebSocket message."""
        try:
            # Update last message time for heartbeat detection
            self._last_message_time = time.time()

            if isinstance(message, str):
                data = json.loads(message)
            elif isinstance(message, bytes):
                data = json.loads(message.decode("utf-8"))
            else:
                data = message

            # Update statistics
            self._update_stats()

            # Skip non-data messages (like subscription confirmations)
            if "data" not in data:
                return

            for ticker in data.get("data", []):
                pair = ticker.get("instId", "")
                last_price = ticker.get("last", "0")
                sod_utc0 = ticker.get("sodUtc0", "0")

                # Calculate percentage
                try:
                    from config.settings import get_settings_manager

                    settings = get_settings_manager().settings
                    basis = settings.price_change_basis

                    last = float(last_price)

                    if basis == "utc_0":
                        open_price = float(sod_utc0)
                    else:
                        # For 24h rolling, we need open24h.
                        # open24h is explicitly available in OKX ticker channel as 'open24h'
                        open_price_str = ticker.get("open24h", "0")
                        open_price = float(open_price_str)

                    if open_price > 0:
                        pct = (last - open_price) / open_price * 100
                        percentage = f"+{pct:.2f}%" if pct >= 0 else f"{pct:.2f}%"
                    else:
                        percentage = "0.00%"
                except (ValueError, ZeroDivisionError):
                    percentage = "0.00%"

                # Extract extended data
                high_24h = ticker.get("high24h", "0")
                low_24h = ticker.get("low24h", "0")
                quote_volume = ticker.get("volCcy24h", "0")

                ticker_data = {
                    "price": last_price,
                    "percentage": percentage,
                    "high_24h": high_24h,
                    "low_24h": low_24h,
                    "quote_volume_24h": quote_volume,
                }

                # Emit signal (thread-safe)
                self.ticker_updated.emit(pair, ticker_data)

        except json.JSONDecodeError:
            pass
        except Exception as e:
            self._last_error = f"Message handling error: {e}"
            logger.error(f"Error handling message: {e}")
            self._update_stats()

    def update_pairs(self, pairs: list[str]):
        """Update subscription pairs (requires reconnection or incremental)."""
        self.pairs = pairs
        # Base class handles reconnection logic if needed via main loop,
        # but here we rely on _maintain_connection loop checking for differences.
        # Original: _maintain_connection loop checks:
        # if set(self.pairs) != self._subscribed_pairs: await self._update_subscriptions()
        # This logic is now in BaseWebSocketWorker.


class OkxClientManager(BaseExchangeClient):
    """
    Manages OKX WebSocket connections.
    Handles multiple subscriptions and reconnection with automatic retry.

    Key features:
    - Automatic reconnection with exponential backoff
    - Incremental subscription updates (no full reconnect needed)
    - Connection health monitoring
    - Detailed connection statistics
    """

    ticker_updated = pyqtSignal(str, dict)  # pair, data_dict
    connection_status = pyqtSignal(bool, str)  # connected, message
    connection_state_changed = pyqtSignal(str, str, int)  # state, message, retry_count
    stats_updated = pyqtSignal(dict)  # connection statistics

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._worker: OkxWebSocketWorker | None = None
        self._pairs: list[str] = []

    def _detach_and_stop_worker(self, worker: OkxWebSocketWorker):
        """
        Safely detach and stop a worker thread.
        Orphans the worker so it isn't destroyed if the parent client is deleted.
        """
        if not worker:
            return

        # CRITICAL: Remove parent before moving to module-level list
        worker.setParent(None)

        # Keep worker alive in module-level list until it finishes
        if worker.isRunning():
            _dying_workers.append(worker)

            def cleanup():
                if worker in _dying_workers:
                    try:
                        _dying_workers.remove(worker)
                    except ValueError:
                        pass
                worker.deleteLater()

            worker.finished.connect(cleanup)
            worker.stop()
        else:
            worker.deleteLater()

    def subscribe(self, pairs: list[str]):
        """
        Subscribe to ticker updates for given pairs.

        Uses incremental updates - only new/removed pairs cause subscription changes.
        Existing connections remain active.
        """
        pairs = list(pairs)  # Make a copy

        # If we have an active worker, update incrementally
        if self._worker is not None and self._worker.isRunning():
            # Just update the pairs list and signal the worker
            old_pairs = set(self._worker.pairs)
            new_pairs = set(pairs)

            # Check if it's just a change in pairs
            if old_pairs != new_pairs:
                # Update worker's pairs list
                self._worker.pairs = pairs
                # Worker will detect the change and update subscriptions incrementally

            self._pairs = pairs
            return

        # No active worker - create a new one
        self._create_worker(pairs)

    def _create_worker(self, pairs: list[str]):
        """Create a new WebSocket worker."""
        # Stop any existing worker first
        if self._worker is not None:
            self._detach_and_stop_worker(self._worker)

        self._pairs = pairs
        self._worker = OkxWebSocketWorker(pairs, self)

        # Connect signals
        self._worker.ticker_updated.connect(self.ticker_updated)
        self._worker.connection_status.connect(self.connection_status)
        self._worker.connection_state_changed.connect(self.connection_state_changed)
        self._worker.stats_updated.connect(self.stats_updated)

        # Start the worker
        self._worker.start()

    def add_pair(self, pair: str):
        """Add a new pair to subscription (incremental update)."""
        pair = pair.upper()
        if pair not in self._pairs:
            self._pairs.append(pair)
            if self._worker is not None and self._worker.isRunning():
                # Incremental update - no full reconnect
                self._worker.pairs = list(self._pairs)
            else:
                # No active worker, create one
                self._create_worker(self._pairs)

    def remove_pair(self, pair: str):
        """Remove a pair from subscription (incremental update)."""
        pair = pair.upper()
        if pair in self._pairs:
            self._pairs.remove(pair)
            if self._worker is not None and self._worker.isRunning():
                # Incremental update - no full reconnect
                self._worker.pairs = list(self._pairs)
                # If no more pairs, stop the worker
                if not self._pairs:
                    self.stop()
            else:
                if self._pairs:
                    self._create_worker(self._pairs)
                else:
                    self.stop()

    def stop(self):
        """Stop all connections."""
        if self._worker:
            self._detach_and_stop_worker(self._worker)
            self._worker = None
        self.stopped.emit()

    def reconnect(self):
        """Force reconnect with current pairs (for manual recovery)."""
        if self._pairs:
            self._create_worker(self._pairs)

    def get_stats(self) -> dict[str, Any] | None:
        """Get current connection statistics."""
        if self._worker is not None:
            # Safely access _connection_state from base worker
            state = "unknown"
            if hasattr(self._worker, "_connection_state"):
                state = self._worker._connection_state.value

            return {
                "state": state,
                "subscribed_pairs": len(self._pairs),
                "worker_running": self._worker.isRunning(),
            }
        return None

    def fetch_klines(self, pair: str, interval: str, limit: int = 24) -> list[dict]:
        """
        Fetch klines from OKX.
        GET /api/v5/market/candles
        """
        import requests

        okx_interval = interval
        if interval.lower() == "1h":
            okx_interval = "1H"
        elif interval.lower() == "4h":
            okx_interval = "4H"
        elif interval.lower() == "1d":
            okx_interval = "1D"

        url = "https://www.okx.com/api/v5/market/candles"
        params = {"instId": pair, "bar": okx_interval, "limit": limit}

        try:
            # Construct proxies dict if needed.
            from config.settings import get_settings_manager

            settings = get_settings_manager().settings
            proxies = {}
            if settings.proxy.enabled:
                if settings.proxy.type.lower() == "http":
                    proxy_url = f"http://{settings.proxy.host}:{settings.proxy.port}"
                    if settings.proxy.username:
                        proxy_url = f"http://{settings.proxy.username}:{settings.proxy.password}@{settings.proxy.host}:{settings.proxy.port}"
                    proxies = {"http": proxy_url, "https": proxy_url}
                else:
                    # SOCKS5
                    proxy_url = f"socks5://{settings.proxy.host}:{settings.proxy.port}"
                    if settings.proxy.username:
                        proxy_url = f"socks5://{settings.proxy.username}:{settings.proxy.password}@{settings.proxy.host}:{settings.proxy.port}"
                    proxies = {"http": proxy_url, "https": proxy_url}

            response = requests.get(url, params=params, proxies=proxies, timeout=5)
            response.raise_for_status()
            data = response.json()

            klines = []
            if data.get("code") == "0":
                raw_data = data.get("data", [])
                for item in reversed(raw_data):
                    klines.append(
                        {
                            "timestamp": int(item[0]),
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
        """Check if currently connected and receiving data."""
        if self._worker is None or not self._worker.isRunning():
            return False

        # Check if we have a recent message (within last 30 seconds)
        if hasattr(self._worker, "_last_message_time"):
            import time

            return (time.time() - self._worker._last_message_time) < 30

        return False
