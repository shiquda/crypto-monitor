from dataclasses import dataclass


@dataclass
class TickerData:
    pair: str
    price: str
    percentage: str
    high_24h: str = "0"
    low_24h: str = "0"
    quote_volume_24h: str = "0"
    amplitude_24h: str = "0.00%"

    icon_url: str = ""
    display_name: str = ""
    quote_token: str = ""
