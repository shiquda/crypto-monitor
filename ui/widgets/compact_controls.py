"""
Compact mode control widget with floating navigation buttons.
"""

from typing import Optional
from PyQt6.QtWidgets import QWidget, QHBoxLayout
from PyQt6.QtCore import pyqtSignal, Qt
from qfluentwidgets import TransparentToolButton, FluentIcon as FIF


class CompactControls(QWidget):
    """Control widget for compact mode with floating navigation buttons."""

    prev_clicked = pyqtSignal()  # Emitted when previous button is clicked
    next_clicked = pyqtSignal()  # Emitted when next button is clicked

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Setup the compact controls UI with floating buttons."""
        # Make widget transparent
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedHeight(40)

        # Layout with buttons positioned at left and right edges with minimal margin
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Left button (previous) - tiny size
        self.prev_button = TransparentToolButton(FIF.CARE_LEFT_SOLID, self)
        self.prev_button.setFixedSize(14, 14)
        self.prev_button.setToolTip("Previous Pair")
        self.prev_button.clicked.connect(self.prev_clicked)
        self.prev_button.setVisible(False)

        # Right button (next) - tiny size
        self.next_button = TransparentToolButton(FIF.CARE_RIGHT_SOLID, self)
        self.next_button.setFixedSize(14, 14)
        self.next_button.setToolTip("Next Pair")
        self.next_button.clicked.connect(self.next_clicked)
        self.next_button.setVisible(False)

        layout.addWidget(self.prev_button)
        layout.addStretch()
        layout.addWidget(self.next_button)

    def show_controls(self):
        """Show all floating controls."""
        self.prev_button.setVisible(True)
        self.next_button.setVisible(True)

    def hide_controls(self):
        """Hide all floating controls."""
        self.prev_button.setVisible(False)
        self.next_button.setVisible(False)
