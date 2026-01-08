import webbrowser
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import pyqtSignal, QUrl
from PyQt6.QtGui import QDesktopServices
from qfluentwidgets import SettingCardGroup, ScrollArea, PrimaryPushSettingCard, FluentIcon, InfoBar, InfoBarPosition, MessageBox
from core.i18n import _
from core.version import __version__

class AboutPage(QWidget):
    """About settings page."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        
    def _setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        self.scroll = ScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(30, 30, 30, 30)
        self.scroll_layout.setSpacing(20)
        
        self.about_group = SettingCardGroup(_("About"), self.scroll_content)
        
        # Version Card
        self.version_card = PrimaryPushSettingCard(
            _("Check Update"),
            FluentIcon.INFO,
            _("Current Version"),
            __version__,
            self.about_group
        )
        self.version_card.button.clicked.connect(self._check_for_updates)
        self.about_group.addSettingCard(self.version_card)
        
        # GitHub Card
        self.github_card = PrimaryPushSettingCard(
            _("View"),
            FluentIcon.GITHUB,
            _("GitHub Repository"),
            _("View source code, report issues, or contribute"),
            self.about_group
        )
        self.github_card.button.clicked.connect(lambda: webbrowser.open("https://github.com/shiquda/crypto-monitor"))
        self.about_group.addSettingCard(self.github_card)
        
        # Log Directory Card
        self.app_dir_card = PrimaryPushSettingCard(
            _("Open"),
            FluentIcon.FOLDER,
            _("Log Directory"),
            _("Open the logs directory"),
            self.about_group
        )
        self.app_dir_card.button.clicked.connect(self._open_log_directory)
        self.about_group.addSettingCard(self.app_dir_card)
        
        self.scroll_layout.addWidget(self.about_group)
        self.scroll_layout.addStretch(1)
        
        self.scroll.setWidget(self.scroll_content)
        self.layout.addWidget(self.scroll)

    def _open_log_directory(self):
        """Open the application log directory in file explorer."""
        import os
        from pathlib import Path
        
        if os.name == 'nt':  # Windows
            log_dir = Path(os.environ.get('APPDATA', '')) / 'crypto-monitor' / 'logs'
        else:  # Linux/Mac
            log_dir = Path.home() / '.config' / 'crypto-monitor' / 'logs'
            
        if not log_dir.exists():
            log_dir.mkdir(parents=True, exist_ok=True)
            
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(log_dir)))

    def _check_for_updates(self):
        """Check for updates."""
        self.version_card.button.setEnabled(False)
        self.version_card.button.setText(_("Checking..."))
        
        from core.update_checker import UpdateChecker
        
        self._update_checker = UpdateChecker(__version__, self)
        self._update_checker.update_available.connect(self._on_update_available)
        self._update_checker.up_to_date.connect(self._on_up_to_date)
        self._update_checker.check_failed.connect(self._on_check_failed)
        self._update_checker.finished.connect(lambda: self.version_card.button.setEnabled(True))
        # Wait, if I set text back here, it might conflict if up_to_date also sets it? 
        # Actually usually we revert text or leave it. 
        # Original code: self.version_card.button.setText(_("Check Update"))
        self._update_checker.finished.connect(lambda: self.version_card.button.setText(_("Check Update")))
        self._update_checker.start()

    def _on_update_available(self, release_info: dict):
        tag_name = release_info.get("tag_name", "Unknown")
        html_url = release_info.get("html_url", "")
        
        w = MessageBox(
            _("New Version Available"),
            f"{_('Version')} {tag_name} {_('is available.')}",
            self.window() # Use window() to safely get parent window
        )
        w.yesButton.setText(_("Go to Download"))
        w.cancelButton.setText(_("Cancel"))
        
        if w.exec():
            QDesktopServices.openUrl(QUrl(html_url))

    def _on_up_to_date(self, version: str):
        InfoBar.success(
            title=_("Up to Date"),
            content=f"{_('You are using the latest version')} ({version})",
            orient=0,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self.window()
        )

    def _on_check_failed(self, error: str):
        InfoBar.error(
            title=_("Check Failed"),
            content=f"{_('Failed to check for updates')}: {error}",
            orient=0,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self.window()
        )
