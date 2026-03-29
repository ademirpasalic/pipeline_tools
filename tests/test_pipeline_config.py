"""Tests for ConfigManager (no Qt required)."""
import json
import pytest
from pipeline_config import ConfigManager, DEFAULT_PIPELINE_CONFIG


class TestConfigManager:
    def test_loads_default_config(self, tmp_path):
        cm = ConfigManager(str(tmp_path / "config.json"))
        assert cm.config["pipeline"]["studio"] == DEFAULT_PIPELINE_CONFIG["pipeline"]["studio"]

    def test_save_and_reload_json(self, tmp_path):
        path = str(tmp_path / "config.json")
        cm = ConfigManager(path)
        cm.config["pipeline"]["studio"] = "Test Studio"
        cm.save(path)
        cm2 = ConfigManager(path)
        assert cm2.config["pipeline"]["studio"] == "Test Studio"

    def test_get_value(self, tmp_path):
        cm = ConfigManager(str(tmp_path / "config.json"))
        val = cm.get("pipeline.studio")
        assert val == DEFAULT_PIPELINE_CONFIG["pipeline"]["studio"]

    def test_set_value(self, tmp_path):
        cm = ConfigManager(str(tmp_path / "config.json"))
        cm.set("pipeline.studio", "New Studio")
        assert cm.get("pipeline.studio") == "New Studio"

    def test_resolve_path_template(self, tmp_path):
        cm = ConfigManager(str(tmp_path / "config.json"))
        resolved = cm.resolve_path("paths.asset_root", project="my_proj", asset_type="char", asset_name="hero")
        assert "my_proj" in resolved
        assert "hero" in resolved

    def test_validate_returns_list(self, tmp_path):
        cm = ConfigManager(str(tmp_path / "config.json"))
        issues = cm.validate()
        assert isinstance(issues, list)
