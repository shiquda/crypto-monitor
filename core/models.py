"""
Standard data models for the application.
"""

from dataclasses import dataclass


@dataclass
class TickerData:
    """Standardized ticker data from exchanges."""

    pair: str
    price: str
    percentage: str
    high_24h: str = "0"
    low_24h: str = "0"
    quote_volume_24h: str = "0"
