"""
Toolbar widget with window controls.
"""

from typing import Optional
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PyQt6.QtCore import pyqtSignal, Qt


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
        """Setup toolbar UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        # Center the buttons
        layout.addStretch()

        # Settings button
        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setObjectName("toolbarButton")
        self.settings_btn.setToolTip("Settings")
        self.settings_btn.clicked.connect(self.settings_clicked)
        layout.addWidget(self.settings_btn)

        # Add pair button
        self.add_btn = QPushButton("+")
        self.add_btn.setObjectName("toolbarButton")
        self.add_btn.setToolTip("Add Pair")
        self.add_btn.clicked.connect(self.add_clicked)
        layout.addWidget(self.add_btn)

        # Minimize button
        self.minimize_btn = QPushButton("−")
        self.minimize_btn.setObjectName("toolbarButton")
        self.minimize_btn.setToolTip("Minimize")
        self.minimize_btn.clicked.connect(self.minimize_clicked)
        layout.addWidget(self.minimize_btn)

        # Pin button
        self.pin_btn = QPushButton("📌")
        self.pin_btn.setObjectName("toolbarButton")
        self.pin_btn.setToolTip("Pin Window")
        self.pin_btn.clicked.connect(self._toggle_pin)
        layout.addWidget(self.pin_btn)

        # Close button
        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("toolbarButton")
        self.close_btn.setToolTip("Close")
        self.close_btn.clicked.connect(self.close_clicked)
        layout.addWidget(self.close_btn)

        layout.addStretch()

        # Style buttons
        for btn in [self.settings_btn, self.add_btn, self.minimize_btn,
                    self.pin_btn, self.close_btn]:
            btn.setFixedSize(24, 24)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton#toolbarButton {
                    background: transparent;
                    border: none;
                    color: #FFFFFF;
                    font-size: 14px;
                }
                QPushButton#toolbarButton:hover {
                    background: rgba(255, 255, 255, 0.1);
                    border-radius: 4px;
                }
            """)

    def _toggle_pin(self):
        """Toggle pin state."""
        self._pinned = not self._pinned
        self.pin_btn.setText("📍" if self._pinned else "📌")
        self.pin_btn.setToolTip("Unpin Window" if self._pinned else "Pin Window")
        self.pin_clicked.emit(self._pinned)

    def is_pinned(self) -> bool:
        """Check if window is pinned."""
        return self._pinned
