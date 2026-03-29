"""
Per-tool settings persistence using QSettings.

Usage:
    from shared.settings import AppSettings

    settings = AppSettings("asset_validator")
    settings.set("last_path", "/projects/foo")
    settings.save_geometry(self)          # call in closeEvent

    # On next launch:
    last = settings.get("last_path", "")
    settings.restore_geometry(self)       # call after show()
"""
from typing import Any

try:
    from PySide6 import QtCore, QtWidgets
except ImportError:
    from PyQt5 import QtCore, QtWidgets


class AppSettings:
    """Thin wrapper around QSettings scoped to a single tool.

    Data is stored in the platform-native location (registry on Windows,
    plist on macOS, INI file on Linux) under the organisation
    "pipeline_tools/<tool_name>".

    Args:
        tool_name: Unique short name for the tool (e.g. "asset_validator").
    """

    def __init__(self, tool_name: str) -> None:
        self._q = QtCore.QSettings("pipeline_tools", tool_name)

    # ── Key / value ─────────────────────────────────────────────────────────

    def get(self, key: str, default: Any = None) -> Any:
        """Return the stored value for key, or default if not set."""
        return self._q.value(key, default)

    def set(self, key: str, value: Any) -> None:
        """Persist key → value immediately."""
        self._q.setValue(key, value)

    def remove(self, key: str) -> None:
        self._q.remove(key)

    # ── Window geometry helpers ──────────────────────────────────────────────

    def save_geometry(self, window: "QtWidgets.QWidget") -> None:
        """Save window size and position. Call in closeEvent."""
        self._q.setValue("_geometry", window.saveGeometry())

    def restore_geometry(self, window: "QtWidgets.QWidget") -> None:
        """Restore previously saved window size/position. Call after show()."""
        geometry = self._q.value("_geometry")
        if geometry:
            window.restoreGeometry(geometry)
