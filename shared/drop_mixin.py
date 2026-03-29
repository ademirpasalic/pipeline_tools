"""
Drag-and-drop file/folder mixin for pipeline tool windows.

Usage:
    from shared.drop_mixin import DropTargetMixin

    class MyWindow(DropTargetMixin, QtWidgets.QMainWindow):
        def __init__(self):
            super().__init__()
            self.enable_drop()          # activates drop support

        def on_files_dropped(self, paths):
            for p in paths:
                self._add_file(p)       # your existing add logic
"""
from pathlib import Path

try:
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:
    from PyQt5 import QtCore, QtGui, QtWidgets


class DropTargetMixin:
    """Mixin that adds file/folder drag-and-drop to any QWidget subclass.

    The host class must:
    - Call ``self.enable_drop()`` during __init__ (after super().__init__()).
    - Implement ``on_files_dropped(paths: list[Path])``.

    Folder drops are expanded recursively to individual files.
    Duplicate paths are deduplicated before on_files_dropped is called.
    """

    def enable_drop(self, extensions: list[str] | None = None) -> None:
        """Activate drag-and-drop. Optionally filter by file extensions.

        Args:
            extensions: Allowed extensions including dot, e.g. [".png", ".exr"].
                        Pass None to accept all file types.
        """
        self._drop_extensions = {e.lower() for e in extensions} if extensions else None
        self.setAcceptDrops(True)

    # ── Qt event overrides ───────────────────────────────────────────────────

    def dragEnterEvent(self, event: "QtGui.QDragEnterEvent") -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: "QtGui.QDragMoveEvent") -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: "QtGui.QDropEvent") -> None:
        paths: list[Path] = []
        seen: set[Path] = set()

        for url in event.mimeData().urls():
            local = Path(url.toLocalFile())
            if local.is_dir():
                for child in local.rglob("*"):
                    if child.is_file():
                        self._maybe_add(child, paths, seen)
            elif local.is_file():
                self._maybe_add(local, paths, seen)

        event.acceptProposedAction()
        if paths:
            self.on_files_dropped(paths)

    # ── Subclass interface ───────────────────────────────────────────────────

    def on_files_dropped(self, paths: list[Path]) -> None:
        """Override in the host window to handle dropped files.

        Args:
            paths: Deduplicated list of Path objects (files only, never dirs).
        """

    # ── Internal ─────────────────────────────────────────────────────────────

    def _maybe_add(self, path: Path, paths: list[Path], seen: set[Path]) -> None:
        if path in seen:
            return
        if self._drop_extensions and path.suffix.lower() not in self._drop_extensions:
            return
        seen.add(path)
        paths.append(path)
