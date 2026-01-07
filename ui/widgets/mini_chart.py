from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QBrush, QColor, QPen, QLinearGradient, QPainterPath
from PyQt6.QtCore import Qt, QPointF
from typing import List

class MiniChart(QWidget):
    """
    Minimalist line chart (Sparkline) for hover cards.
    Designed for high performance using native QPainter.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(60)
        self.setFixedWidth(200) # Match hover card width approx
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

        # 2. Determine Color
        start_price = self._data[0]
        end_price = self._data[-1]
        
        if end_price > start_price:
            base_color = self._color_up
        elif end_price < start_price:
            base_color = self._color_down
        else:
            base_color = self._neutral_color
            
        color = QColor(base_color)

        # 3. Geometry
        w = self.width()
        h = self.height()
        # Increased top padding as requested to give more space for labels
        padding_top = 22 
        padding_bottom = 15 # Space for MIN label
        padding_left = 5
        padding_right = 45 # Space for Right axis labels
        plot_h = h - padding_top - padding_bottom
        plot_w = w - padding_left - padding_right
        
        # Calculate points
        points = []
        step_x = plot_w / (len(self._data) - 1)
        
        for i, val in enumerate(self._data):
            x = padding_left + (i * step_x)
            normalized = (val - min_val) / range_val
            y = (h - padding_bottom) - (normalized * plot_h)
            points.append(QPointF(x, y))

        # 4. Draw Baseline (Start Price)
        # Calculate y for start price
        normalized_start = (start_price - min_val) / range_val
        y_start = (h - padding_bottom) - (normalized_start * plot_h)
        
        baseline_pen = QPen(QColor("#888888"))
        baseline_pen.setStyle(Qt.PenStyle.DashLine)
        baseline_pen.setWidth(1)
        painter.setPen(baseline_pen)
        painter.drawLine(int(padding_left), int(y_start), int(padding_left + plot_w), int(y_start))

        # 5. Draw Path (Line)
        path = QPainterPath()
        path.moveTo(points[0])
        for p in points[1:]:
            path.lineTo(p)
            
        pen = QPen(color)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawPath(path)

        # 6. Draw Gradient Fill
        fill_path = QPainterPath(path)
        fill_path.lineTo(padding_left + plot_w, h - padding_bottom)
        fill_path.lineTo(padding_left, h - padding_bottom)
        fill_path.closeSubpath()

        grad = QLinearGradient(0, padding_top, 0, h - padding_bottom)
        c_top = QColor(color)
        c_top.setAlpha(60) 
        grad.setColorAt(0, c_top)
        c_bottom = QColor(color)
        c_bottom.setAlpha(0) 
        grad.setColorAt(1, c_bottom)
        
        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(fill_path)
        
        # 7. Draw Labels
        painter.setPen(QColor(base_color))
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)
        
        # Max Label (Right aligned at top)
        painter.drawText(int(w - padding_right + 2), int(padding_top), f"{max_val:.2f}")
        
        # Min Label (Right aligned at bottom)
        painter.drawText(int(w - padding_right + 2), int(h - 2), f"{min_val:.2f}")
        
        # Period Label (Left aligned at top, bold)
        font.setBold(True)
        # Increase size for period label
        font.setPointSize(10)
        painter.setFont(font)
        painter.setPen(QColor(base_color))
        
        period_text = self._period
        painter.drawText(int(padding_left), int(padding_top - 2), period_text)
        
        # Draw Percentage Change
        # Calculate change
        pct_change = ((end_price - start_price) / start_price) * 100
        pct_text = f"{pct_change:+.2f}%"
        
        # Determine color for percentage
        from config.settings import get_settings_manager
        settings = get_settings_manager().settings
        color_up = "#4CAF50" if settings.color_schema == "standard" else "#F44336"
        color_down = "#F44336" if settings.color_schema == "standard" else "#4CAF50"
        
        pct_color = color_up if pct_change >= 0 else color_down
        
        painter.setPen(QColor(pct_color))
        
        # Measure period width to place pct next to it
        fm = painter.fontMetrics()
        period_width = fm.horizontalAdvance(period_text)
        
        # Use regular font
        font.setBold(False)
        font.setPointSize(8)
        painter.setFont(font)
        
        # Move percentage text up slightly to align visually with the larger period text
        painter.drawText(int(padding_left + period_width + 8), int(padding_top - 4), pct_text)


