import time
from unittest.mock import MagicMock, patch

import pytest

from config.settings import PriceAlert
from core.alert_manager import AlertManager


class TestAlertManager:
    @pytest.fixture
    def alert_manager(self):
        """Fixture to create an AlertManager instance with mocked dependencies."""
        with (
            patch("core.alert_manager.get_settings_manager") as mock_get_settings,
            patch("core.alert_manager.get_notification_service") as mock_get_notifier,
        ):
            mock_settings_mgr = MagicMock()
            mock_settings_mgr.settings.alerts = []
            mock_settings_mgr.get_alerts_for_pair.return_value = []
            mock_get_settings.return_value = mock_settings_mgr

            mock_notifier = MagicMock()
            mock_get_notifier.return_value = mock_notifier

            manager = AlertManager()
            manager._settings_manager = mock_settings_mgr
            manager._notification_service = mock_notifier

            yield manager

    def create_alert(
        self, alert_type, target_price, pair="BTC-USDT", repeat_mode="once", cooldown=60
    ):
        """Helper to create a PriceAlert object."""
        return PriceAlert(
            pair=pair,
            alert_type=alert_type,
            target_price=target_price,
            repeat_mode=repeat_mode,
            cooldown_seconds=cooldown,
            enabled=True,
        )

    def test_price_above_trigger(self, alert_manager):
        alert = self.create_alert("price_above", 100.0)

        assert alert_manager._should_trigger(alert, 99.0) is False
        assert alert_manager._should_trigger(alert, 100.0) is False
        assert alert_manager._should_trigger(alert, 101.0) is True

    def test_price_below_trigger(self, alert_manager):
        alert = self.create_alert("price_below", 100.0)

        assert alert_manager._should_trigger(alert, 101.0) is False
        assert alert_manager._should_trigger(alert, 100.0) is False
        assert alert_manager._should_trigger(alert, 99.0) is True

    def test_price_touch_crossing_up(self, alert_manager):
        alert = self.create_alert("price_touch", 100.0)

        assert (
            alert_manager._should_trigger(alert, current_price=101.0, previous_price=99.0) is True
        )

    def test_price_touch_crossing_down(self, alert_manager):
        alert = self.create_alert("price_touch", 100.0)

        assert (
            alert_manager._should_trigger(alert, current_price=99.0, previous_price=101.0) is True
        )

    def test_price_touch_exact_hit(self, alert_manager):
        alert = self.create_alert("price_touch", 100.0)

        assert (
            alert_manager._should_trigger(alert, current_price=100.0, previous_price=90.0) is True
        )

    def test_price_touch_no_trigger(self, alert_manager):
        alert = self.create_alert("price_touch", 100.0)

        assert (
            alert_manager._should_trigger(alert, current_price=95.0, previous_price=90.0) is False
        )

    def test_price_multiple_trigger(self, alert_manager):
        # Alert every $1000 step
        alert = self.create_alert("price_multiple", 1000.0, repeat_mode="repeat")

        assert (
            alert_manager._should_trigger(alert, current_price=9800.0, previous_price=9500.0)
            is False
        )

        assert (
            alert_manager._should_trigger(alert, current_price=10200.0, previous_price=9800.0)
            is True
        )

    def test_price_multiple_repeated_boundary(self, alert_manager):
        """
        Test that crossing the SAME boundary repeatedly doesn't re-trigger
        immediately if last_triggered_value is set.
        """
        alert = self.create_alert("price_multiple", 1000.0, repeat_mode="repeat")

        # Simulate first trigger at 10000 boundary (10 * 1000)
        alert.last_triggered_value = 10

        assert (
            alert_manager._should_trigger(alert, current_price=10100.0, previous_price=9900.0)
            is False
        )

        assert (
            alert_manager._should_trigger(alert, current_price=11200.0, previous_price=10100.0)
            is True
        )

    def test_price_change_pct_trigger(self, alert_manager):
        # Alert every 5% change
        alert = self.create_alert("price_change_pct", 5.0, repeat_mode="repeat")

        assert (
            alert_manager._should_trigger(
                alert, current_price=0, previous_price=0, current_pct=4.0, previous_pct=2.0
            )
            is False
        )

        assert (
            alert_manager._should_trigger(
                alert, current_price=0, previous_price=0, current_pct=6.0, previous_pct=4.0
            )
            is True
        )

    def test_cooldown_logic(self, alert_manager):
        alert = self.create_alert("price_above", 100.0, repeat_mode="repeat", cooldown=10)
        alert.last_triggered = time.time()  # Just triggered now

        assert alert_manager._should_trigger(alert, 150.0) is False

        # Simulate time passing (move last_triggered to past)
        alert.last_triggered = time.time() - 11
        assert alert_manager._should_trigger(alert, 150.0) is True

    def test_check_alerts_flow(self, alert_manager):
        """Test the full check_alerts flow, including side effects like disabling 'once' alerts."""
        pair = "BTC-USDT"
        alert_once = self.create_alert("price_above", 100.0, repeat_mode="once")
        alert_manager._settings_manager.get_alerts_for_pair.return_value = [alert_once]

        alert_manager.check_alerts(pair, "90.00", "+0.0%")
        assert alert_manager._notification_service.send_price_alert.call_count == 0
        assert alert_once.enabled is True

        alert_manager.check_alerts(pair, "110.00", "+1.0%")

        assert alert_manager._notification_service.send_price_alert.call_count == 1
        assert alert_once.enabled is False
        alert_manager._settings_manager.update_alert.assert_called_with(alert_once)

    def test_check_alerts_string_parsing(self, alert_manager):
        """Test robust parsing of price strings (commas, symbols)."""
        pair = "ETH-USDT"
        alert = self.create_alert("price_above", 2000.0)
        alert_manager._settings_manager.get_alerts_for_pair.return_value = [alert]

        alert_manager.check_alerts(pair, "2,500.00", "+5.0%")

        assert alert_manager._notification_service.send_price_alert.call_count == 1
        call_args = alert_manager._notification_service.send_price_alert.call_args[1]
        assert call_args["current_price"] == 2500.0
