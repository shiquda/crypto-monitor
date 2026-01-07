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

    def check_alerts(self, pair: str, price: 'str | float', percentage_str: str = "0.00%"):
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
                current_price = float(str(price).replace(',', ''))
            # Parse percentage string (e.g., "+1.23%")
            percentage_val = float(percentage_str.strip('%').replace('+', ''))
        except (ValueError, AttributeError):
            return

        # Store previous price for reference
        previous_price = self._current_prices.get(pair)
        self._current_prices[pair] = current_price
        
        # Store previous percentage (we can use a separate dict or just rely on stateless checks if previous is needed)
        # For this feature, we need previous percentage for "change step" detection
        if not hasattr(self, '_current_percentages'):
            self._current_percentages = {}
        previous_percentage = self._current_percentages.get(pair)
        self._current_percentages[pair] = percentage_val

        # Get enabled alerts for this pair
        alerts = self._settings_manager.get_alerts_for_pair(pair)

        for alert in alerts:
            if not alert.enabled:
                continue

            if self._should_trigger(alert, current_price, previous_price, percentage_val, previous_percentage):
                self._trigger_alert(alert, current_price, previous_price)

    def reset(self):
        """Reset all price history. Call this when switching data sources."""
        self._current_prices.clear()
        if hasattr(self, '_current_percentages'):
            self._current_percentages.clear()

    def _should_trigger(
        self, 
        alert: PriceAlert, 
        current_price: float, 
        previous_price: Optional[float] = None,
        current_pct: float = 0.0,
        previous_pct: Optional[float] = None
    ) -> bool:
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
            # Check if price is within tolerance of target
            tolerance = alert.target_price * self.TOUCH_TOLERANCE
            return abs(current_price - alert.target_price) <= tolerance
            
        elif alert.alert_type == "price_multiple":
            if previous_price is None or alert.target_price <= 0:
                return False
            # Check if we crossed a multiple of target_price (which acts as step here)
            # Example: step=1000. Prev=95800, Curr=96100. 
            # floor(95800/1000) = 95. floor(96100/1000) = 96. Changed -> Trigger.
            import math
            step = alert.target_price
            return math.floor(previous_price / step) != math.floor(current_price / step)
            
        elif alert.alert_type == "price_change_pct":
            if previous_pct is None or alert.target_price <= 0:
                return False
            # Check if percentage crossed a multiple of target_price (step)
            # Example: step=2. Prev=1.9, Curr=2.1.
            # floor(1.9/2) = 0. floor(2.1/2) = 1. Changed -> Trigger.
            import math
            step = alert.target_price
            return math.floor(previous_pct / step) != math.floor(current_pct / step)

        return False

    def _trigger_alert(self, alert: PriceAlert, current_price: float, previous_price: Optional[float] = None):
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
