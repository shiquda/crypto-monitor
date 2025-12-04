"""
OKX WebSocket client for real-time ticker data.
Uses python-okx library with PyQt signal integration.
"""

import asyncio
import json
from typing import Optional, Callable
from PyQt6.QtCore import QObject, QThread, pyqtSignal

# Import OKX WebSocket
try:
    from okx.websocket.WsPublicAsync import WsPublicAsync
except ImportError:
    WsPublicAsync = None


class TickerData:
    """Ticker data container."""

    def __init__(self, pair: str, price: str, percentage: str):
        self.pair = pair
        self.price = price
        self.percentage = percentage


class OkxWebSocketWorker(QThread):
    """
    Worker thread for OKX WebSocket connection.
    Runs asyncio event loop in a separate thread.
    """

    # Signals
    ticker_updated = pyqtSignal(str, str, str)  # pair, price, percentage
    connection_error = pyqtSignal(str, str)  # pair, error_message
    connection_status = pyqtSignal(bool, str)  # connected, message

    # OKX WebSocket URL
    WS_PUBLIC_URL = "wss://ws.okx.com:8443/ws/v5/public"

    def __init__(self, pairs: list[str], parent: Optional[QObject] = None):
        super().__init__(parent)
        self.pairs = pairs
        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._ws_client: Optional[WsPublicAsync] = None

    def run(self):
        """Run the WebSocket client in asyncio event loop."""
        self._running = True
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        try:
            self._loop.run_until_complete(self._connect_and_subscribe())
        except Exception as e:
            self.connection_status.emit(False, f"Connection error: {e}")
        finally:
            self._loop.close()

    async def _connect_and_subscribe(self):
        """Connect to OKX WebSocket and subscribe to ticker channels."""
        if WsPublicAsync is None:
            # Fallback: use simple websocket implementation
            await self._simple_websocket_subscribe()
            return

        try:
            self._ws_client = WsPublicAsync(self.WS_PUBLIC_URL)
            await self._ws_client.start()

            # Build subscription args for tickers
            args = [{"channel": "tickers", "instId": pair} for pair in self.pairs]

            await self._ws_client.subscribe(args, self._handle_message)
            self.connection_status.emit(True, "Connected to OKX")

            # Keep running until stopped
            while self._running:
                await asyncio.sleep(0.1)

        except Exception as e:
            self.connection_status.emit(False, str(e))

    async def _simple_websocket_subscribe(self):
        """Simple WebSocket implementation without python-okx dependency."""
        import websockets

        try:
            async with websockets.connect(self.WS_PUBLIC_URL) as ws:
                self.connection_status.emit(True, "Connected to OKX")

                # Subscribe to tickers
                subscribe_msg = {
                    "op": "subscribe",
                    "args": [{"channel": "tickers", "instId": pair} for pair in self.pairs]
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
            if isinstance(message, str):
                data = json.loads(message)
            elif isinstance(message, bytes):
                data = json.loads(message.decode('utf-8'))
            else:
                data = message

            # Skip non-data messages (like subscription confirmations)
            if 'data' not in data:
                return

            for ticker in data.get('data', []):
                pair = ticker.get('instId', '')
                last_price = ticker.get('last', '0')
                sod_utc0 = ticker.get('sodUtc0', '0')

                # Calculate percentage
                try:
                    last = float(last_price)
                    sod = float(sod_utc0)
                    if sod > 0:
                        pct = (last - sod) / sod * 100
                        percentage = f"+{pct:.2f}%" if pct >= 0 else f"{pct:.2f}%"
                    else:
                        percentage = "0.00%"
                except (ValueError, ZeroDivisionError):
                    percentage = "0.00%"

                # Emit signal (thread-safe)
                self.ticker_updated.emit(pair, last_price, percentage)

        except json.JSONDecodeError:
            pass
        except Exception as e:
            print(f"Error handling message: {e}")

    def stop(self):
        """Stop the WebSocket connection."""
        self._running = False
        self.wait(5000)  # Wait max 5 seconds to avoid blocking UI

    def update_pairs(self, pairs: list[str]):
        """Update subscription pairs (requires reconnection)."""
        self.pairs = pairs


class OkxClientManager(QObject):
    """
    Manages OKX WebSocket connections.
    Handles multiple subscriptions and reconnection.
    """

    ticker_updated = pyqtSignal(str, str, str)  # pair, price, percentage
    connection_status = pyqtSignal(bool, str)  # connected, message

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._worker: Optional[OkxWebSocketWorker] = None
        self._pairs: list[str] = []

    def subscribe(self, pairs: list[str]):
        """Subscribe to ticker updates for given pairs."""
        self._pairs = pairs

        # Stop existing worker if any
        if self._worker is not None:
            # Signal the worker to stop
            self._worker._running = False

            # Store old worker reference
            old_worker = self._worker
            self._worker = None

            # Wait for thread to finish in background using QTimer
            from PyQt6.QtCore import QTimer

            def check_and_cleanup():
                if old_worker.isRunning():
                    # Still running, check again in 100ms
                    QTimer.singleShot(100, check_and_cleanup)
                else:
                    # Thread finished, safe to delete
                    old_worker.deleteLater()

            # Start checking after 100ms
            QTimer.singleShot(100, check_and_cleanup)

        # Create new worker immediately (don't wait for old one)
        self._worker = OkxWebSocketWorker(pairs, self)
        self._worker.ticker_updated.connect(self.ticker_updated)
        self._worker.connection_status.connect(self.connection_status)
        self._worker.start()

    def add_pair(self, pair: str):
        """Add a new pair to subscription."""
        if pair not in self._pairs:
            self._pairs.append(pair)
            self.subscribe(self._pairs)

    def remove_pair(self, pair: str):
        """Remove a pair from subscription."""
        if pair in self._pairs:
            self._pairs.remove(pair)
            if self._pairs:
                self.subscribe(self._pairs)
            else:
                self.stop()

    def stop(self):
        """Stop all connections."""
        if self._worker is not None:
            self._worker.stop()
            self._worker = None

    def reconnect(self):
        """Reconnect with current pairs."""
        if self._pairs:
            self.subscribe(self._pairs)
