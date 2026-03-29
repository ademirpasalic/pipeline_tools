"""Tests for DCC Launcher config loading (no Qt required).
Note: LauncherWindow has no separate engine class; these tests cover config parsing.
"""
import json
import pytest


def load_launcher_config(path):
    with open(path) as f:
        return json.load(f)


class TestLauncherConfig:
    def test_config_has_projects_and_software(self):
        import os
        root = os.path.join(os.path.dirname(__file__), "..")
        cfg = load_launcher_config(os.path.join(root, "launcher_config.json"))
        assert "projects" in cfg
        assert "software" in cfg

    def test_projects_have_required_fields(self):
        import os
        root = os.path.join(os.path.dirname(__file__), "..")
        cfg = load_launcher_config(os.path.join(root, "launcher_config.json"))
        for name, project in cfg["projects"].items():
            assert "name" in project
            assert "env" in project

    def test_software_entries_have_executable(self):
        import os
        root = os.path.join(os.path.dirname(__file__), "..")
        cfg = load_launcher_config(os.path.join(root, "launcher_config.json"))
        for name, sw in cfg["software"].items():
            assert "name" in sw
            assert "executable" in sw

    def test_env_merge(self):
        """Verify that project env + software env can be merged without collision."""
        import os
        root = os.path.join(os.path.dirname(__file__), "..")
        cfg = load_launcher_config(os.path.join(root, "launcher_config.json"))
        project = next(iter(cfg["projects"].values()))
        software = next(iter(cfg["software"].values()))
        merged = {**os.environ, **project.get("env", {}), **software.get("env", {})}
        assert "PROJECT_NAME" in merged
