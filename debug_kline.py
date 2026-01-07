import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from config.settings import get_settings_manager
from core.binance_client import BinanceClient
from core.okx_client import OkxClientManager

def test_fetch():
    print("--- Starting Debug Test ---")
    
    settings = get_settings_manager().settings
    print(f"Proxy Enabled: {settings.proxy.enabled}")
    if settings.proxy.enabled:
        print(f"Proxy Host: {settings.proxy.host}")
        print(f"Proxy Port: {settings.proxy.port}")
    
    pair = "BTC-USDT"
    
    print(f"\n[Test 1] Testing Binance fetch for {pair}...")
    try:
        # Create client without parent
        client = BinanceClient(None)
        # We need to wait a moment or just call fetch_klines. 
        # fetch_klines is synchronous in its HTTP part, so it should block until done.
        klines = client.fetch_klines(pair, "1h", 24)
        print(f"Result: Found {len(klines)} candles.")
        if klines:
            print(f"Sample: {klines[0]}")
        else:
            print("Result: Empty list returned.")
    except Exception as e:
        print(f"Binance Error: {e}")

    print(f"\n[Test 2] Testing OKX fetch for {pair}...")
    try:
        client = OkxClientManager(None)
        klines = client.fetch_klines(pair, "1h", 24)
        print(f"Result: Found {len(klines)} candles.")
        if klines:
             print(f"Sample: {klines[0]}")
        else:
             print("Result: Empty list returned.")
    except Exception as e:
        print(f"OKX Error: {e}")

if __name__ == "__main__":
    test_fetch()
