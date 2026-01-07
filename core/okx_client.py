"""
OKX WebSocket client for real-time ticker data.
Uses python-okx library with PyQt signal integration.
Enhanced with automatic reconnection and incremental subscription.
"""

import asyncio
import json
import time
import random
from typing import Optional, Callable, Set, Dict, Any
from PyQt6.QtCore import QObject, QThread, pyqtSignal, QTimer
from enum import Enum

try:
    from okx.websocket.WsPublicAsync import WsPublicAsync
except ImportError:
    WsPublicAsync = None

# Module-level list to keep dying workers alive until they finish
_dying_workers = []


class ConnectionState(Enum):
    """WebSocket connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


class ReconnectStrategy:
    """
    Exponential backoff reconnection strategy.
    Implements jitter to prevent thundering herd problem.
    """

    def __init__(self, initial_delay: float = 1.0, max_delay: float = 30.0,
                 backoff_factor: float = 2.0, max_retries: Optional[int] = None):
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.max_retries = max_retries
        self.retry_count = 0

    def next_delay(self) -> float:
        """Get the next retry delay with exponential backoff and jitter."""
        if self.retry_count == 0:
            delay = self.initial_delay
        else:
            delay = min(
                self.initial_delay * (self.backoff_factor ** self.retry_count),
                self.max_delay
            )

        # Add jitter (±25% random variation)
        jitter = delay * 0.25 * random.random()
        delay += jitter if random.random() > 0.5 else -jitter

        self.retry_count += 1
        return max(delay, self.initial_delay)

    def reset(self):
        """Reset retry counter."""
        self.retry_count = 0

    def should_retry(self) -> bool:
        """Check if retry attempts are still within limits."""
        if self.max_retries is None:
            return True
        return self.retry_count < self.max_retries


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
    Enhanced with automatic reconnection and incremental subscription.
    """

    # Signals
    ticker_updated = pyqtSignal(str, str, str)  # pair, price, percentage
    connection_error = pyqtSignal(str, str)  # pair, error_message
    connection_status = pyqtSignal(bool, str)  # connected, message
    connection_state_changed = pyqtSignal(str, str, int)  # state, message, retry_count
    stats_updated = pyqtSignal(dict)  # connection statistics

    # OKX WebSocket URL
    WS_PUBLIC_URL = "wss://ws.okx.com:8443/ws/v5/public"

    def __init__(self, pairs: list[str], parent: Optional[QObject] = None):
        super().__init__(parent)
        self.pairs = list(pairs)  # Store initial pairs
        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._ws_client: Optional[WsPublicAsync] = None
        self._reconnect_strategy = ReconnectStrategy()
        self._connection_state = ConnectionState.DISCONNECTED
        self._subscribed_pairs: Set[str] = set()
        self._last_message_time = 0
        self._connection_start_time = 0
        self._total_reconnect_count = 0
        self._last_error = ""
        self._heartbeat_interval = 30  # seconds
        self._connection_timeout = 60  # seconds

    def _update_connection_state(self, state: ConnectionState, message: str = ""):
        """Update connection state and emit signals."""
        self._connection_state = state
        retry_count = self._reconnect_strategy.retry_count if state == ConnectionState.RECONNECTING else 0
        self.connection_state_changed.emit(state.value, message, retry_count)

        # Emit old-style signal for backward compatibility
        is_connected = state in [ConnectionState.CONNECTED, ConnectionState.CONNECTING]
        self.connection_status.emit(is_connected, message)

    def _update_stats(self):
        """Update connection statistics."""
        stats = {
            'state': self._connection_state.value,
            'reconnect_count': self._total_reconnect_count,
            'retry_count': self._reconnect_strategy.retry_count,
            'subscribed_pairs': len(self._subscribed_pairs),
            'connection_duration': time.time() - self._connection_start_time if self._connection_start_time > 0 else 0,
            'last_message_age': time.time() - self._last_message_time if self._last_message_time > 0 else 0,
            'last_error': self._last_error,
        }
        self.stats_updated.emit(stats)

    def run(self):
        """Run the WebSocket client in asyncio event loop with auto-reconnect."""
        print(f"[OkxWorker] Starting run loop (Thread: {int(QThread.currentThreadId())})")
        self._running = True
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        self._update_connection_state(ConnectionState.CONNECTING, "Initializing connection...")
        self._reconnect_strategy.reset()

        try:
            # Store task reference for cancellation
            self._main_task = self._loop.create_task(self._maintain_connection())
            self._loop.run_until_complete(self._main_task)
        except asyncio.CancelledError:
            print("[OkxWorker] Main task cancelled")
            self._update_connection_state(ConnectionState.DISCONNECTED, "Connection cancelled")
        except Exception as e:
            print(f"[OkxWorker] Fatal error: {e}")
            self._last_error = str(e)
            self._update_connection_state(ConnectionState.FAILED, f"Fatal error: {e}")
        finally:
            print("[OkxWorker] Cleaning up loop...")
            # Clean up all tasks
            try:
                pending = asyncio.all_tasks(self._loop)
                for task in pending:
                    task.cancel()
                if pending:
                    self._loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                self._loop.close()
                print("[OkxWorker] Loop closed.")
            except Exception as e:
                print(f"OKX Loop cleanup error: {e}")
                
            self._update_connection_state(ConnectionState.DISCONNECTED, "Connection closed")

    async def _maintain_connection(self):
        """
        Maintain WebSocket connection with automatic reconnection.
        Uses exponential backoff strategy for reconnection attempts.
        """
        while self._running:
            try:
                # Attempt to connect
                self._update_connection_state(
                    ConnectionState.CONNECTING if self._reconnect_strategy.retry_count > 0 else ConnectionState.CONNECTING,
                    f"Connecting to OKX (attempt {self._reconnect_strategy.retry_count + 1})..."
                )

                await self._connect_and_subscribe()
                # If we reach here, connection was successful
                self._reconnect_strategy.reset()
                self._update_connection_state(ConnectionState.CONNECTED, "Connected to OKX")
                self._update_stats()

                # Keep connection alive with periodic checks
                while self._running:
                    await asyncio.sleep(1)

                    # Check if we need to update subscriptions (incremental changes)
                    if set(self.pairs) != self._subscribed_pairs:
                        await self._update_subscriptions()

                    # Check heartbeat - if no message received for too long, reconnect
                    if self._last_message_time > 0:
                        time_since_last = time.time() - self._last_message_time
                        if time_since_last > self._connection_timeout:
                            self._last_error = f"Heartbeat timeout: {time_since_last:.1f}s"
                            self._update_connection_state(
                                ConnectionState.RECONNECTING,
                                f"Heartbeat timeout after {time_since_last:.1f}s, reconnecting..."
                            )
                            break

            except asyncio.CancelledError:
                raise  # Propagate cancellation to run()
            except Exception as e:
                self._last_error = str(e)
                error_msg = f"Connection failed: {e}"

                # Check if we should retry
                if self._reconnect_strategy.should_retry():
                    self._update_connection_state(ConnectionState.RECONNECTING, error_msg)
                    self._total_reconnect_count += 1

                    delay = self._reconnect_strategy.next_delay()
                    await asyncio.sleep(delay)
                else:
                    self._update_connection_state(ConnectionState.FAILED, f"Max retries exceeded: {e}")
                    raise

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
                    "args": [{"channel": "tickers", "instId": pair} for pair in current_pairs]
                }
                await self._ws_client.send(json.dumps(subscribe_msg))
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
            # Update last message time for heartbeat detection
            self._last_message_time = time.time()

            if isinstance(message, str):
                data = json.loads(message)
            elif isinstance(message, bytes):
                data = json.loads(message.decode('utf-8'))
            else:
                data = message

            # Update statistics
            self._update_stats()

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
            self._last_error = f"Message handling error: {e}"
            print(f"Error handling message: {e}")
            self._update_stats()

    def stop(self):
        """Stop the WebSocket connection."""
        self._running = False
        if self._loop and self._loop.is_running():
            # Thread-safe cancellation
            self._loop.call_soon_threadsafe(self._cancel_task_safe)
            
    def _cancel_task_safe(self):
        """Helper to cancel the main task from within the loop."""
        if hasattr(self, '_main_task') and self._main_task:
            self._main_task.cancel()

    def update_pairs(self, pairs: list[str]):
        """Update subscription pairs (requires reconnection)."""
        self.pairs = pairs


from core.base_client import BaseExchangeClient

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

    ticker_updated = pyqtSignal(str, str, str)  # pair, price, percentage
    connection_status = pyqtSignal(bool, str)  # connected, message
    connection_state_changed = pyqtSignal(str, str, int)  # state, message, retry_count
    stats_updated = pyqtSignal(dict)  # connection statistics

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._worker: Optional[OkxWebSocketWorker] = None
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

    def get_stats(self) -> Optional[Dict[str, Any]]:
        """Get current connection statistics."""
        if self._worker is not None:
            return {
                'state': self._worker._connection_state.value if hasattr(self._worker, '_connection_state') else 'unknown',
                'subscribed_pairs': len(self._pairs),
                'worker_running': self._worker.isRunning(),
            }
        return None

    @property
    def is_connected(self) -> bool:
        """Check if currently connected and receiving data."""
        if self._worker is None or not self._worker.isRunning():
            return False

        # Check if we have a recent message (within last 30 seconds)
        if hasattr(self._worker, '_last_message_time'):
            import time
            return (time.time() - self._worker._last_message_time) < 30

        return False
