from PyQt6.QtCore import Qt
from qfluentwidgets import ComboBox, SettingCard
from qfluentwidgets import FluentIcon as FIF

from config.settings import get_settings_manager
from core.i18n import _


class DataSourceSettingCard(SettingCard):
    """Setting card for selecting cryptocurrency data source."""

    def __init__(self, parent=None):
        super().__init__(
            FIF.SYNC,
            _("Data Source"),
            _("Select the exchange for real-time data"),
            parent,
        )

        self.combo = ComboBox(self)
        self.combo.addItem("OKX", "OKX")
        self.combo.addItem("Binance", "Binance")

        self.hBoxLayout.addWidget(self.combo, 0, Qt.AlignmentFlag.AlignRight)
        self.hBoxLayout.addSpacing(16)

        self._load_setting()
        self.combo.currentIndexChanged.connect(self._on_changed)

    def _load_setting(self):
        settings = get_settings_manager().settings
        source = settings.data_source
        if source.upper() == "BINANCE":
            self.combo.setCurrentIndex(1)
        else:
            self.combo.setCurrentIndex(0)

    def _on_changed(self, index):
        # We don't save immediately here, we let the save button in settings window handle it
        # But wait, SettingsWindow logic is "Save Button" -> collect data.
        pass

    def get_data_source(self) -> str:
        return self.combo.currentText()  # "OKX" or "Binance"

    def set_data_source(self, source: str):
        if source.upper() == "BINANCE":
            self.combo.setCurrentIndex(1)
        else:
            self.combo.setCurrentIndex(0)
