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
        self.combo.addItem(_("OKX"), userData="OKX")
        self.combo.addItem(_("OKX_swap"), userData="OKX_MARK")
        self.combo.addItem(_("Binance"), userData="BINANCE")
        self.combo.addItem(_("Binance_swap"), userData="BINANCE_MARK")
        self.combo.addItem(_("GATE"), userData="GATE")
        self.combo.addItem(_("GATE_swap"), userData="GATE_MARK")

        self.hBoxLayout.addWidget(self.combo, 0, Qt.AlignmentFlag.AlignRight)
        self.hBoxLayout.addSpacing(16)

        self._load_setting()
        self.combo.currentIndexChanged.connect(self._on_changed)

    def _load_setting(self):
        settings = get_settings_manager().settings
        self.set_data_source(settings.data_source)

    def _on_changed(self, index):
        # We don't save immediately here, we let the save button in settings window handle it
        # But wait, SettingsWindow logic is "Save Button" -> collect data.
        pass

    def get_data_source(self) -> str:
        value = self.combo.currentData()
        if isinstance(value, str) and value:
            return value.upper()

        index_to_source = {
            0: "OKX",
            1: "OKX_MARK",
            2: "BINANCE",
            3: "BINANCE_MARK",
            4: "GATE",
            5: "GATE_MARK",
        }
        return index_to_source.get(self.combo.currentIndex(), "OKX")

    def set_data_source(self, source: str):
        source_upper = (source or "").upper()
        index = self.combo.findData(source_upper)
        if index >= 0:
            self.combo.setCurrentIndex(index)
            return

        index_map = {
            "OKX": 0,
            "OKX_MARK": 1,
            "OKX_SWAP": 1,
            "BINANCE": 2,
            "BINANCE_MARK": 3,
            "BINANCE_SWAP": 3,
            "GATE": 4,
            "GATE_MARK": 5,
            "GATE_SWAP": 5,
        }
        self.combo.setCurrentIndex(index_map.get(source_upper, 0))
