"""
Price Alert Manager for Crypto Monitor.
Monitors prices and triggers notifications when alert conditions are met.
"""

import time

from PyQt6.QtCore import QObject, pyqtSignal

from config.settings import PriceAlert, get_settings_manager
from core.notifier import get_notification_service


class AlertManager(QObject):
    """
    Manages price alerts and triggers notifications.

    Monitors price updates and checks them against configured alerts.
    Handles alert cooldowns and one-time alert disabling.
    """

    alert_triggered = pyqtSignal(str, str, float, float)  # pair, alert_type, target, current

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings_manager = get_settings_manager()
        self._notification_service = get_notification_service()
        self._current_prices = {}

    def check_alerts(self, pair, price, percentage_str="0.00%"):
        """
        Check if any alerts should be triggered for the given price.

        Args:
            pair: Trading pair, e.g., "BTC-USDT"
            price: Current price as string or float
            percentage_str: Current 24h change percentage as string
        """
        try:
            # Handle both string and float inputs
            if isinstance(price, (int, float)):
                current_price = float(price)
            else:
                current_price = float(str(price).replace(",", ""))
            # Parse percentage string (e.g., "+1.23%")
            percentage_val = float(percentage_str.strip("%").replace("+", ""))
        except (ValueError, AttributeError):
            return

        # Store previous price for reference
        previous_price = self._current_prices.get(pair)
        self._current_prices[pair] = current_price

        # Store previous percentage (we can use a separate dict or just rely on stateless checks if previous is needed)
        # For this feature, we need previous percentage for "change step" detection
        if not hasattr(self, "_current_percentages"):
            self._current_percentages = {}
        previous_percentage = self._current_percentages.get(pair)
        self._current_percentages[pair] = percentage_val

        # Get enabled alerts for this pair
        alerts = self._settings_manager.get_alerts_for_pair(pair)

        for alert in alerts:
            if not alert.enabled:
                continue

            if self._should_trigger(
                alert,
                current_price,
                previous_price,
                percentage_val,
                previous_percentage,
            ):
                self._trigger_alert(
                    alert,
                    current_price,
                    previous_price,
                    percentage_val,
                    previous_percentage,
                )

    def reset(self):
        """Reset all price history. Call this when switching data sources."""
        self._current_prices.clear()
        if hasattr(self, "_current_percentages"):
            self._current_percentages.clear()

    def _should_trigger(
        self,
        alert,
        current_price,
        previous_price=None,
        current_pct=0.0,
        previous_pct=None,
    ):
        """
        Check if an alert should be triggered.
        """
        # Check cooldown for repeat mode
        if alert.repeat_mode == "repeat" and alert.last_triggered:
            time_since_last = time.time() - alert.last_triggered
            if time_since_last < alert.cooldown_seconds:
                return False

        # Check condition based on alert type
        if alert.alert_type == "price_above":
            return current_price > alert.target_price

        elif alert.alert_type == "price_below":
            return current_price < alert.target_price

        elif alert.alert_type == "price_touch":
            if previous_price is None:
                # If first price, ONLY trigger if exactly equal
                return current_price == alert.target_price

            # Trigger if:
            # 1. Precise hit: current_price == target
            # 2. Crossed from below: prev < target and curr > target
            # 3. Crossed from above: prev > target and curr < target
            crossed_up = previous_price < alert.target_price and current_price > alert.target_price
            crossed_down = (
                previous_price > alert.target_price and current_price < alert.target_price
            )

            return current_price == alert.target_price or crossed_up or crossed_down

        elif alert.alert_type == "price_multiple":
            if previous_price is None or alert.target_price <= 0:
                return False

            import math

            step = alert.target_price
            curr_step = math.floor(current_price / step)
            prev_step = math.floor(previous_price / step)

            if curr_step == prev_step:
                return False

            # The boundary crossed is the higher of the two steps
            # e.g., 9.9 -> 10.1 crosses boundary 10. 10.1 -> 9.9 also crosses boundary 10.
            boundary = max(curr_step, prev_step)

            is_new_boundary = (
                alert.last_triggered_value is None or boundary != alert.last_triggered_value
            )
            return is_new_boundary

        elif alert.alert_type == "price_change_pct":
            if previous_pct is None or alert.target_price <= 0:
                return False

            import math

            step = alert.target_price
            curr_step = math.floor(current_pct / step)
            prev_step = math.floor(previous_pct / step)

            if curr_step == prev_step:
                return False

            boundary = max(curr_step, prev_step)

            is_new_boundary = (
                alert.last_triggered_value is None or boundary != alert.last_triggered_value
            )
            return is_new_boundary

        return False

    def _trigger_alert(
        self,
        alert,
        current_price,
        previous_price=None,
        current_pct=0.0,
        previous_pct=None,
    ):
        """
        Trigger an alert notification.
        """
        # Determine notification type
        notif_alert_type = alert.alert_type

        # Infer direction for touch alerts
        if alert.alert_type == "price_touch" and previous_price is not None:
            if current_price > previous_price:
                notif_alert_type = "price_above"  # Treated as crossing above
            elif current_price < previous_price:
                notif_alert_type = "price_below"  # Treated as crossing below

        # Send notification
        self._notification_service.send_price_alert(
            pair=alert.pair,
            alert_type=notif_alert_type,
            target_price=alert.target_price,
            current_price=current_price,
            current_pct=current_pct,
            previous_price=previous_price,
            previous_pct=previous_pct,
        )

        # Update alert state
        alert.last_triggered = time.time()

        # Record step value if applicable
        if alert.alert_type == "price_multiple" and alert.target_price > 0:
            import math

            curr_step = math.floor(current_price / alert.target_price)
            prev_step = (
                math.floor(previous_price / alert.target_price)
                if previous_price is not None
                else curr_step
            )
            # Record the boundary we just crossed
            alert.last_triggered_value = max(curr_step, prev_step)
        elif alert.alert_type == "price_change_pct" and alert.target_price > 0:
            import math

            curr_step = math.floor(current_pct / alert.target_price)
            prev_step = (
                math.floor(previous_pct / alert.target_price)
                if previous_pct is not None
                else curr_step
            )
            alert.last_triggered_value = max(curr_step, prev_step)

        if alert.repeat_mode == "once":
            # Disable one-time alerts after triggering
            alert.enabled = False

        # Save updated alert
        self._settings_manager.update_alert(alert)

        # Emit signal
        self.alert_triggered.emit(alert.pair, alert.alert_type, alert.target_price, current_price)

    def get_current_price(self, pair):
        """Get the current price for a pair."""
        return self._current_prices.get(pair)

    def add_alert(self, pair, alert_type, target_price, repeat_mode="once", cooldown_seconds=60):
        """
        Add a new price alert.

        Args:
            pair: Trading pair
            alert_type: Alert type ("price_above", "price_below", "price_touch")
            target_price: Target price
            repeat_mode: "once" or "repeat"
            cooldown_seconds: Cooldown for repeat mode

        Returns:
            The created PriceAlert
        """
        alert = PriceAlert(
            pair=pair,
            alert_type=alert_type,
            target_price=target_price,
            repeat_mode=repeat_mode,
            cooldown_seconds=cooldown_seconds,
        )
        self._settings_manager.add_alert(alert)
        return alert

    def remove_alert(self, alert_id):
        """Remove an alert by ID."""
        return self._settings_manager.remove_alert(alert_id)

    def get_alerts(self):
        """Get all alerts."""
        return self._settings_manager.settings.alerts

    def get_alerts_for_pair(self, pair):
        """Get all alerts for a specific pair."""
        return self._settings_manager.get_alerts_for_pair(pair)

    def toggle_alert(self, alert_id):
        """Toggle alert enabled state."""
        for alert in self._settings_manager.settings.alerts:
            if alert.id == alert_id:
                alert.enabled = not alert.enabled
                self._settings_manager.update_alert(alert)
                return True
        return False


# Global alert manager instance
_alert_manager = None


def get_alert_manager():
    """Get the global alert manager instance."""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager
