from PyQt6.QtWidgets import QWidget, QVBoxLayout
from qfluentwidgets import SettingCardGroup, ScrollArea
from ui.widgets.setting_cards import LanguageSettingCard, DisplaySettingCard, HoverSettingCard
from core.i18n import _

class AppearancePage(QWidget):
    """Appearance settings page."""
    
    def __init__(self, settings_group, parent=None):
        super().__init__(parent)
        self.settings_group = settings_group
        self._setup_ui()
        
    def _setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Scroll Area
        self.scroll = ScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(30, 30, 30, 30)
        self.scroll_layout.setSpacing(20)
        
        # Appearance Group
        self.appearance_group = SettingCardGroup(_("Appearance"), self.scroll_content)
        
        from ui.widgets.setting_cards import ThemeSettingCard
        self.theme_card = ThemeSettingCard(self.appearance_group)
        self.appearance_group.addSettingCard(self.theme_card)
        
        self.language_card = LanguageSettingCard(self.appearance_group)
        self.appearance_group.addSettingCard(self.language_card)
        
        self.hover_card = HoverSettingCard(self.appearance_group)
        self.appearance_group.addSettingCard(self.hover_card)
        
        self.display_card = DisplaySettingCard(self.appearance_group)
        self.appearance_group.addSettingCard(self.display_card)
        
        self.scroll_layout.addWidget(self.appearance_group)
        self.scroll_layout.addStretch(1)
        
        self.scroll.setWidget(self.scroll_content)
        self.layout.addWidget(self.scroll)
