"""
Toolbar widget with window controls using Fluent Design.
"""

from typing import Optional
from PyQt6.QtWidgets import QWidget, QHBoxLayout
from PyQt6.QtCore import pyqtSignal, Qt
from qfluentwidgets import TransparentToolButton, FluentIcon as FIF


class Toolbar(QWidget):
    """Toolbar with application control buttons."""

    settings_clicked = pyqtSignal()
    pin_clicked = pyqtSignal(bool)  # Emits new pin state
    close_clicked = pyqtSignal()
    compact_mode_toggled = pyqtSignal(bool)  # Emits when compact mode is toggled

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._pinned = False
        self._compact_mode = False
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
        self.settings_btn.setToolTip("Settings")
        self.settings_btn.clicked.connect(self.settings_clicked)
        layout.addWidget(self.settings_btn)

        # Compact/Normal mode toggle button
        self.mode_btn = TransparentToolButton(FIF.MINIMIZE, self)
        self.mode_btn.setFixedSize(24, 24)
        self.mode_btn.setToolTip("Switch to Compact Mode")
        self.mode_btn.clicked.connect(self._toggle_mode)
        layout.addWidget(self.mode_btn)

        # Pin button - using Fluent Icon
        self.pin_btn = TransparentToolButton(FIF.PIN, self)
        self.pin_btn.setFixedSize(24, 24)
        self.pin_btn.setToolTip("Pin Window")
        self.pin_btn.clicked.connect(self._toggle_pin)
        layout.addWidget(self.pin_btn)

        # Close button - using Fluent Icon
        self.close_btn = TransparentToolButton(FIF.CLOSE, self)
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.setToolTip("Close")
        self.close_btn.clicked.connect(self.close_clicked)
        layout.addWidget(self.close_btn)

        layout.addStretch()

    def _toggle_pin(self):
        """Toggle pin state."""
        self._pinned = not self._pinned
        # Update icon based on pin state
        self.pin_btn.setIcon(FIF.UNPIN if self._pinned else FIF.PIN)
        self.pin_btn.setToolTip("Unpin Window" if self._pinned else "Pin Window")
        self.pin_clicked.emit(self._pinned)

    def _toggle_mode(self):
        """Toggle between compact and normal mode."""
        self._compact_mode = not self._compact_mode
        # Update icon and tooltip based on mode
        if self._compact_mode:
            self.mode_btn.setIcon(FIF.UP)
            self.mode_btn.setToolTip("Switch to Normal Mode")
        else:
            self.mode_btn.setIcon(FIF.MINIMIZE)
            self.mode_btn.setToolTip("Switch to Compact Mode")
        self.compact_mode_toggled.emit(self._compact_mode)

    def set_compact_mode(self, enabled: bool):
        """Set the compact mode state."""
        self._compact_mode = enabled
        if enabled:
            self.mode_btn.setIcon(FIF.UP)
            self.mode_btn.setToolTip("Switch to Normal Mode")
        else:
            self.mode_btn.setIcon(FIF.MINIMIZE)
            self.mode_btn.setToolTip("Switch to Compact Mode")

    def is_pinned(self) -> bool:
        """Check if window is pinned."""
        return self._pinned
