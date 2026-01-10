import json
import os
from unittest.mock import MagicMock, patch

import pytest

from config.settings import AppSettings, ProxyConfig, SettingsManager


class TestSettingsManager:
    @pytest.fixture
    def temp_config_dir(self, tmp_path):
        config_dir = tmp_path / "crypto-monitor"
        config_dir.mkdir()
        return config_dir

    @pytest.fixture
    def settings_manager(self, temp_config_dir):
        with patch("config.settings.SettingsManager.__init__", return_value=None):
            manager = SettingsManager()
            manager.config_dir = temp_config_dir
            manager.config_file = temp_config_dir / "settings.json"
            manager.settings = AppSettings()
            manager.migration_manager = MagicMock()
            manager.migration_manager.migrate_if_needed.return_value = (
                False,
                "No migration needed",
                None,
            )
            return manager

    def test_load_defaults_when_file_missing(self, settings_manager):
        if settings_manager.config_file.exists():
            settings_manager.config_file.unlink()

        settings = settings_manager.load(auto_migrate=False)

        assert isinstance(settings, AppSettings)
        assert settings.data_source == "OKX"
        assert settings.theme_mode == "light"

    def test_save_and_load_persistence(self, settings_manager):
        settings_manager.settings.data_source = "Binance"
        settings_manager.settings.theme_mode = "dark"
        settings_manager.settings.crypto_pairs = ["BTC-USDT"]

        settings_manager.save()

        assert settings_manager.config_file.exists()

        settings_manager.settings = AppSettings()
        loaded_settings = settings_manager.load(auto_migrate=False)

        assert loaded_settings.data_source == "Binance"
        assert loaded_settings.theme_mode == "dark"
        assert loaded_settings.crypto_pairs == ["BTC-USDT"]

    def test_add_remove_pairs(self, settings_manager):
        settings_manager.settings.crypto_pairs = []

        assert settings_manager.add_pair("BTC-USDT") is True
        assert "BTC-USDT" in settings_manager.settings.crypto_pairs

        assert settings_manager.add_pair("BTC-USDT") is False
        assert len(settings_manager.settings.crypto_pairs) == 1

        assert settings_manager.remove_pair("BTC-USDT") is True
        assert len(settings_manager.settings.crypto_pairs) == 0

        assert settings_manager.remove_pair("ETH-USDT") is False

    def test_load_handles_corrupted_file(self, settings_manager):
        with open(settings_manager.config_file, "w") as f:
            f.write("{invalid json")

        settings = settings_manager.load(auto_migrate=False)

        assert isinstance(settings, AppSettings)
        assert settings.data_source == "OKX"

    def test_proxy_update_applies_env(self, settings_manager):
        proxy = ProxyConfig(enabled=True, host="1.2.3.4", port=8080)

        with patch.dict("os.environ", clear=True):
            settings_manager.update_proxy(proxy)

            assert settings_manager.settings.proxy.host == "1.2.3.4"
            assert "HTTP_PROXY" in os.environ
            assert "http://1.2.3.4:8080" in os.environ["HTTP_PROXY"]

    def test_partial_config_load(self, settings_manager):
        partial_data = {
            "data_source": "Binance",
        }
        with open(settings_manager.config_file, "w") as f:
            json.dump(partial_data, f)

        settings = settings_manager.load(auto_migrate=False)

        assert settings.data_source == "Binance"
        assert settings.websocket.auto_reconnect is True
        assert settings.alerts == []
