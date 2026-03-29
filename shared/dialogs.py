"""
Consistent error/warning/info dialogs for pipeline tools.

Usage:
    from shared.dialogs import show_error, show_warning, show_info

    show_error(self, "Publish Failed", "Could not copy file.", detail=traceback_str)
    show_warning(self, "Overwrite?", "File already exists.")
    show_info(self, "Done", "Collected 42 files.")
"""
try:
    from PySide6 import QtWidgets
except ImportError:
    from PyQt5 import QtWidgets


def show_error(
    parent: "QtWidgets.QWidget | None",
    title: str,
    message: str,
    detail: str = "",
) -> None:
    """Show a modal error dialog with an optional collapsible detail section.

    Args:
        parent:  Parent widget (or None for top-level).
        title:   Dialog window title.
        message: Primary error message shown to the user.
        detail:  Optional technical detail (stack trace, stderr, etc.) shown
                 in the "Show Details" section.
    """
    dlg = QtWidgets.QMessageBox(parent)
    dlg.setWindowTitle(title)
    dlg.setText(message)
    dlg.setIcon(QtWidgets.QMessageBox.Critical)
    if detail:
        dlg.setDetailedText(detail)
    dlg.exec()


def show_warning(
    parent: "QtWidgets.QWidget | None",
    title: str,
    message: str,
    detail: str = "",
) -> None:
    """Show a modal warning dialog."""
    dlg = QtWidgets.QMessageBox(parent)
    dlg.setWindowTitle(title)
    dlg.setText(message)
    dlg.setIcon(QtWidgets.QMessageBox.Warning)
    if detail:
        dlg.setDetailedText(detail)
    dlg.exec()


def show_info(
    parent: "QtWidgets.QWidget | None",
    title: str,
    message: str,
) -> None:
    """Show a modal informational dialog."""
    dlg = QtWidgets.QMessageBox(parent)
    dlg.setWindowTitle(title)
    dlg.setText(message)
    dlg.setIcon(QtWidgets.QMessageBox.Information)
    dlg.exec()


def confirm(
    parent: "QtWidgets.QWidget | None",
    title: str,
    message: str,
) -> bool:
    """Show a Yes/No confirmation dialog. Returns True if user clicked Yes."""
    result = QtWidgets.QMessageBox.question(
        parent,
        title,
        message,
        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        QtWidgets.QMessageBox.No,
    )
    return result == QtWidgets.QMessageBox.Yes
