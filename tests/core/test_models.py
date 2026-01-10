from core.models import TickerData


def test_ticker_data_initialization():
    ticker = TickerData(pair="BTC-USDT", price="50000.00", percentage="+1.5%")

    assert ticker.pair == "BTC-USDT"
    assert ticker.price == "50000.00"
    assert ticker.percentage == "+1.5%"
    assert ticker.high_24h == "0"
    assert ticker.low_24h == "0"
    assert ticker.quote_volume_24h == "0"


def test_ticker_data_full_initialization():
    ticker = TickerData(
        pair="ETH-USDT",
        price="3000.00",
        percentage="-2.0%",
        high_24h="3100.00",
        low_24h="2900.00",
        quote_volume_24h="100M",
    )

    assert ticker.high_24h == "3100.00"
    assert ticker.low_24h == "2900.00"
    assert ticker.quote_volume_24h == "100M"


def test_ticker_data_immutability_check():
    ticker = TickerData("BTC-USDT", "100", "0%")
    ticker.price = "101"
    assert ticker.price == "101"
