import asyncio
import json
import time
import random
import logging
from typing import Optional, List, Set, Dict, Any
from PyQt6.QtCore import QThread, pyqtSignal, QObject
from enum import Enum
import aiohttp

from core.base_client import BaseExchangeClient

# Module-level list to keep dying workers alive until they finish
# This prevents Python GC from destroying them prematurely
_dying_workers: List[QThread] = []

logger = logging.getLogger(__name__)

class ConnectionState(Enum):
    """WebSocket connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


class ReconnectStrategy:
    """Exponential backoff reconnection strategy."""
    def __init__(self, initial_delay: float = 1.0, max_delay: float = 30.0,
                 backoff_factor: float = 2.0, max_retries: Optional[int] = None):
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.max_retries = max_retries
        self.retry_count = 0

    def next_delay(self) -> float:
        if self.retry_count == 0:
            delay = self.initial_delay
        else:
            delay = min(self.initial_delay * (self.backoff_factor ** self.retry_count), self.max_delay)
        
        # Add jitter
        jitter = delay * 0.25 * random.random()
        delay += jitter if random.random() > 0.5 else -jitter
        
        self.retry_count += 1
        return max(delay, self.initial_delay)

    def reset(self):
        self.retry_count = 0

    def should_retry(self) -> bool:
        return self.max_retries is None or self.retry_count < self.max_retries


class BinanceWebSocketWorker(QThread):
    """
    Worker thread for Binance WebSocket connection.
    Uses aiohttp for proxy support via environment variables.
    """
    
    ticker_updated = pyqtSignal(str, dict)
    connection_state_changed = pyqtSignal(str, str, int)
    connection_status = pyqtSignal(bool, str)
    stats_updated = pyqtSignal(dict)

    WS_URL = "wss://stream.binance.com:9443/ws"

    def __init__(self, pairs: List[str], parent: Optional[QObject] = None):
        super().__init__(parent)
        self.pairs = list(pairs)
        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._reconnect_strategy = ReconnectStrategy()
        self._connection_state = ConnectionState.DISCONNECTED
        self._connection_start_time = 0
        self._last_message_time = 0
        self._last_error = ""
        self._total_reconnect_count = 0
        # Map normalized symbol (btcusdt) to display pair (BTC-USDT)
        self._symbol_map: Dict[str, str] = {}
        self._precision_map: Dict[str, int] = {}

    def _update_connection_state(self, state: ConnectionState, message: str = ""):
        self._connection_state = state
        retry_count = self._reconnect_strategy.retry_count if state == ConnectionState.RECONNECTING else 0
        self.connection_state_changed.emit(state.value, message, retry_count)
        is_connected = state in [ConnectionState.CONNECTED, ConnectionState.CONNECTING]
        self.connection_status.emit(is_connected, message)

    def _update_stats(self):
        stats = {
            'state': self._connection_state.value,
            'reconnect_count': self._total_reconnect_count,
            'retry_count': self._reconnect_strategy.retry_count,
            'subscribed_pairs': len(self.pairs),
            'connection_duration': time.time() - self._connection_start_time if self._connection_start_time > 0 else 0,
            'last_message_age': time.time() - self._last_message_time if self._last_message_time > 0 else 0,
            'last_error': self._last_error,
        }
        self.stats_updated.emit(stats)

    async def _maintain_connection(self):
        while self._running:
            try:
                self._update_connection_state(
                    ConnectionState.CONNECTING,
                    f"Connecting to Binance (attempt {self._reconnect_strategy.retry_count + 1})..."
                )
                
                # trust_env=True enables automatic proxy detection from environment variables
                async with aiohttp.ClientSession(trust_env=True) as session:
                    async with session.ws_connect(self.WS_URL) as ws:
                        self._connection_start_time = time.time()
                        self._reconnect_strategy.reset()
                        self._update_connection_state(ConnectionState.CONNECTED, "Connected to Binance")
                        self._total_reconnect_count += 1
                        
                        # refresh symbol map
                        self._symbol_map = {p.replace("-", "").lower(): p for p in self.pairs}
                        
                        # Subscribe
                        streams = [f"{p.replace('-', '').lower()}@ticker" for p in self.pairs]
                        if streams:
                            subscribe_msg = {
                                "method": "SUBSCRIBE",
                                "params": streams,
                                "id": 1
                            }
                            await ws.send_json(subscribe_msg)

                        while self._running:
                            try:
                                msg = await ws.receive(timeout=1.0) # Reduce timeout for responsiveness
                                if msg.type == aiohttp.WSMsgType.TEXT:
                                    self._handle_message(msg.data)
                                elif msg.type == aiohttp.WSMsgType.CLOSED:
                                    break
                                elif msg.type == aiohttp.WSMsgType.ERROR:
                                    break
                            except asyncio.TimeoutError:
                                # Just check _running and loop again
                                continue
                            
            except asyncio.CancelledError:
                raise # Propagate cancellation to run()
            except Exception as e:
                self._last_error = str(e)
                if not self._running:
                    break
                    
                if self._reconnect_strategy.should_retry():
                    self._update_connection_state(ConnectionState.RECONNECTING, f"Connection lost: {e}")
                    delay = self._reconnect_strategy.next_delay()
                    await asyncio.sleep(delay)
                else:
                    self._update_connection_state(ConnectionState.FAILED, f"Max retries exceeded: {e}")
                    raise

    def run(self):
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
            self._update_connection_state(ConnectionState.DISCONNECTED, "Connection cancelled")
        except Exception as e:
            self._last_error = str(e)
            self._update_connection_state(ConnectionState.FAILED, f"Fatal error: {e}")
        finally:
            # Clean up all tasks
            try:
                pending = asyncio.all_tasks(self._loop)
                for task in pending:
                    task.cancel()
                if pending:
                    self._loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                self._loop.close()
            except Exception as e:
                logger.error(f"Loop cleanup error: {e}")
                
            self._update_connection_state(ConnectionState.DISCONNECTED, "Connection closed")

    def stop(self):
        self._running = False
        if self._loop and self._loop.is_running():
            # Schedule cancellation in the event loop thread
            self._loop.call_soon_threadsafe(self._cancel_task_safe)
            
    def _cancel_task_safe(self):
        """Helper to cancel the main task from within the loop."""
        if hasattr(self, '_main_task') and self._main_task:
            self._main_task.cancel()

    def set_precisions(self, precision_map: Dict[str, int]):
        """Update precision map."""
        self._precision_map = precision_map
        
    # ... (skipping to BinanceClient methods)

    def _handle_message(self, message):
        try:
            self._last_message_time = time.time()
            data = json.loads(message)
            
            # Handle Ticker Event
            # {"e": "24hrTicker", "s": "BTCUSDT", "c": "6000.00", "P": "1.2", "h": "...", "l": "...", "q": "..."}
            if data.get('e') == '24hrTicker':
                symbol = data.get('s', '').lower()
                price_str = data.get('c', '0')
                percent_val = data.get('P', '0') # Binance returns formatted percent (e.g. 1.234)
                
                # Format price based on precision
                precision = self._precision_map.get(symbol, 2) # Default to 2 decimals
                try:
                    price_float = float(price_str)
                    price = f"{price_float:.{precision}f}"
                except:
                    price = price_str
                
                # Map back to display pair
                original_pair = self._symbol_map.get(symbol)
                if original_pair:
                    # Format percentage to match app style (+1.23%)
                    try:
                        pct = float(percent_val)
                        formatted_pct = f"+{pct:.2f}%" if pct >= 0 else f"{pct:.2f}%"
                    except:
                        formatted_pct = "0.00%"
                    
                    # Extract extended data
                    high_24h = data.get('h', '0')
                    low_24h = data.get('l', '0')
                    quote_volume = data.get('q', '0')
                    
                    # Format volume slightly for readability (optional, but raw is fine for now, will format in UI or here)
                    # Let's keep it raw string or formatted? UI might want to format. 
                    # But generic "update_data" might expect ready strings.
                    # Let's pass raw-ish strings, maybe round to 2 decimals if floats
                    
                    ticker_data = {
                        "price": price,
                        "percentage": formatted_pct,
                        "high_24h": high_24h,
                        "low_24h": low_24h,
                        "quote_volume_24h": quote_volume,
                        # "volume_24h": data.get('v', '0') # Base volume if needed
                    }

                    self.ticker_updated.emit(original_pair, ticker_data)
            
            self._update_stats()
            
        except Exception as e:
            self._last_error = f"Message error: {e}"


class BinanceClient(BaseExchangeClient):
    """Binance Client implementation."""
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._worker: Optional[BinanceWebSocketWorker] = None
        self._pairs: List[str] = []
        self._precision_map: Dict[str, int] = {} # pair -> decimals
        self._fetch_precisions()

    def _fetch_precisions(self):
        """Fetch symbol precision rules and validate pairs from Binance API."""
        import requests
        from PyQt6.QtCore import QTimer
        
        # Run in background to avoid blocking
        def fetch():
            try:
                # Use request session to allow automatic env proxy usage if requests supports it
                # (requests usually supports env vars by default)
                response = requests.get("https://api.binance.com/api/v3/exchangeInfo", timeout=10)
                data = response.json()
                
                new_map = {}
                valid_symbols = set()
                
                for symbol_info in data.get("symbols", []):
                    symbol = symbol_info.get("symbol", "").lower() # btcusdt
                    valid_symbols.add(symbol)
                    
                    # Find PRICE_FILTER
                    tick_size = "0.01" # Default
                    for filter_item in symbol_info.get("filters", []):
                        if filter_item.get("filterType") == "PRICE_FILTER":
                            tick_size = filter_item.get("tickSize", "0.01")
                            break
                    
                    # Calculate precision from tick size (e.g. 0.001 -> 3)
                    if "." in str(tick_size):
                        precision = len(str(tick_size).rstrip("0").split(".")[1])
                    else:
                        precision = 0
                        
                    new_map[symbol] = precision
                
                # Check if client still exists and is not stopped
                try:
                    if hasattr(self, '_stop_requested') and not self._stop_requested:
                        self._precision_map = new_map
                        
                        # Validate currently configured pairs
                        if self._pairs:
                            invalid_pairs = []
                            for pair in self._pairs:
                                normalized = pair.replace("-", "").lower()
                                if normalized not in valid_symbols:
                                    invalid_pairs.append(pair)
                            
                            if invalid_pairs:
                                logger.warning(f"⚠️  [Binance Warning] The following pairs are not valid or not supported: {', '.join(invalid_pairs)}")
                                logger.warning("    Please check spelling or availability on Binance Spot market.")

                        # If worker is running, update its precision map
                        if self._worker:
                            self._worker.set_precisions(self._precision_map)
                except RuntimeError:
                    # Client might be deleted
                    pass
                    
            except Exception as e:
                logger.error(f"Failed to fetch Binance precisions: {e}")
            finally:
                # Mark as not fetching anymore
                try:
                    if hasattr(self, '_fetching_precisions'):
                        self._fetching_precisions = False
                except RuntimeError:
                    pass
                
        import threading
        threading.Thread(target=fetch, daemon=True).start()

    def _detach_and_stop_worker(self, worker: 'BinanceWebSocketWorker'):
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

    def subscribe(self, pairs: List[str]):
        self._pairs = pairs
        self._restart_worker()

    def _restart_worker(self):
        if self._worker:
            self._detach_and_stop_worker(self._worker)
            
        self._worker = BinanceWebSocketWorker(self._pairs, self)
        self._worker.set_precisions(self._precision_map)
        self._worker.ticker_updated.connect(self.ticker_updated)
        self._worker.connection_status.connect(self.connection_status)
        self._worker.connection_state_changed.connect(self.connection_state_changed)
        self._worker.stats_updated.connect(self.stats_updated)
        self._worker.start()

    def stop(self):
        self._stop_requested = True
        if self._worker:
            self._detach_and_stop_worker(self._worker)
            self._worker = None
        
        # If we have a fetch thread running, we can't easily kill it, 
        # but the flag _stop_requested handled in _fetch_precisions will prevent updates.
        
        self.stopped.emit()

    def reconnect(self):
        if self._pairs:
            self._restart_worker()

    def get_stats(self) -> Optional[Dict[str, Any]]:
        return {}

    def fetch_klines(self, pair: str, interval: str, limit: int = 24) -> List[Dict]:
        """
        Fetch klines from Binance.
        GET /api/v3/klines
        """
        import requests
        
        # Map pair to symbol (e.g. BTC-USDT -> BTCUSDT)
        symbol = pair.replace('-', '').upper()
        
        # Binance intervals: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
        # Our app might use "1h" or similar.
        
        url = "https://api.binance.com/api/v3/klines"
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        
        try:
            # Check for proxy settings from environment or settings
            # Using requests directly here. Ideally we should use a shared session or respect proxy settings.
            # _fetch_precisions uses requests.
            # Let's try to get proxy from settings if possible, or rely on env.
            # For simplicity in this method, let's respect env vars (BinanceWebSocketWorker uses trust_env=True)
            
            # Construct proxies dict if needed. 
            # However, BaseExchangeClient doesn't easily expose settings. 
            # We can import settings here.
            from config.settings import get_settings_manager
            settings = get_settings_manager().settings
            proxies = {}
            if settings.proxy.enabled:
                if settings.proxy.type.lower() == 'http':
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
            
            # Binance response: 
            # [
            #   [
            #     1499040000000,      // Open time
            #     "0.01634790",       // Open
            #     "0.80000000",       // High
            #     "0.01575800",       // Low
            #     "0.01577100",       // Close
            #     ...
            #   ]
            # ]
            
            klines = []
            for item in data:
                klines.append({
                    "timestamp": item[0],
                    "open": float(item[1]),
                    "high": float(item[2]),
                    "low": float(item[3]),
                    "close": float(item[4]),
                    "volume": float(item[5])
                })
            return klines
            
        except Exception as e:
            logger.error(f"Failed to fetch klines for {pair}: {e}")
            return []

    @property
    def is_connected(self) -> bool:
        return self._worker is not None and self._worker.isRunning()
