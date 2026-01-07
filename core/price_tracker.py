"""
Price tracking and color calculation logic.
Ported from the original Vue.js implementation.
"""

from dataclasses import dataclass
from typing import Dict, Optional
from PyQt6.QtGui import QColor


@dataclass
class PriceState:
    """State for a single crypto pair."""
    current_price: float = 0.0
    average_price: float = 0.0
    trend: str = ""  # "↑", "↓", ""
    color: str = "#FFFFFF"
    percentage: str = "0.00%"


class PriceTracker:
    """
    Tracks price changes and calculates display colors.
    Implements moving average and color gradient logic.
    """

    # Maximum difference ratio for color intensity (50%)
    MAX_DIFF_RATIO = 0.5

    # Moving average period
    PERIOD = 60

    def __init__(self):
        self._states: Dict[str, PriceState] = {}

    def update_price(self, pair: str, price_str: str, percentage: str) -> PriceState:
        """
        Update price for a pair and calculate new state.

        Args:
            pair: Trading pair (e.g., "BTC-USDT")
            price_str: Price as string
            percentage: Percentage change string

        Returns:
            Updated PriceState
        """
        try:
            current_price = float(price_str)
        except ValueError:
            current_price = 0.0

        # Get or create state
        if pair not in self._states:
            self._states[pair] = PriceState(
                current_price=current_price,
                average_price=current_price
            )

        state = self._states[pair]

        # Update moving average
        state.average_price = (
            state.average_price * (self.PERIOD - 1) + current_price
        ) / self.PERIOD

        state.current_price = current_price
        state.percentage = percentage

        # Calculate color based on intraday percentage (as requested by user)
        # Check settings for color schema
        from config.settings import get_settings_manager
        settings = get_settings_manager().settings
        is_standard = settings.color_schema == "standard"
        
        green = "#4CAF50"
        red = "#F44336"
        white = "#FFFFFF" # or adapt to theme, but PriceTracker is theme-agnostic usually, returning hex.
        # Ideally white should be theme dependent but here we return a fixed color. 
        # The card handles text color default based on theme if trend is flat.
        
        if percentage.startswith('+'):
            state.color = green if is_standard else red
            state.trend = "↑"
        elif percentage.startswith('-'):
            state.color = red if is_standard else green
            state.trend = "↓"
        else:
            state.color = white
            state.trend = ""

        return state

    def _calculate_color(self, difference: float, avg_price: float) -> str:
        """
        Calculate display color based on price difference.

        Green gradient for positive difference (price going up).
        Red gradient for negative difference (price going down).
        White for no change.

        Args:
            difference: Price difference from average
            avg_price: Average price

        Returns:
            HSL color string
        """
        if avg_price == 0:
            return "hsl(0, 0%, 100%)"

        # Calculate ratio (0 to 1)
        ratio = min(abs(difference / avg_price), self.MAX_DIFF_RATIO) / self.MAX_DIFF_RATIO

        if difference > 0:
            # Green: hue = 120
            hue = 120
        elif difference < 0:
            # Red: hue = 0
            hue = 0
        else:
            # Black for no change
            return "#333333"

        # Calculate lightness (50% to 80%)
        # Higher ratio = more saturated color = lower lightness
        lightness = 80 - (ratio * 30)
        lightness = max(50, min(80, lightness))

        return f"hsl({hue}, 100%, {lightness}%)"

    def get_state(self, pair: str) -> Optional[PriceState]:
        """Get current state for a pair."""
        return self._states.get(pair)

    def clear_pair(self, pair: str):
        """Clear state for a pair."""
        self._states.pop(pair, None)

    def clear_all(self):
        """Clear all states."""
        self._states.clear()


def hsl_to_qcolor(hsl_string: str) -> QColor:
    """
    Convert HSL string to QColor.

    Args:
        hsl_string: HSL color string like "hsl(120, 100%, 70%)"

    Returns:
        QColor object
    """
    try:
        # Parse HSL string
        hsl_string = hsl_string.strip()
        if hsl_string.startswith("hsl(") and hsl_string.endswith(")"):
            values = hsl_string[4:-1].split(",")
            h = int(values[0].strip())
            s = int(values[1].strip().rstrip('%'))
            l = int(values[2].strip().rstrip('%'))

            # QColor.fromHsl expects h (0-359), s (0-255), l (0-255)
            color = QColor.fromHsl(
                h,
                int(s * 2.55),  # Convert 0-100 to 0-255
                int(l * 2.55)
            )
            return color
    except (ValueError, IndexError):
        pass

    return QColor(255, 255, 255)  # Default to white


def percentage_color(percentage_str: str) -> QColor:
    """
    Get color for percentage display.

    Args:
        percentage_str: Percentage string like "+1.23%" or "-0.45%"

    Returns:
        QColor - green for positive, red for negative
    """
    if percentage_str.startswith('+'):
        return QColor(0x99, 0xFF, 0x99)  # Light green
    elif percentage_str.startswith('-'):
        return QColor(0xFF, 0x99, 0x99)  # Light red
    else:
        return QColor(0xFF, 0xFF, 0xFF)  # White
