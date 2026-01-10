"""
Base WebSocket worker for crypto exchanges.
Handles connection management, reconnection logic, and thread lifecycle.
"""

import asyncio
import logging
import time
from abc import abstractmethod
from enum import Enum

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from core.models import TickerData
from core.reconnect_strategy import ReconnectStrategy

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """WebSocket connection states."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


class BaseWebSocketWorker(QThread):
    """
    Base worker thread for WebSocket connections.
    Runs asyncio event loop in a separate thread.
    Handles automatic reconnection and signal emission.
    """

    # Signals
    ticker_updated = pyqtSignal(str, TickerData)  # pair, TickerData object
    connection_error = pyqtSignal(str, str)  # pair, error_message
    connection_status = pyqtSignal(bool, str)  # connected, message
    connection_state_changed = pyqtSignal(str, str, int)  # state, message, retry_count
    stats_updated = pyqtSignal(dict)  # connection statistics
    klines_ready = pyqtSignal(str, list)

    def __init__(self, pairs: list[str], parent: QObject | None = None):
        super().__init__(parent)
        self.pairs = list(pairs)  # Store initial pairs
        self._running = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self._reconnect_strategy = ReconnectStrategy()
        self._connection_state = ConnectionState.DISCONNECTED
        self._subscribed_pairs: set[str] = set()
        self._last_message_time = 0
        self._connection_start_time = 0
        self._total_reconnect_count = 0
        self._last_error = ""
        self._connection_timeout = 60  # seconds
        self._ping_interval = 20  # seconds
        self._main_task = None

    def _update_connection_state(self, state: ConnectionState, message: str = ""):
        """Update connection state and emit signals."""
        self._connection_state = state
        retry_count = (
            self._reconnect_strategy.retry_count if state == ConnectionState.RECONNECTING else 0
        )
        self.connection_state_changed.emit(state.value, message, retry_count)

        # Emit old-style signal for backward compatibility
        is_connected = state in [ConnectionState.CONNECTED, ConnectionState.CONNECTING]
        self.connection_status.emit(is_connected, message)

    def _update_stats(self):
        """Update connection statistics."""
        stats = {
            "state": self._connection_state.value,
            "reconnect_count": self._total_reconnect_count,
            "retry_count": self._reconnect_strategy.retry_count,
            "subscribed_pairs": len(self._subscribed_pairs),
            "connection_duration": time.time() - self._connection_start_time
            if self._connection_start_time > 0
            else 0,
            "last_message_age": time.time() - self._last_message_time
            if self._last_message_time > 0
            else 0,
            "last_error": self._last_error,
        }
        self.stats_updated.emit(stats)

    def run(self):
        """Run the WebSocket client in asyncio event loop with auto-reconnect."""
        logger.info(
            f"[{self.__class__.__name__}] Starting run loop "
            f"(Thread: {int(QThread.currentThreadId())})"
        )
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
            logger.info(f"[{self.__class__.__name__}] Main task cancelled")
            self._update_connection_state(ConnectionState.DISCONNECTED, "Connection cancelled")
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Fatal error: {e}", exc_info=True)
            self._last_error = str(e)
            self._update_connection_state(ConnectionState.FAILED, f"Fatal error: {e}")
        finally:
            logger.info(f"[{self.__class__.__name__}] Cleaning up loop...")
            # Clean up all tasks
            try:
                pending = asyncio.all_tasks(self._loop)
                for task in pending:
                    task.cancel()
                if pending:
                    self._loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                self._loop.close()
                logger.info(f"[{self.__class__.__name__}] Loop closed.")
            except Exception as e:
                logger.error(f"Loop cleanup error: {e}")

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
                    ConnectionState.CONNECTING
                    if self._reconnect_strategy.retry_count > 0
                    else ConnectionState.CONNECTING,
                    f"Connecting... (attempt {self._reconnect_strategy.retry_count + 1})",
                )

                await self._connect_and_subscribe()
                # If we reach here, connection was successful
                self._reconnect_strategy.reset()
                self._update_connection_state(ConnectionState.CONNECTED, "Connected")
                self._update_stats()

                # Keep connection alive with periodic checks
                last_ping_time = time.time()

                while self._running:
                    await asyncio.sleep(1)

                    # 1. Update subscriptions (Thread-safe copy)
                    # Create a copy to avoid modification during iteration
                    current_pairs = list(self.pairs)
                    if set(current_pairs) != self._subscribed_pairs:
                        await self._update_subscriptions()

                    # 2. Send active ping
                    if time.time() - last_ping_time > self._ping_interval:
                        await self._send_ping()
                        last_ping_time = time.time()

                    # 3. Check heartbeat (Zombie detection)
                    if self._last_message_time > 0:
                        time_since_last = time.time() - self._last_message_time
                        if time_since_last > self._connection_timeout:
                            self._last_error = f"Heartbeat timeout: {time_since_last:.1f}s"
                            self._update_connection_state(
                                ConnectionState.RECONNECTING,
                                f"Heartbeat timeout after {time_since_last:.1f}s, reconnecting...",
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
                    self._update_connection_state(
                        ConnectionState.FAILED, f"Max retries exceeded: {e}"
                    )
                    raise

    async def _send_ping(self):
        """
        Send a ping message to keep the connection alive.
        Subclasses can override this to implement protocol-specific pings.
        """
        pass

    @abstractmethod
    async def _connect_and_subscribe(self):
        """
        Connect to WebSocket and subscribe to ticker channels.
        Must be implemented by subclasses.
        """
        pass

    @abstractmethod
    async def _update_subscriptions(self):
        """
        Update subscriptions incrementally (only changed pairs).
        Must be implemented by subclasses.
        """
        pass

    async def fetch_klines_async(self, pair: str, interval: str, limit: int):
        """
        Fetch klines asynchronously.
        Base implementation does nothing. Subclasses should override.
        """
        pass

    def request_klines(self, pair: str, interval: str, limit: int):
        """Schedule an async kline fetch task in the event loop."""
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self.fetch_klines_async(pair, interval, limit), self._loop
            )

    def stop(self):
        """Stop the WebSocket connection."""
        self._running = False
        if self._loop and self._loop.is_running():
            # Thread-safe cancellation
            self._loop.call_soon_threadsafe(self._cancel_task_safe)

    def _cancel_task_safe(self):
        """Helper to cancel the main task from within the loop."""
        if hasattr(self, "_main_task") and self._main_task:
            self._main_task.cancel()
