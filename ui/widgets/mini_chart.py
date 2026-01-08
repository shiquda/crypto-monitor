from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QBrush, QColor, QPen, QLinearGradient, QPainterPath
from PyQt6.QtCore import Qt, QPointF, QRectF
from typing import List

class MiniChart(QWidget):
    """
    Minimalist line chart (Sparkline) for hover cards.
    Designed for high performance using native QPainter.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(60)
        self.setFixedWidth(220) # Increased width for better visibility
        self._data: List[float] = []
        self._color_up = "#4CAF50"
        self._color_down = "#F44336"
        self._neutral_color = "#888888"
        
        # Transparent background for widget itself, drawing will be overlay
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._period = "24H"

    def set_data(self, data: List[float], period: str = "24H"):
        """Update chart data."""
        self._data = data
        self._period = period
        self.update() # Trigger repaint

    def paintEvent(self, event):
        if not self._data or len(self._data) < 2:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. Determine Range
        min_val = min(self._data)
        max_val = max(self._data)
        range_val = max_val - min_val
        
        if range_val == 0:
            range_val = 1 # Avoid division by zero

        # Format labels first to determine padding
        from core.utils import format_price
        max_str = format_price(max_val)
        min_str = format_price(min_val)
        
        # Calculate required padding for labels
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)
        fm = painter.fontMetrics()
        
        max_w = fm.horizontalAdvance(max_str)
        min_w = fm.horizontalAdvance(min_str)
        required_padding = max(max_w, min_w) + 8 # Add margin
        
        # 2. Geometry
        w = self.width()
        h = self.height()
        padding_top = 22 
        padding_bottom = 15 
        padding_left = 5
        padding_right = max(45, required_padding) # Dynamic padding, minimum 45
        
        plot_h = h - padding_top - padding_bottom
        plot_w = w - padding_left - padding_right
        
        # 3. Calculate points and start line Y
        start_price = self._data[0]
        end_price = self._data[-1]
        
        normalized_start = (start_price - min_val) / range_val
        y_start = (h - padding_bottom) - (normalized_start * plot_h)
        
        points = []
        step_x = plot_w / (len(self._data) - 1)
        
        for i, val in enumerate(self._data):
            x = padding_left + (i * step_x)
            normalized = (val - min_val) / range_val
            y = (h - padding_bottom) - (normalized * plot_h)
            points.append(QPointF(x, y))

        # 4. Helper function to draw chart segments
        def draw_segment(clip_rect, color_hex, is_top=True):
            painter.save()
            painter.setClipRect(clip_rect)
            
            c = QColor(color_hex)
            pen = QPen(c)
            pen.setWidth(2)
            painter.setPen(pen)
            
            # Draw Line
            path = QPainterPath()
            if points:
                path.moveTo(points[0])
                for p in points[1:]:
                    path.lineTo(p)
            painter.drawPath(path)
            
            # Draw Gradient Fill
            fill_path = QPainterPath(path)
            # Close path to the baseline (y_start)
            fill_path.lineTo(padding_left + plot_w, y_start)
            fill_path.lineTo(padding_left, y_start)
            fill_path.closeSubpath()

            grad = QLinearGradient(0, padding_top, 0, h - padding_bottom)
            c_fill_start = QColor(c)
            c_fill_start.setAlpha(60)
            c_fill_end = QColor(c)
            c_fill_end.setAlpha(10) # Less transparent at bottom for visibility
            
            # Adjust gradient based on whether it's top or bottom segment for better visual
            if is_top:
                 grad.setColorAt(0, c_fill_start)
                 grad.setColorAt(1, c_fill_end)
            else:
                 grad.setColorAt(0, c_fill_end)
                 grad.setColorAt(1, c_fill_start)

            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPath(fill_path)
            
            painter.restore()

        # 5. Draw Baseline (Dashed)
        baseline_pen = QPen(QColor("#888888"))
        baseline_pen.setStyle(Qt.PenStyle.DashLine)
        baseline_pen.setWidth(1)
        painter.setPen(baseline_pen)
        painter.drawLine(int(padding_left), int(y_start), int(padding_left + plot_w), int(y_start))

        # 6. Draw Segments (Split Coloring)
        from config.settings import get_settings_manager
        settings = get_settings_manager().settings
        # Define colors based on settings
        color_up_hex = "#4CAF50" if settings.color_schema == "standard" else "#F44336"
        color_down_hex = "#F44336" if settings.color_schema == "standard" else "#4CAF50"
        
        # Rect for top part (Above start price -> Green/UpColor)
        # Note: In Qt coords, smaller Y is higher up. 
        # So "above" y_start is rect(0, 0, w, y_start)
        rect_top = QRectF(0, 0, w, y_start)
        draw_segment(rect_top, color_up_hex, is_top=True)
        
        # Rect for bottom part (Below start price -> Red/DownColor)
        # "below" y_start is rect(0, y_start, w, h - y_start)
        rect_bottom = QRectF(0, y_start, w, h - y_start)
        draw_segment(rect_bottom, color_down_hex, is_top=False)

        # 7. Draw Labels (Keep existing logic for Colors)
        
        # Determine overall trend color for text
        pct_change = ((end_price - start_price) / start_price) * 100
        text_color_hex = color_up_hex if pct_change >= 0 else color_down_hex
        
        painter.setPen(QColor(text_color_hex))
        
        # Max Label (Right Aligned)
        # Use calculate padded position or align to right edge minus margin
        # Align to the right side of the widget, regardless of padding_right logic used for chart
        # Because we expanded chart padding to fit this text.
        
        painter.drawText(int(w - max_w - 2), int(padding_top), max_str)
        
        # Min Label
        painter.drawText(int(w - min_w - 2), int(h - 2), min_str)
        
        # Period Label
        font.setBold(True)
        font.setPointSize(10)
        painter.setFont(font)
        painter.drawText(int(padding_left), int(padding_top - 2), self._period)
        
        # Percentage Change
        pct_text = f"{pct_change:+.2f}%"
        fm = painter.fontMetrics()
        period_width = fm.horizontalAdvance(self._period)
        
        font.setBold(False)
        font.setPointSize(8)
        painter.setFont(font)
        painter.drawText(int(padding_left + period_width + 8), int(padding_top - 4), pct_text)


