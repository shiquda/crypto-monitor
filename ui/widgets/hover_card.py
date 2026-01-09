from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QLabel,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.i18n import _
from ui.widgets.mini_chart import MiniChart


class HoverCard(QWidget):
    """
    Custom hover card widget for displaying extended crypto data.
    Designed to match the Fluent Design style of the main application.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        # Use ToolTip window type to allow floating above other widgets
        # FramelessWindowHint removes OS borders
        self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self._setup_ui()

    def _setup_ui(self):
        # Main container with background
        self.container = QWidget(self)
        self.container.setObjectName("container")

        # Determine theme-based colors (Defaulting to light/dark detection logic later,
        # or accepting it via method. For now, we'll try to be somewhat dynamic or
        # let the styles be set by the caller/theme manager).
        # We'll set a base style here.

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)  # Margin for shadow
        self.layout.addWidget(self.container)

        # Internal layout
        self.content_layout = QVBoxLayout(self.container)
        self.content_layout.setContentsMargins(12, 12, 12, 12)
        self.content_layout.setSpacing(6)

        # Labels
        self.high_label = self._create_label()
        self.low_label = self._create_label()
        self.amplitude_label = self._create_label()
        self.vol_label = self._create_label()

        self.content_layout.addWidget(self.high_label)
        self.content_layout.addWidget(self.low_label)
        # Add amplitude between Low and Volume
        self.content_layout.addWidget(self.amplitude_label)
        self.content_layout.addWidget(self.vol_label)

        # Chart Section
        self.chart_container = QStackedWidget()
        self.chart_container.setFixedHeight(60)

        # 1. Loading state
        self.loading_label = QLabel(_("Loading Chart..."))
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet("color: #888888; font-size: 10px;")
        self.chart_container.addWidget(self.loading_label)

        # 2. Chart widget
        self.mini_chart = MiniChart()
        self.chart_container.addWidget(self.mini_chart)

        self.content_layout.addWidget(self.chart_container)

        # Shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 2)
        self.container.setGraphicsEffect(shadow)

    def _create_label(self) -> QLabel:
        label = QLabel()
        # Initial style, can be overridden by theme update
        label.setStyleSheet("font-family: 'Microsoft YaHei', sans-serif; font-size: 11px;")
        return label

    def update_data(
        self,
        high: str,
        low: str,
        volume: str,
        quote_currency: str,
        amplitude: str = "0.00%",
    ):
        """Update the displayed data."""
        # Use bold for keys
        self.high_label.setText(f"<b>{_('24h High')}:</b> {high}")
        self.low_label.setText(f"<b>{_('24h Low')}:</b> {low}")
        self.amplitude_label.setText(f"<b>{_('24h Amplitude')}:</b> {amplitude}")
        self.vol_label.setText(
            f"<b>{_('24h Vol')}:</b> {self._format_volume(volume)} {quote_currency}"
        )

        # Adjust size to fit content
        # Adjust size to fit content
        self.adjustSize()

    def update_chart(self, data: list[float], period: str = "24H", error: str = None):
        """Update the mini chart with historical data."""
        if error:
            self.chart_container.setCurrentWidget(self.loading_label)
            self.loading_label.setText(f"Error: {error}")
            self.loading_label.setToolTip(error)  # Show full error on hover
            return

        if not data:
            self.chart_container.setCurrentWidget(self.loading_label)
            self.loading_label.setText(_("No Data"))
            return

        self.mini_chart.set_data(data, period)
        self.chart_container.setCurrentWidget(self.mini_chart)

    def set_chart_loading(self):
        """Show loading state for chart."""
        self.chart_container.setCurrentWidget(self.loading_label)
        self.loading_label.setText(_("Loading Chart..."))

    def set_visibility(self, show_stats: bool, show_chart: bool):
        """Set visibility of components."""
        # Stats labels
        stats_widgets = [
            self.high_label,
            self.low_label,
            self.vol_label,
            self.amplitude_label,
        ]
        for w in stats_widgets:
            w.setVisible(show_stats)

        # Chart
        self.chart_container.setVisible(show_chart)

        # Adjust size immediately
        self.adjustSize()

    def update_theme(self, theme_mode: str):
        """Update style based on theme."""
        if theme_mode == "dark":
            bg_color = "#2D3B4E"  # Slightly lighter than main bg #1B2636
            text_color = "#FFFFFF"
            border_color = "rgba(255, 255, 255, 0.08)"
        else:
            bg_color = "#FFFFFF"
            text_color = "#333333"
            border_color = "rgba(0, 0, 0, 0.05)"

        self.container.setStyleSheet(f"""
            QWidget#container {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 8px;
            }}
            QLabel {{
                color: {text_color};
            }}
        """)

    def _format_volume(self, volume_str: str) -> str:
        """Format volume with K/M/B suffixes."""
        try:
            vol = float(volume_str)
        except ValueError:
            return volume_str

        if vol >= 1_000_000_000:
            return f"{vol / 1_000_000_000:.2f}B"
        elif vol >= 1_000_000:
            return f"{vol / 1_000_000:.2f}M"
        elif vol >= 1_000:
            return f"{vol / 1_000:.2f}K"
        else:
            return f"{vol:.2f}"
