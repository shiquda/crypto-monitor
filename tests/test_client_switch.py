import sys
import time

from PyQt6.QtWidgets import QApplication

from config.settings import get_settings_manager
from core.exchange_factory import ExchangeFactory


def test_switching_stress():
    _ = QApplication(sys.argv)
    settings_manager = get_settings_manager()

    print("Starting stress test for client switching WITH ALERTS...")

    # Add a test alert
    from core.alert_manager import get_alert_manager

    alert_manager = get_alert_manager()
    # Add an alert that will definitely NOT trigger normally, but we want to test the check logic
    # Or add one that WILL trigger to test notification crash
    settings_manager.add_alert(
        alert_manager.add_alert(
            "BTC-USDT", "price_above", 10000.0
        )  # Always trigger if price > 10000
    )

    for i in range(10):
        # Toggle between Binance and OKX
        source = "BINANCE" if i % 2 == 0 else "OKX"
        print(f"Iteration {i + 1}: Switching to {source}")

        settings_manager.settings.data_source = source
        settings_manager.save()

        client = ExchangeFactory.create_client()
        client.subscribe(["BTC-USDT", "ETH-USDT"])

        # Connect to alert manager (simulating MainWindow logic)
        # We need a slot to receive the signal
        def on_ticker(pair, ticker_data):
            alert_manager.check_alerts(pair, ticker_data.price, ticker_data.percentage)

        client.ticker_updated.connect(on_ticker)

        # Simulate incoming data to trigger alert checks
        # Price > 10000 to trigger the alert we added
        from core.models import TickerData

        dummy_data = TickerData(
            pair="BTC-USDT",
            price="50000.00",
            percentage="+1.0%",
            high_24h="0",
            low_24h="0",
            quote_volume_24h="0",
        )
        client.ticker_updated.emit("BTC-USDT", dummy_data)

        # Give it a tiny bit of time to start threads and process alerts
        time.sleep(0.5)

        print(f"Stopping {source} client...")
        if client:
            client.stop()
            # client.deleteLater() # Usually handled by parent or GC, but in test we might need care

        # we don't wait for 'stopped' signal here to simulate rapid switching
        print(f"Iteration {i + 1} done.")
        sys.stdout.flush()

    print("Stress test completed successfully without immediate crash!")

    # Clean up global components to avoid exit crash
    from core.notifier import get_notification_service

    ns = get_notification_service()
    if ns:
        ns.stop()

    # Allow some time for dying workers to finish
    print("Waiting for dying workers to finish...")
    from core.worker_controller import WorkerController

    WorkerController.get_instance().cleanup_all()
    print("Done.")


if __name__ == "__main__":
    test_switching_stress()
