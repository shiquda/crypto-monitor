from core.symbol_search import SymbolSearchService


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_okx_swap_symbols_use_display_symbol_and_raw_inst_id(monkeypatch):
    service = SymbolSearchService()

    payload = {
        "code": "0",
        "data": [
            {
                "instId": "BTC-USDT-SWAP",
                "baseCcy": "BTC",
                "quoteCcy": "USDT",
                "state": "live",
            }
        ],
    }

    monkeypatch.setattr(
        "core.symbol_search.requests.get",
        lambda *args, **kwargs: _FakeResponse(payload),
    )

    symbols = service._fetch_okx_swap_symbols({})

    assert len(symbols) == 1
    assert symbols[0].symbol == "BTC-USDT"
    assert symbols[0].raw_symbol == "BTC-USDT-SWAP"
