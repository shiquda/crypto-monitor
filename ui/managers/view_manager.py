"""
View state management (Minimalist View, Animations, Resizing).
"""

import logging
import time

from PyQt6.QtCore import QEasingCurve, QObject, QPropertyAnimation, QTimer
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QGraphicsOpacityEffect, QMainWindow, QWidget

from config.settings import SettingsManager

logger = logging.getLogger(__name__)


class ViewManager(QObject):
    """Manages window appearance, animations, and minimalist mode."""

    def __init__(self, window: QMainWindow, settings_manager: SettingsManager):
        super().__init__(window)
        self._window = window
        self._settings_manager = settings_manager

        # State
        self._is_adjusting_height = False
        self._last_state_change_time = 0
        self._last_collapsed = None
        self._last_limit = None

        # Timers
        self._collapse_timer = QTimer(window)
        self._collapse_timer.setSingleShot(True)
        self._collapse_timer.timeout.connect(self._check_and_collapse)

        self._hover_polling_timer = QTimer(window)
        self._hover_polling_timer.setInterval(200)
        self._hover_polling_timer.timeout.connect(self._poll_minimalist_hover)
        self._hover_polling_timer.start()

    def setup_animations(self, toolbar: QWidget, pagination: QWidget):
        """Initialize animations and effects."""
        self._toolbar = toolbar
        self._pagination = pagination

        # Opacity effect for toolbar
        self.toolbar_opacity = QGraphicsOpacityEffect(toolbar)
        self.toolbar_opacity.setOpacity(1.0)
        toolbar.setGraphicsEffect(self.toolbar_opacity)

        self.toolbar_anim = QPropertyAnimation(self.toolbar_opacity, b"opacity")
        self.toolbar_anim.setDuration(250)
        self.toolbar_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        # Opacity effect for pagination
        self.pagination_opacity = QGraphicsOpacityEffect(pagination)
        self.pagination_opacity.setOpacity(1.0)
        pagination.setGraphicsEffect(self.pagination_opacity)

        self.pagination_anim = QPropertyAnimation(self.pagination_opacity, b"opacity")
        self.pagination_anim.setDuration(250)
        self.pagination_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        # Window height animation
        self.window_anim = QPropertyAnimation(self._window, b"geometry")
        self.window_anim.setDuration(250)
        self.window_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        # Initial state
        if self._settings_manager.settings.minimalist_view:
            self.toolbar_opacity.setOpacity(0.0)
            self.pagination_opacity.setOpacity(0.0)

    def adjust_window_height(self, limit: int = None, collapsed: bool = None):
        """Adjust window height with state locking and precise visibility management."""
        if self._is_adjusting_height:
            return

        if limit is None:
            limit = self._settings_manager.settings.display_limit

        is_minimalist = self._settings_manager.settings.minimalist_view
        if collapsed is None:
            pos = QCursor.pos()
            # If the window is not yet shown properly, geometry might be wrong,
            # but we assume this is called after init.
            collapsed = is_minimalist and not self._window.geometry().contains(pos)

        # Skip logic with state verification
        if self._last_collapsed == collapsed and limit == self._last_limit:
            # If we are expanded, ensure the toolbar hasn't drifted to hidden
            if not collapsed and self._toolbar.isHidden():
                pass  # Continue to fix it
            else:
                return

        self._is_adjusting_height = True
        try:
            self._last_collapsed = collapsed
            self._last_limit = limit

            # Precise dimensions
            CARD_H = 67
            CARD_SPACING = 8
            content_height = (limit * CARD_H) + (max(0, limit - 1) * CARD_SPACING)

            top_margin, bottom_margin = 7, 8
            layout_spacing = 5
            toolbar_h, pagination_h = 34, 34

            EXPANDED_TOP_GAP = top_margin + toolbar_h + layout_spacing
            EXPANDED_BOTTOM_GAP = layout_spacing + pagination_h + bottom_margin
            COLLAPSED_GAP = 8

            current_geom = self._window.geometry()
            target_w = 160

            if collapsed:
                target_h = content_height + (COLLAPSED_GAP * 2)

                # Shifting logic
                if not self._toolbar.isHidden():
                    dy = EXPANDED_TOP_GAP - COLLAPSED_GAP
                    new_y = current_geom.y() + dy
                else:
                    new_y = current_geom.y()

                self._toolbar.hide()
                self._pagination.hide()
                self._window.centralWidget().layout().setContentsMargins(
                    10, COLLAPSED_GAP, 10, COLLAPSED_GAP
                )
                self._window.centralWidget().layout().setSpacing(0)

                self.toolbar_anim.stop()
                self.toolbar_opacity.setOpacity(0.0)
                self.pagination_anim.stop()
                self.pagination_opacity.setOpacity(0.0)
            else:
                target_h = content_height + EXPANDED_TOP_GAP + EXPANDED_BOTTOM_GAP

                # Expand upwards
                if self._toolbar.isHidden():
                    dy = EXPANDED_TOP_GAP - COLLAPSED_GAP
                    new_y = current_geom.y() - dy
                else:
                    new_y = current_geom.y()

                self._toolbar.show()
                self._pagination.show()

                self.toolbar_anim.stop()
                self.toolbar_opacity.setOpacity(1.0)
                self.pagination_anim.stop()
                self.pagination_opacity.setOpacity(1.0)

                self._window.centralWidget().layout().setContentsMargins(
                    10, top_margin, 10, bottom_margin
                )
                self._window.centralWidget().layout().setSpacing(layout_spacing)

                self._toolbar.raise_()
                self._pagination.raise_()

            logger.debug(
                f"Setting window state: Collapsed={collapsed}, Limit={limit}, TotalH={target_h}"
            )

            if self._window.height() != int(target_h) or self._window.y() != int(new_y):
                self._window.setFixedSize(target_w, int(target_h))
                self._window.move(current_geom.x(), int(new_y))
                self._last_state_change_time = time.time()

            self._window.update()
        finally:
            self._is_adjusting_height = False

    def _poll_minimalist_hover(self):
        """Unified poll for minimalist state."""
        if not self._settings_manager.settings.minimalist_view:
            return

        if self._is_adjusting_height:
            return

        # Reduced cooldown
        if time.time() - self._last_state_change_time < 0.2:
            return

        pos = QCursor.pos()
        is_hovering = self._window.geometry().contains(pos)

        if is_hovering and self._toolbar.isHidden():
            self._collapse_timer.stop()
            self.adjust_window_height(collapsed=False)
        elif not is_hovering and not self._toolbar.isHidden():
            hysteresis_rect = self._window.geometry().adjusted(-5, -5, 5, 5)
            if not hysteresis_rect.contains(pos):
                if not self._collapse_timer.isActive():
                    self._collapse_timer.start(300)

    def _check_and_collapse(self):
        """Final check before collapsing window."""
        if not self._settings_manager.settings.minimalist_view:
            return

        pos = QCursor.pos()
        if not self._window.geometry().contains(pos):
            self.adjust_window_height(collapsed=True)

    def handle_enter_event(self):
        """Handle mouse enter."""
        if self._settings_manager.settings.minimalist_view:
            self._collapse_timer.stop()
            if self._toolbar.isHidden():
                self.adjust_window_height(collapsed=False)

    def handle_leave_event(self):
        """Handle mouse leave."""
        if self._settings_manager.settings.minimalist_view:
            pos = QCursor.pos()
            if not self._window.geometry().contains(pos):
                if not self._collapse_timer.isActive():
                    self._collapse_timer.start(300)

                if not self._toolbar.isHidden():
                    self.toolbar_anim.stop()
                    self.toolbar_anim.setEndValue(0.0)
                    self.toolbar_anim.start()
                    self.pagination_anim.stop()
                    self.pagination_anim.setEndValue(0.0)
                    self.pagination_anim.start()

    def reset_state(self):
        """Force reset of internal state (e.g. on settings change)."""
        self._last_collapsed = None
