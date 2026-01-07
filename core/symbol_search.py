"""
Symbol Search Service for cryptocurrency trading pairs.
Fetches and caches available trading pairs from exchange APIs,
provides search functionality with prefix and fuzzy matching.
"""

import logging
import threading
from dataclasses import dataclass
from typing import List, Optional, Dict, Set
from PyQt6.QtCore import QObject, pyqtSignal

import requests

logger = logging.getLogger(__name__)


@dataclass
class SymbolInfo:
    """Trading pair information."""
    symbol: str        # Formatted symbol, e.g., "BTC-USDT"
    raw_symbol: str    # Original symbol, e.g., "BTCUSDT"
    base_asset: str    # Base asset, e.g., "BTC"
    quote_asset: str   # Quote asset, e.g., "USDT"

    def matches(self, query: str) -> bool:
        """Check if this symbol matches the search query."""
        query = query.upper().strip()
        if not query:
            return True
        
        # Direct match
        if query in self.symbol or query in self.raw_symbol:
            return True
        
        # Base/Quote asset match
        if query in self.base_asset or query in self.quote_asset:
            return True
        
        # Prefix match on formatted symbol without dash
        symbol_no_dash = self.symbol.replace("-", "")
        if symbol_no_dash.startswith(query) or query.replace("-", "") in symbol_no_dash:
            return True
        
        return False

    def match_score(self, query: str) -> int:
        """
        Calculate match score for ranking results.
        Higher score = better match.
        """
        query = query.upper().strip()
        if not query:
            return 0
        
        # Exact match gets highest score
        if self.symbol == query or self.raw_symbol == query:
            return 100
        
        # Base asset exact match
        if self.base_asset == query:
            return 90
        
        # Symbol starts with query
        if self.symbol.startswith(query) or self.raw_symbol.startswith(query):
            return 80
        
        # Base asset starts with query
        if self.base_asset.startswith(query):
            return 70
        
        # Query in base asset
        if query in self.base_asset:
            return 50
        
        # Query in symbol
        if query in self.symbol or query in self.raw_symbol:
            return 30
        
        # Query in quote asset
        if query in self.quote_asset:
            return 10
        
        return 0


class SymbolSearchService(QObject):
    """
    Trading pair search service.
    Loads and caches symbols from exchange APIs, provides search functionality.
    """

    # Signals
    symbols_loaded = pyqtSignal(list)  # Emits list of SymbolInfo on successful load
    loading_started = pyqtSignal()     # Emits when loading starts
    loading_error = pyqtSignal(str)    # Emits error message on failure

    # API endpoints
    BINANCE_API = "https://api.binance.com/api/v3/exchangeInfo"
    OKX_API = "https://www.okx.com/api/v5/public/instruments"

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._symbols: List[SymbolInfo] = []
        self._symbol_set: Set[str] = set()  # For fast validation
        self._current_source: str = ""
        self._loading: bool = False
        self._lock = threading.Lock()

    @property
    def is_loading(self) -> bool:
        """Check if symbols are currently being loaded."""
        return self._loading

    @property
    def symbols_count(self) -> int:
        """Get the number of loaded symbols."""
        return len(self._symbols)

    def load_symbols(self, source: str, force_reload: bool = False) -> None:
        """
        Asynchronously load symbols from the specified data source.
        
        Args:
            source: Data source name ("Binance" or "OKX")
            force_reload: If True, reload even if already loaded for this source
        """
        source = source.upper()
        
        # Skip if already loaded for this source (unless forced)
        if not force_reload and self._current_source == source and self._symbols:
            self.symbols_loaded.emit(self._symbols)
            return
        
        # Skip if already loading
        if self._loading:
            return
        
        self._loading = True
        self.loading_started.emit()
        
        # Load in background thread
        thread = threading.Thread(
            target=self._load_symbols_thread,
            args=(source,),
            daemon=True
        )
        thread.start()

    def _load_symbols_thread(self, source: str) -> None:
        """Background thread for loading symbols."""
        try:
            # Get proxy settings
            from config.settings import get_settings_manager
            settings = get_settings_manager().settings
            proxies = {}
            if settings.proxy.enabled:
                proxy_url = settings.proxy.get_proxy_url()
                if proxy_url:
                    proxies = {"http": proxy_url, "https": proxy_url}

            if source == "BINANCE":
                symbols = self._fetch_binance_symbols(proxies)
            elif source == "OKX":
                symbols = self._fetch_okx_symbols(proxies)
            else:
                raise ValueError(f"Unknown data source: {source}")

            with self._lock:
                self._symbols = symbols
                self._symbol_set = {s.symbol.upper() for s in symbols}
                self._symbol_set.update(s.raw_symbol.upper() for s in symbols)
                self._current_source = source

            logger.info(f"Loaded {len(symbols)} symbols from {source}")
            self.symbols_loaded.emit(symbols)

        except Exception as e:
            logger.error(f"Failed to load symbols from {source}: {e}")
            self.loading_error.emit(str(e))
        finally:
            self._loading = False

    def _fetch_binance_symbols(self, proxies: Dict) -> List[SymbolInfo]:
        """Fetch symbols from Binance API."""
        response = requests.get(self.BINANCE_API, proxies=proxies, timeout=15)
        response.raise_for_status()
        data = response.json()

        symbols = []
        for item in data.get("symbols", []):
            # Only include TRADING status symbols
            if item.get("status") != "TRADING":
                continue
            
            raw_symbol = item.get("symbol", "")
            base = item.get("baseAsset", "")
            quote = item.get("quoteAsset", "")
            
            if not raw_symbol or not base or not quote:
                continue
            
            # Format as BASE-QUOTE
            formatted = f"{base}-{quote}"
            
            symbols.append(SymbolInfo(
                symbol=formatted,
                raw_symbol=raw_symbol,
                base_asset=base,
                quote_asset=quote
            ))

        return symbols

    def _fetch_okx_symbols(self, proxies: Dict) -> List[SymbolInfo]:
        """Fetch symbols from OKX API."""
        response = requests.get(
            self.OKX_API,
            params={"instType": "SPOT"},
            proxies=proxies,
            timeout=15
        )
        response.raise_for_status()
        data = response.json()

        symbols = []
        if data.get("code") == "0":
            for item in data.get("data", []):
                inst_id = item.get("instId", "")
                base = item.get("baseCcy", "")
                quote = item.get("quoteCcy", "")
                state = item.get("state", "")
                
                # Only include live instruments
                if state != "live":
                    continue
                
                if not inst_id or not base or not quote:
                    continue
                
                # OKX uses BASE-QUOTE format already
                symbols.append(SymbolInfo(
                    symbol=inst_id,
                    raw_symbol=inst_id.replace("-", ""),
                    base_asset=base,
                    quote_asset=quote
                ))

        return symbols

    def search(self, query: str, limit: int = 50) -> List[SymbolInfo]:
        """
        Search for symbols matching the query.
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            
        Returns:
            List of matching SymbolInfo objects, sorted by relevance
        """
        if not query or not query.strip():
            # Return first N symbols if no query
            return self._symbols[:limit]
        
        query = query.upper().strip()
        
        # Find matches and score them
        matches = []
        for symbol in self._symbols:
            if symbol.matches(query):
                score = symbol.match_score(query)
                matches.append((score, symbol))
        
        # Sort by score (descending), then by symbol name
        matches.sort(key=lambda x: (-x[0], x[1].symbol))
        
        return [m[1] for m in matches[:limit]]

    def is_valid(self, symbol: str) -> bool:
        """
        Check if a symbol is valid (exists in the loaded list).
        
        Args:
            symbol: Symbol to validate (can be formatted or raw)
            
        Returns:
            True if the symbol is valid
        """
        if not symbol:
            return False
        
        symbol = symbol.upper().strip()
        return symbol in self._symbol_set

    def format_symbol(self, symbol: str) -> Optional[str]:
        """
        Format a symbol to the standard BASE-QUOTE format.
        
        Args:
            symbol: Input symbol (can be various formats)
            
        Returns:
            Formatted symbol or None if not found
        """
        symbol = symbol.upper().strip()
        
        # Try to find in loaded symbols
        for s in self._symbols:
            if s.symbol.upper() == symbol or s.raw_symbol.upper() == symbol:
                return s.symbol
        
        return None

    def clear(self) -> None:
        """Clear the cached symbols."""
        with self._lock:
            self._symbols = []
            self._symbol_set = set()
            self._current_source = ""


# Global service instance
_symbol_search_service: Optional[SymbolSearchService] = None


def get_symbol_search_service() -> SymbolSearchService:
    """Get the global symbol search service instance."""
    global _symbol_search_service
    if _symbol_search_service is None:
        _symbol_search_service = SymbolSearchService()
    return _symbol_search_service
