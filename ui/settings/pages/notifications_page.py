from PyQt6.QtWidgets import QWidget, QVBoxLayout
from qfluentwidgets import SettingCardGroup, ScrollArea
from ui.widgets.alert_setting_card import AlertSettingCard
from core.i18n import _

class NotificationsPage(QWidget):
    """Notifications settings page."""
    
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
        
        self.alerts_group = SettingCardGroup(_("Notifications"), self.scroll_content)
        self.alerts_card = AlertSettingCard(self.alerts_group)
        self.alerts_group.addSettingCard(self.alerts_card)
        
        self.scroll_layout.addWidget(self.alerts_group)
        self.scroll_layout.addStretch(1)
        
        self.scroll.setWidget(self.scroll_content)
        self.layout.addWidget(self.scroll)
