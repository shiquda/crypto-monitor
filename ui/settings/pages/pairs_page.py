from PyQt6.QtWidgets import QWidget, QVBoxLayout
from qfluentwidgets import SettingCardGroup, ScrollArea
from ui.widgets.setting_cards import PairsSettingCard
from core.i18n import _

class PairsPage(QWidget):
    """Trading Pairs settings page."""
    
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
        
        self.pairs_group = SettingCardGroup(_("Trading Pairs"), self.scroll_content)
        self.pairs_card = PairsSettingCard(self.pairs_group)
        self.pairs_group.addSettingCard(self.pairs_card)
        
        self.scroll_layout.addWidget(self.pairs_group)
        self.scroll_layout.addStretch(1)
        
        self.scroll.setWidget(self.scroll_content)
        self.layout.addWidget(self.scroll)
        
    def set_pairs(self, pairs):
        self.pairs_card.set_pairs(pairs)
        
    def get_pairs(self):
        return self.pairs_card.get_pairs()
