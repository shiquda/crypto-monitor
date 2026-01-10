"""
Crypto Monitor - PyQt6 Desktop Application
Main entry point.
"""

import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from config.settings import get_settings_manager
from core.logger import setup_logging
from ui.main_window import MainWindow

setup_logging()


def main():
    """Main application entry point."""
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Crypto Monitor")

    from core.version import __version__

    app.setApplicationVersion(__version__)

    # Load settings (which initializes language loader)
    settings_manager = get_settings_manager()
    if settings_manager.settings.proxy.enabled:
        settings_manager._apply_proxy_env()

    # Create and show main window
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
