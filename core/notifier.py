"""
Desktop notification service for Crypto Monitor.
Uses desktop-notifier for cross-platform system notifications.
"""

import asyncio
import webbrowser
import threading
from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal, QThread
from core.i18n import _

try:
    from desktop_notifier import DesktopNotifier, Urgency, DEFAULT_SOUND
    NOTIFIER_AVAILABLE = True
except ImportError:
    NOTIFIER_AVAILABLE = False
    print("Warning: desktop-notifier not installed. Notifications will be disabled.")


class AsyncLoopThread(QThread):
    """
    Persistent worker thread that runs an asyncio event loop.
    Keeps the loop running to handle notification callbacks.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.loop = None
        self._ready = threading.Event()
        self._keep_running = True

    def run(self):
        """Run the event loop forever."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self._ready.set()
        
        try:
            self.loop.run_forever()
        finally:
            # Clean up pending tasks
            try:
                tasks = asyncio.all_tasks(self.loop)
                for task in tasks:
                    task.cancel()
                if tasks:
                    self.loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
                self.loop.close()
            except Exception as e:
                print(f"Error closing loop: {e}")

    def get_loop(self):
        """Get the running loop, waiting if necessary."""
        self._ready.wait()
        return self.loop

    def stop(self):
        """Stop the event loop."""
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        self.wait()


class NotificationService(QObject):
    """
    Service for sending desktop notifications.

    Uses desktop-notifier library for cross-platform support.
    Notifications can be clicked to open a URL.
    """

    notification_clicked = pyqtSignal(str)  # Emits pair name when notification clicked

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: Optional[AsyncLoopThread] = None
        
        if NOTIFIER_AVAILABLE:
            self._worker = AsyncLoopThread(self)
            self._worker.start()

    def _get_okx_url(self, pair: str) -> str:
        """Get OKX trading page URL for a pair."""
        formatted_pair = pair.lower()
        return f"https://www.okx.com/trade-spot/{formatted_pair}"

    def _open_url(self, pair: str):
        """Open the trading URL in browser."""
        url = self._get_okx_url(pair)
        webbrowser.open(url)
        self.notification_clicked.emit(pair)

    async def _send_notification_task(
        self,
        title: str,
        message: str,
        pair: str,
        urgency: 'Urgency' = None
    ):
        """
        Coroutine to send notification. 
        Runs in the background thread's loop.
        """
        if urgency is None:
            urgency = Urgency.Normal

        try:
            # We initialize a new notifier for each notification to ensure thread safety
            # relative to the current thread (the worker thread).
            # Improvements could be made to reuse it if we are sure it stays on this thread.
            notifier = DesktopNotifier(
                app_name="Crypto Monitor",
                app_icon=None
            )
            
            await notifier.send(
                title=title,
                message=message,
                urgency=urgency,
                on_clicked=lambda: self._open_url(pair),
                sound=DEFAULT_SOUND,
            )
        except Exception as e:
            print(f"Failed to send notification: {e}")

    def send_price_alert(
        self,
        pair: str,
        alert_type: str,
        target_price: float,
        current_price: float
    ):
        """
        Send a price alert notification.

        Args:
            pair: Trading pair, e.g., "BTC-USDT"
            alert_type: Alert type ("price_above", "price_below", "price_touch")
            target_price: The target price that triggered the alert
            current_price: The current price
        """
        if not NOTIFIER_AVAILABLE or not self._worker:
            print(f"[Alert] {pair}: {alert_type} at {current_price} (target: {target_price})")
            return

        # Build notification message
        symbol = pair.split("-")[0]

        if alert_type == "price_above":
            title = f"{symbol} 📈 {_('Crossed Above Target')}"
            message = f"{_('Price rose above')} ${target_price:,.2f}\n{_('Current:')} ${current_price:,.2f}"
        elif alert_type == "price_below":
            title = f"{symbol} 📉 {_('Crossed Below Target')}"
            message = f"{_('Price fell below')} ${target_price:,.2f}\n{_('Current:')} ${current_price:,.2f}"
        elif alert_type == "price_touch":
            title = f"{symbol} 🎯 {_('Price Touched Target')}"
            message = f"{_('Price reached')} ${target_price:,.2f}\n{_('Current:')} ${current_price:,.2f}"
        elif alert_type == "price_multiple":
            title = f"{symbol} 🔢 {_('Price Step Reached')}"
            message = f"{_('Price hit multiple of')} ${target_price:,.0f}\n{_('Current:')} ${current_price:,.2f}"
        elif alert_type == "price_change_pct":
            title = f"{symbol} 📊 {_('Percentage Step Reached')}"
            message = f"{_('24h Change crossed')} {target_price:.2f}% {_('step')}\n{_('Current:')} ${current_price:,.2f}"
        else:
            title = f"{symbol} 🔔 {_('Price Alert')}"
            message = f"{_('Target:')} {target_price}\n{_('Current:')} ${current_price:,.2f}"

        # Schedule usage on the background loop
        loop = self._worker.get_loop()
        if loop and loop.is_running():
             asyncio.run_coroutine_threadsafe(
                self._send_notification_task(
                    title=title,
                    message=message,
                    pair=pair,
                    urgency=Urgency.Normal
                ),
                loop
            )

    def send_test_notification(self):
        """Send a test notification."""
        if not NOTIFIER_AVAILABLE or not self._worker:
            print("[Test] Notification service not available")
            return

        loop = self._worker.get_loop()
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._send_notification_task(
                    title=_("Crypto Monitor"),
                    message=_("Notifications are working!"),
                    pair="BTC-USDT"
                ),
                loop
            )

    @property
    def is_available(self) -> bool:
        """Check if notification service is available."""
        return NOTIFIER_AVAILABLE and self._worker is not None

    def stop(self):
        """Stop the background worker."""
        if self._worker:
            self._worker.stop()


# Global notification service instance
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Get the global notification service instance."""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service
