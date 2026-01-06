"""
Toolbar widget with window controls using Fluent Design.
"""

from typing import Optional
from PyQt6.QtWidgets import QWidget, QHBoxLayout
from PyQt6.QtCore import pyqtSignal, Qt
from qfluentwidgets import TransparentToolButton, FluentIcon as FIF


from core.i18n import _

class Toolbar(QWidget):
    """Toolbar with application control buttons."""

    settings_clicked = pyqtSignal()
    add_clicked = pyqtSignal()
    minimize_clicked = pyqtSignal()
    pin_clicked = pyqtSignal(bool)  # Emits new pin state
    close_clicked = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._pinned = False
        self._setup_ui()

    def _setup_ui(self):
        """Setup toolbar UI with Fluent Design components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(4)

        # Center the buttons
        layout.addStretch()

        # Settings button - using Fluent Icon
        self.settings_btn = TransparentToolButton(FIF.SETTING, self)
        self.settings_btn.setFixedSize(24, 24)
        self.settings_btn.setToolTip(_("Settings"))
        self.settings_btn.clicked.connect(self.settings_clicked)
        layout.addWidget(self.settings_btn)

        # Add pair button - using Fluent Icon
        self.add_btn = TransparentToolButton(FIF.ADD, self)
        self.add_btn.setFixedSize(24, 24)
        self.add_btn.setToolTip(_("Add Pair"))
        self.add_btn.clicked.connect(self.add_clicked)
        layout.addWidget(self.add_btn)

        # Minimize button - using Fluent Icon
        self.minimize_btn = TransparentToolButton(FIF.MINIMIZE, self)
        self.minimize_btn.setFixedSize(24, 24)
        self.minimize_btn.setToolTip(_("Minimize"))
        self.minimize_btn.clicked.connect(self.minimize_clicked)
        layout.addWidget(self.minimize_btn)

        # Pin button - using Fluent Icon
        self.pin_btn = TransparentToolButton(FIF.PIN, self)
        self.pin_btn.setFixedSize(24, 24)
        self.pin_btn.setToolTip(_("Pin Window"))
        self.pin_btn.clicked.connect(self._toggle_pin)
        layout.addWidget(self.pin_btn)

        # Close button - using Fluent Icon
        self.close_btn = TransparentToolButton(FIF.CLOSE, self)
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.setToolTip(_("Close"))
        self.close_btn.clicked.connect(self.close_clicked)
        layout.addWidget(self.close_btn)

        layout.addStretch()

    def _toggle_pin(self):
        """Toggle pin state."""
        self._pinned = not self._pinned
        # Update icon based on pin state
        self.pin_btn.setIcon(FIF.UNPIN if self._pinned else FIF.PIN)
        self.pin_btn.setToolTip(_("Unpin Window") if self._pinned else _("Pin Window"))
        self.pin_clicked.emit(self._pinned)

    def is_pinned(self) -> bool:
        """Check if window is pinned."""
        return self._pinned
