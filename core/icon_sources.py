"""Icon source configuration and fallback chain for cryptocurrency logos."""

import logging
from dataclasses import dataclass
from typing import ClassVar

logger = logging.getLogger(__name__)


@dataclass
class IconSource:
    """Configuration for a single icon source."""

    name: str
    url_template: str
    format: str
    priority: int
    description: str = ""


class IconSourceManager:
    """Manages multiple icon sources with fallback chain."""

    SOURCES: ClassVar[list[IconSource]] = [
        IconSource(
            name="okx",
            url_template="https://static.okx.com/cdn/oksupport/asset/currency/icon/{symbol_lower}.png",
            format="png",
            priority=1,
            description="OKX - Excellent coverage, 90%+ mainstream coins",
        ),
        IconSource(
            name="binance",
            url_template="https://cdn.jsdelivr.net/gh/vadimmalykhin/binance-icons/crypto/{symbol_lower}.svg",
            format="svg",
            priority=2,
            description="Binance Icons - SVG format, good coverage",
        ),
        IconSource(
            name="cryptocurrency-icons",
            url_template="https://cdn.jsdelivr.net/npm/cryptocurrency-icons@0.18.1/svg/color/{symbol_lower}.svg",
            format="svg",
            priority=3,
            description="Cryptocurrency Icons - NPM package, mainstream coins",
        ),
        IconSource(
            name="cryptofonts",
            url_template="https://cdn.jsdelivr.net/gh/Cryptofonts/cryptoicons@master/SVG/{symbol_lower}.svg",
            format="svg",
            priority=4,
            description="Cryptofonts - Community maintained, includes meme coins",
        ),
    ]

    @classmethod
    def get_sources_for_symbol(cls, symbol: str) -> list[tuple[IconSource, dict[str, str]]]:
        """
        Get all applicable icon sources for a given symbol with URL parameters.

        Args:
            symbol: Coin symbol (e.g., 'BTC', 'MIDNIGHT')

        Returns:
            List of (IconSource, url_params) tuples, ordered by priority
        """
        symbol_lower = symbol.lower()
        sources_with_params = []

        for source in sorted(cls.SOURCES, key=lambda s: s.priority):
            params = {
                "symbol": symbol.upper(),
                "symbol_lower": symbol_lower,
            }
            sources_with_params.append((source, params))

        return sources_with_params

    @classmethod
    def build_icon_url(cls, source: IconSource, params: dict[str, str]) -> str:
        """
        Build icon URL from source and parameters.

        Args:
            source: IconSource configuration
            params: URL parameters dict

        Returns:
            Complete icon URL
        """
        return source.url_template.format(**params)
