"""
Window behavior implementation (e.g., dragging).
"""

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QWidget


class DraggableWindowBehavior:
    """Mixin to enable window dragging for frameless windows."""

    def __init__(self, window: QWidget):
        self._window = window
        self._drag_pos: QPoint | None = None

    def mouse_press_event(self, event: QMouseEvent):
        """Handle mouse press for window dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint() - self._window.frameGeometry().topLeft()
            )

    def mouse_move_event(self, event: QMouseEvent):
        """Handle mouse move for window dragging."""
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self._window.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouse_release_event(self, event: QMouseEvent):
        """Handle mouse release."""
        self._drag_pos = None
