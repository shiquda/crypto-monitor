import logging

import requests
from PyQt6.QtCore import QTimer

from config.settings import get_settings_manager
from core.base_client import BaseExchangeClient
from core.models import TickerData

logger = logging.getLogger(__name__)


class DexScreenerClient(BaseExchangeClient):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pairs = set()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll_data)
        self._timer.setInterval(10000)
        self._session = requests.Session()
        self._configure_proxy()
        self._is_connected = False

    def _configure_proxy(self):
        settings = get_settings_manager().settings
        if settings.proxy.enabled:
            proxy_url = settings.proxy.get_proxy_url()
            if proxy_url:
                logger.debug(f"Configuring proxy for DexScreenerClient: {proxy_url}")
                self._session.proxies = {"http": proxy_url, "https": proxy_url}
        else:
            self._session.proxies = {}

    def subscribe(self, pairs: list[str]):
        new_pairs = [p for p in pairs if p.startswith("chain:")]
        if not new_pairs:
            return

        logger.info(f"Subscribing to DEX pairs: {new_pairs}")
        for pair in new_pairs:
            self._pairs.add(pair)

        if not self._timer.isActive() and self._pairs:
            logger.info("Starting DEX polling timer")
            self._timer.start()
            self._is_connected = True
            self.connection_status.emit(True, "Connected (Polling)")
            self._poll_data()
        else:
            logger.info(
                f"Timer already active or no pairs. Active: {self._timer.isActive()}, "
                f"Pairs count: {len(self._pairs)}"
            )
            self._poll_data()

    def stop(self):
        self._timer.stop()
        self._pairs.clear()
        self._is_connected = False
        self.stopped.emit()

    def reconnect(self):
        self._configure_proxy()
        self._poll_data()

    def get_stats(self):
        return {"type": "REST Polling", "interval": "10s", "pairs": len(self._pairs)}

    def fetch_klines(self, pair: str, interval: str, limit: int) -> list[dict]:
        if not pair.startswith("chain:"):
            return []

        try:
            parts = pair.split(":")
            if len(parts) < 3:
                return []

            network = parts[1]
            address = parts[2]

            network_map = {
                "ethereum": "eth",
                "polygon": "polygon_pos",
                "avalanche": "avax",
            }

            network = network_map.get(network, network)

            token_url = f"https://api.dexscreener.com/latest/dex/tokens/{address}"

            headers = {"User-Agent": "Mozilla/5.0"}

            logger.debug(f"Fetching klines: token info from {token_url}")
            resp = self._session.get(token_url, headers=headers, timeout=10)
            data = resp.json()
            pairs = data.get("pairs", [])
            if not pairs:
                logger.warning(f"No pairs found for kline fetch: {pair}")
                return []

            sorted_pairs = sorted(
                pairs, key=lambda x: float(x.get("liquidity", {}).get("usd", 0) or 0), reverse=True
            )
            best_pair = sorted_pairs[0]
            pool_address = best_pair["pairAddress"]

            timeframe = "day"
            if "h" in interval:
                timeframe = "hour"
            elif "m" in interval:
                timeframe = "minute"

            gt_url = f"https://api.geckoterminal.com/api/v2/networks/{network}/pools/{pool_address}/ohlcv/{timeframe}"
            logger.debug(f"Fetching klines: OHLCV from {gt_url}")
            gt_resp = self._session.get(gt_url, headers=headers, timeout=10)
            gt_data = gt_resp.json()

            ohlcv_list = gt_data.get("data", {}).get("attributes", {}).get("ohlcv_list", [])

            klines = []
            for item in ohlcv_list[:limit]:
                klines.append(
                    {
                        "timestamp": item[0] * 1000,
                        "open": item[1],
                        "high": item[2],
                        "low": item[3],
                        "close": item[4],
                        "volume": str(item[5]),
                    }
                )

            klines.reverse()

            return klines

        except Exception as e:
            logger.error(f"Error fetching klines for {pair}: {e}")
            return []

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    def _poll_data(self):
        if not self._pairs:
            logger.debug("No pairs to poll")
            return

        addresses = []
        pair_map = {}

        for p in self._pairs:
            parts = p.split(":")
            if len(parts) >= 3:
                original_addr = parts[2]
                addresses.append(original_addr)
                pair_map[original_addr.lower()] = p
            else:
                logger.warning(f"Invalid pair format in subscription: {p}")

        if not addresses:
            return

        addr_str = ",".join(addresses[:30])
        url = f"https://api.dexscreener.com/latest/dex/tokens/{addr_str}"
        headers = {"User-Agent": "Mozilla/5.0"}

        logger.debug(f"Polling DEX data for {len(addresses)} tokens. URL: {url}")

        try:
            resp = self._session.get(url, headers=headers, timeout=10)

            if resp.status_code != 200:
                logger.error(f"Polling failed with status code: {resp.status_code}")
                self.connection_status.emit(False, f"HTTP Error: {resp.status_code}")
                return

            data = resp.json()

            if not data.get("pairs"):
                logger.warning(
                    f"No pairs returned in response from {url}. "
                    "Check if the address case is correct (Solana addresses are case-sensitive)."
                )
                logger.debug(f"Raw response: {resp.text[:500]}")
                return

            token_best_pair = {}
            for pair_data in data["pairs"]:
                base_token = pair_data.get("baseToken", {})
                token_addr = base_token.get("address", "").lower()

                if not token_addr:
                    continue

                if token_addr not in token_best_pair:
                    token_best_pair[token_addr] = pair_data
                else:
                    curr_liq = float(
                        token_best_pair[token_addr].get("liquidity", {}).get("usd", 0) or 0
                    )
                    new_liq = float(pair_data.get("liquidity", {}).get("usd", 0) or 0)
                    if new_liq > curr_liq:
                        token_best_pair[token_addr] = pair_data

            updated_count = 0
            for addr, pair_data in token_best_pair.items():
                if addr in pair_map:
                    original_id = pair_map[addr]

                    price = str(pair_data.get("priceUsd", "0"))
                    change = f"{pair_data.get('priceChange', {}).get('h24', 0)}%"
                    if not change.startswith("-"):
                        change = f"+{change}"

                    ticker = TickerData(
                        pair=original_id,
                        price=price,
                        percentage=change,
                        quote_volume_24h=str(pair_data.get("volume", {}).get("h24", 0)),
                        icon_url=pair_data.get("info", {}).get("imageUrl", ""),
                        display_name=pair_data.get("baseToken", {}).get("symbol", ""),
                        quote_token=pair_data.get("quoteToken", {}).get("symbol", ""),
                    )

                    logger.debug(f"Emitting update for {original_id}: {price} ({change})")
                    self.ticker_updated.emit(original_id, ticker)
                    updated_count += 1
                else:
                    logger.debug(
                        f"Received data for {addr} but not in requested map: "
                        f"{list(pair_map.keys())}"
                    )

            logger.debug(f"Poll success: Updated {updated_count}/{len(addresses)} requested tokens")

        except Exception as e:
            logger.error(f"Polling error details: {e}", exc_info=True)
            self.connection_status.emit(False, f"Polling Error: {str(e)}")
