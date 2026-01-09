"""
Desktop notification service for Crypto Monitor.
Uses desktop-notifier for cross-platform system notifications.
"""

import asyncio
import webbrowser
# Keeping imports clean
import threading
import sys
import os
from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal, QThread, QUrl
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from core.i18n import _
from core.utils import suppress_output
from config.settings import get_settings_manager

try:
    from desktop_notifier import DesktopNotifier, Urgency, DEFAULT_SOUND, Sound
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
        self._notifier: Optional['DesktopNotifier'] = None
        
        if NOTIFIER_AVAILABLE:
            self._worker = AsyncLoopThread(self)
            self._worker.start()
            
        # Initialize media player for custom sounds
        self._player = QMediaPlayer()
        self._audio_output = QAudioOutput()
        self._player.setAudioOutput(self._audio_output)

    def _get_okx_url(self, pair: str) -> str:
        """Get OKX trading page URL for a pair."""
        formatted_pair = pair.lower()
        return f"https://www.okx.com/trade-spot/{formatted_pair}"

    def _open_url(self, pair: str):
        """Open the trading URL in browser."""
        url = self._get_okx_url(pair)
        webbrowser.open(url)
        self.notification_clicked.emit(pair)

    async def _ensure_notifier(self):
        """Ensure DesktopNotifier is initialized (lazy init in loop)."""
        if self._notifier is None:
            try:
                self._notifier = DesktopNotifier(
                    app_name="Crypto Monitor",
                    app_icon=None
                )
            except Exception as e:
                print(f"Failed to initialize DesktopNotifier: {e}")

    def _play_sound(self, sound_path: str):
        """Play a custom sound using Qt Multimedia."""
        try:
            if os.path.exists(sound_path):
                # Suppress FFmpeg/backend logs
                with suppress_output():
                    self._player.setSource(QUrl.fromLocalFile(sound_path))
                    self._audio_output.setVolume(1.0)
                    self._player.play()
            else:
                print(f"Sound file not found: {sound_path}")
        except Exception as e:
            print(f"Error playing sound: {e}")

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
            await self._ensure_notifier()
            if self._notifier:
                settings = get_settings_manager().settings
                sound_file = None
                
                if settings.sound_mode == "system":
                    sound_file = DEFAULT_SOUND
                elif settings.sound_mode == "chime":
                    # Resolve path for chime sound
                    if getattr(sys, 'frozen', False):
                        # Running in PyInstaller bundle
                        base_path = sys._MEIPASS
                    else:
                        # Running in dev mode
                        base_path = os.getcwd()
                    
                    chime_path = os.path.join(base_path, 'assets', 'sounds', 'chime-alert.mp3')
                    # Play sound directly using Qt
                    self._play_sound(chime_path)
                    # Don't use system notification sound
                    sound_file = None

                await self._notifier.send(
                    title=title,
                    message=message,
                    urgency=urgency,
                    on_clicked=lambda: self._open_url(pair),
                    sound=sound_file,
                )
        except Exception as e:
            print(f"Failed to send notification: {e}")

    def send_price_alert(
        self,
        pair: str,
        alert_type: str,
        target_price: float,
        current_price: float,
        current_pct: float = 0.0,
        previous_price: float = None,
        previous_pct: float = None
    ):
        """
        Send a price alert notification.

        Args:
            pair: Trading pair, e.g., "BTC-USDT"
            alert_type: Alert type ("price_above", "price_below", "price_touch")
            target_price: The target price that triggered the alert
            current_price: The current price
            current_pct: The current 24h change percentage
            previous_price: The previous price (for step alerts)
            previous_pct: The previous percentage (for percentage step alerts)
        """
        if not NOTIFIER_AVAILABLE or not self._worker:
            print(f"[Alert] {pair}: {alert_type} at {current_price} (target: {target_price})")
            return

        from core.utils import format_price

        # Build notification message
        symbol = pair.split("-")[0]
        
        # Format current price with smart precision and percentage change
        pct_sign = "+" if current_pct >= 0 else ""
        current_display = f"${format_price(current_price)} ({pct_sign}{current_pct:.2f}%)"

        if alert_type == "price_above":
            title = f"{symbol} 📈 {_('Crossed Above Target')}"
            message = f"{_('Price rose above')} ${format_price(target_price)}\n{_('Current:')} {current_display}"
        elif alert_type == "price_below":
            title = f"{symbol} 📉 {_('Crossed Below Target')}"
            message = f"{_('Price fell below')} ${format_price(target_price)}\n{_('Current:')} {current_display}"
        elif alert_type == "price_touch":
            title = f"{symbol} 🎯 {_('Price Touched Target')}"
            message = f"{_('Price reached')} ${format_price(target_price)}\n{_('Current:')} {current_display}"
        elif alert_type == "price_multiple":
            # Calculate the crossed price step using previous_price
            # When price crosses a step boundary, we want to show the boundary that was crossed
            import math
            step = target_price
            if previous_price is not None:
                prev_step = math.floor(previous_price / step)
                curr_step = math.floor(current_price / step)
                # The crossed boundary is the one between prev_step and curr_step
                if curr_step > prev_step:
                    # Price went up, crossed from prev_step to curr_step
                    reached_price = curr_step * step
                else:
                    # Price went down, crossed from prev_step to curr_step
                    reached_price = (prev_step) * step
            else:
                reached_price = math.floor(current_price / step) * step
            title = f"{symbol} 🔢 {_('Price Step Reached')}"
            message = f"{_('Reached')} ${format_price(reached_price)}\n{_('Current:')} {current_display}"
        elif alert_type == "price_change_pct":
            # Calculate the crossed percentage step using previous_pct
            import math
            step = target_price
            if previous_pct is not None:
                prev_step = math.floor(previous_pct / step)
                curr_step = math.floor(current_pct / step)
                # The crossed boundary is the one between prev_step and curr_step
                if curr_step > prev_step:
                    # Percentage went up
                    reached_pct = curr_step * step
                else:
                    # Percentage went down
                    reached_pct = prev_step * step
            else:
                reached_pct = math.floor(current_pct / step) * step
            # Determine precision from step value (e.g., 0.01 -> 2 decimals)
            if step < 1:
                step_str = f"{step:.10f}".rstrip('0')
                pct_precision = len(step_str.split('.')[1]) if '.' in step_str else 0
            else:
                pct_precision = 0
            pct_display = f"+{reached_pct:.{pct_precision}f}%" if reached_pct >= 0 else f"{reached_pct:.{pct_precision}f}%"
            title = f"{symbol} 📊 {_('Percentage Step Reached')}"
            message = f"{_('24h Change reached')} {pct_display}\n{_('Current:')} {current_display}"
        else:
            title = f"{symbol} 🔔 {_('Price Alert')}"
            message = f"{_('Target:')} {format_price(target_price)}\n{_('Current:')} {current_display}"

        # Schedule usage on the background loop
        loop = self._worker.get_loop()
        if loop and loop.is_running() and not loop.is_closed():
             try:
                 asyncio.run_coroutine_threadsafe(
                    self._send_notification_task(
                        title=title,
                        message=message,
                        pair=pair,
                        urgency=Urgency.Normal
                    ),
                    loop
                )
             except RuntimeError:
                 # Loop might be closed during execution
                 pass

    def send_test_notification(self):
        """Send a test notification."""
        if not NOTIFIER_AVAILABLE or not self._worker:
            print("[Test] Notification service not available")
            return

        loop = self._worker.get_loop()
        if loop and loop.is_running() and not loop.is_closed():
            try:
                asyncio.run_coroutine_threadsafe(
                    self._send_notification_task(
                        title=_("Crypto Monitor"),
                        message=_("Notifications are working!"),
                        pair="BTC-USDT"
                    ),
                    loop
                )
            except RuntimeError:
                pass

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
