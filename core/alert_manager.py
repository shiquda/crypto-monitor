"""
Price Alert Manager for Crypto Monitor.
Monitors prices and triggers notifications when alert conditions are met.
"""

import time
from typing import Dict, Optional, List
from PyQt6.QtCore import QObject, pyqtSignal

from config.settings import get_settings_manager, PriceAlert
from core.notifier import get_notification_service


class AlertManager(QObject):
    """
    Manages price alerts and triggers notifications.

    Monitors price updates and checks them against configured alerts.
    Handles alert cooldowns and one-time alert disabling.
    """

    alert_triggered = pyqtSignal(str, str, float, float)  # pair, alert_type, target, current

    # Price touch tolerance (0.1% of target price)
    TOUCH_TOLERANCE = 0.001

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings_manager = get_settings_manager()
        self._notification_service = get_notification_service()
        self._current_prices: Dict[str, float] = {}

    def check_alerts(self, pair: str, price_str: str):
        """
        Check if any alerts should be triggered for the given price.

        Args:
            pair: Trading pair, e.g., "BTC-USDT"
            price_str: Current price as string
        """
        try:
            current_price = float(price_str.replace(',', ''))
        except (ValueError, AttributeError):
            return

        # Store previous price for reference
        previous_price = self._current_prices.get(pair)
        self._current_prices[pair] = current_price

        # Get enabled alerts for this pair
        alerts = self._settings_manager.get_alerts_for_pair(pair)

        for alert in alerts:
            if not alert.enabled:
                continue

            if self._should_trigger(alert, current_price):
                self._trigger_alert(alert, current_price, previous_price)

    def _should_trigger(self, alert: PriceAlert, current_price: float) -> bool:
        """
        Check if an alert should be triggered.

        Args:
            alert: The alert configuration
            current_price: Current price

        Returns:
            True if alert should trigger
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
            # Check if price is within tolerance of target
            tolerance = alert.target_price * self.TOUCH_TOLERANCE
            return abs(current_price - alert.target_price) <= tolerance

        return False

    def _trigger_alert(self, alert: PriceAlert, current_price: float, previous_price: Optional[float] = None):
        """
        Trigger an alert notification.

        Args:
            alert: The alert configuration
            current_price: Current price that triggered the alert
            previous_price: Price before update (optional)
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
            current_price=current_price
        )

        # Update alert state
        alert.last_triggered = time.time()

        if alert.repeat_mode == "once":
            # Disable one-time alerts after triggering
            alert.enabled = False

        # Save updated alert
        self._settings_manager.update_alert(alert)

        # Emit signal
        self.alert_triggered.emit(
            alert.pair,
            alert.alert_type,
            alert.target_price,
            current_price
        )

    def get_current_price(self, pair: str) -> Optional[float]:
        """Get the current price for a pair."""
        return self._current_prices.get(pair)

    def add_alert(
        self,
        pair: str,
        alert_type: str,
        target_price: float,
        repeat_mode: str = "once",
        cooldown_seconds: int = 60
    ) -> PriceAlert:
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
            cooldown_seconds=cooldown_seconds
        )
        self._settings_manager.add_alert(alert)
        return alert

    def remove_alert(self, alert_id: str) -> bool:
        """Remove an alert by ID."""
        return self._settings_manager.remove_alert(alert_id)

    def get_alerts(self) -> List[PriceAlert]:
        """Get all alerts."""
        return self._settings_manager.settings.alerts

    def get_alerts_for_pair(self, pair: str) -> List[PriceAlert]:
        """Get all alerts for a specific pair."""
        return self._settings_manager.get_alerts_for_pair(pair)

    def toggle_alert(self, alert_id: str) -> bool:
        """Toggle alert enabled state."""
        for alert in self._settings_manager.settings.alerts:
            if alert.id == alert_id:
                alert.enabled = not alert.enabled
                self._settings_manager.update_alert(alert)
                return True
        return False


# Global alert manager instance
_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """Get the global alert manager instance."""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager
