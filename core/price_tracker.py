from dataclasses import dataclass

from PyQt6.QtGui import QColor

from core.models import TickerData


@dataclass
class PriceState:
    current_price: float = 0.0
    average_price: float = 0.0
    trend: str = ""
    color: str = "#FFFFFF"
    percentage: str = "0.00%"
    high_24h: str = "0"
    low_24h: str = "0"
    quote_volume_24h: str = "0"
    amplitude_24h: str = "0.00%"

    icon_url: str = ""
    display_name: str = ""
    quote_token: str = ""


class PriceTracker:
    MAX_DIFF_RATIO = 0.5
    PERIOD = 60

    def __init__(self):
        self._states: dict[str, PriceState] = {}

    def update_price(self, pair: str, data: TickerData) -> PriceState:
        price_str = data.price
        percentage_str = data.percentage

        try:
            current_price = float(price_str)
        except ValueError:
            current_price = 0.0

        if pair not in self._states:
            self._states[pair] = PriceState(
                current_price=current_price, average_price=current_price
            )

        state = self._states[pair]

        state.average_price = (
            state.average_price * (self.PERIOD - 1) + current_price
        ) / self.PERIOD

        state.current_price = current_price
        state.percentage = percentage_str
        state.high_24h = data.high_24h
        state.low_24h = data.low_24h
        state.quote_volume_24h = data.quote_volume_24h

        state.icon_url = data.icon_url
        state.display_name = data.display_name
        state.quote_token = data.quote_token

        try:
            high = float(state.high_24h)
            low = float(state.low_24h)
            pct_val = float(percentage_str.strip("%").replace("+", "")) / 100.0

            if current_price > 0:
                open_price = current_price / (1 + pct_val)
                if open_price > 0:
                    amplitude = (high - low) / open_price * 100
                    state.amplitude_24h = f"{amplitude:.2f}%"
                else:
                    state.amplitude_24h = "0.00%"
            else:
                state.amplitude_24h = "0.00%"
        except (ValueError, ZeroDivisionError):
            state.amplitude_24h = "0.00%"

        from config.settings import get_settings_manager

        settings = get_settings_manager().settings
        is_standard = settings.color_schema == "standard"

        green = "#4CAF50"
        red = "#F44336"
        white = "#FFFFFF"

        if percentage_str.startswith("+"):
            state.color = green if is_standard else red
            state.trend = "↑"
        elif percentage_str.startswith("-"):
            state.color = red if is_standard else green
            state.trend = "↓"
        else:
            state.color = white
            state.trend = ""

        return state

    def _calculate_color(self, difference: float, avg_price: float) -> str:
        if avg_price == 0:
            return "hsl(0, 0%, 100%)"

        ratio = min(abs(difference / avg_price), self.MAX_DIFF_RATIO) / self.MAX_DIFF_RATIO

        if difference > 0:
            hue = 120
        elif difference < 0:
            hue = 0
        else:
            return "#333333"

        lightness = 80 - (ratio * 30)
        lightness = max(50, min(80, lightness))

        return f"hsl({hue}, 100%, {lightness}%)"

    def get_state(self, pair: str) -> PriceState | None:
        return self._states.get(pair)

    def clear_pair(self, pair: str):
        self._states.pop(pair, None)

    def clear_all(self):
        self._states.clear()


def hsl_to_qcolor(hsl_string: str) -> QColor:
    try:
        hsl_string = hsl_string.strip()
        if hsl_string.startswith("hsl(") and hsl_string.endswith(")"):
            values = hsl_string[4:-1].split(",")
            h = int(values[0].strip())
            s = int(values[1].strip().rstrip("%"))
            l_val = int(values[2].strip().rstrip("%"))

            color = QColor.fromHsl(
                h,
                int(s * 2.55),
                int(l_val * 2.55),
            )
            return color
    except (ValueError, IndexError):
        pass

    return QColor(255, 255, 255)


def percentage_color(percentage_str: str) -> QColor:
    if percentage_str.startswith("+"):
        return QColor(0x99, 0xFF, 0x99)
    elif percentage_str.startswith("-"):
        return QColor(0xFF, 0x99, 0x99)
    else:
        return QColor(0xFF, 0xFF, 0xFF)
