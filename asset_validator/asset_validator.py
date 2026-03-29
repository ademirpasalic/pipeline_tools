"""
Asset Validator
A production pipeline tool for validating naming conventions, file structure,
and metadata against configurable rulesets.

Author: Ademir Pasalic
Requirements: pip install PySide6
"""

import os
import re
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from shared.logging_config import get_logger

logger = get_logger(__name__)

try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    from PyQt5 import QtWidgets, QtCore, QtGui

from shared.dialogs import show_error, show_info
from shared.settings import AppSettings

# ── Constants ──────────────────────────────────────────────────────────────────

NAMING_PATTERN = r"^[a-z][a-z0-9]*(_[a-z0-9]+)*\.[a-z0-9]+$"
NAMING_MAX_LENGTH = 80
FORBIDDEN_CHARS = ["#", " ", "(", ")", "&", "!", "@"]
REQUIRED_FOLDERS = ["assets", "textures", "scenes", "cache", "output"]
REQUIRED_EXTENSIONS = [".ma", ".mb", ".fbx", ".abc", ".usd", ".usda", ".usdz", ".png", ".exr", ".jpg"]
MAX_FILE_SIZE_MB = 500
MAX_AGE_DAYS = 365

_MB = 1024 * 1024

# Status color hex codes for the results table
COLOR_PASS = "#00e5a0"
COLOR_WARN = "#ffc040"
COLOR_FAIL = "#ff4060"
COLOR_DEFAULT = "#ffffff"

# Pre-compiled naming regex used in the validation loop
_NAMING_RE = re.compile(NAMING_PATTERN)

# ── Default validation rules ────────────────────────────────────────────────────

DEFAULT_RULES = {
    "naming": {
        "pattern": NAMING_PATTERN,
        "description": "lowercase_snake_case with extension",
        "max_length": NAMING_MAX_LENGTH,
    },
    "required_extensions": REQUIRED_EXTENSIONS,
    "forbidden_chars": FORBIDDEN_CHARS,
    "required_folders": REQUIRED_FOLDERS,
    "metadata_checks": {
        "check_file_size": True,
        "max_file_size_mb": MAX_FILE_SIZE_MB,
        "check_modified_date": True,
        "max_age_days": MAX_AGE_DAYS,
    },
}


class ValidationResult:
    """Holds the outcome of a single validation check.

    Attributes:
        status:    One of PASS, WARN, or FAIL.
        rule:      Name of the rule that produced this result (e.g. "naming").
        message:   Human-readable description of the check outcome.
        filepath:  Relative or absolute path of the file/directory checked.
        timestamp: ISO-8601 timestamp of when the check was performed.
    """

    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"

    def __init__(
        self,
        status: str,
        rule: str,
        message: str,
        filepath: str = "",
    ) -> None:
        """Initialise a ValidationResult.

        Args:
            status:   Check outcome — one of ValidationResult.PASS/WARN/FAIL.
            rule:     Rule category (e.g. "naming", "structure", "metadata").
            message:  Description of the check result.
            filepath: Path of the asset being validated.
        """
        self.status = status
        self.rule = rule
        self.message = message
        self.filepath = filepath
        self.timestamp = datetime.now().isoformat()


class AssetValidator:
    """Core validation engine — no Qt dependency.

    Validates a directory tree against configurable naming conventions,
    folder-structure requirements, and file-metadata rules.

    Attributes:
        rules:   Active ruleset dict (defaults to DEFAULT_RULES).
        results: List of ValidationResult objects from the last run.
    """

    def __init__(self, rules: Optional[dict] = None) -> None:
        """Initialise the validator with an optional custom ruleset.

        Args:
            rules: Rule configuration dict.  When omitted, DEFAULT_RULES is used.
        """
        self.rules = rules or DEFAULT_RULES
        self.results: List[ValidationResult] = []
        # Pre-compile the naming pattern; fall back to module-level default.
        pattern_str = self.rules.get("naming", {}).get("pattern", NAMING_PATTERN)
        self._naming_re = re.compile(pattern_str)

    # Public API ---------------------------------------------------------------

    def validate(self, root_path: str) -> List[ValidationResult]:
        """Run all validation checks on a directory tree.

        Args:
            root_path: Absolute or relative path to the root directory.

        Returns:
            List of ValidationResult objects covering every check performed.
        """
        logger.debug("Validation started for: %s", root_path)
        self.results = []
        root = Path(root_path)

        if not root.exists():
            logger.debug("Path does not exist: %s", root_path)
            self.results.append(ValidationResult(
                ValidationResult.FAIL, "path", f"Path does not exist: {root_path}"
            ))
            return self.results

        self._check_folder_structure(root)
        self._check_files(root)

        passes = sum(1 for r in self.results if r.status == ValidationResult.PASS)
        warns  = sum(1 for r in self.results if r.status == ValidationResult.WARN)
        fails  = sum(1 for r in self.results if r.status == ValidationResult.FAIL)
        logger.debug(
            "Validation complete — %d passed, %d warnings, %d failures",
            passes, warns, fails,
        )
        return self.results

    # Backwards-compatible alias
    def validate_path(self, root_path: str) -> List[ValidationResult]:
        """Alias for validate(); kept for backwards compatibility.

        Args:
            root_path: Path to the directory to validate.

        Returns:
            List of ValidationResult objects.
        """
        return self.validate(root_path)

    def export_report(self, filepath: str) -> str:
        """Export the most recent validation results as a JSON report.

        Args:
            filepath: Destination path for the JSON file.

        Returns:
            The filepath that was written.
        """
        data = {
            "timestamp": datetime.now().isoformat(),
            "total": len(self.results),
            "passed":   sum(1 for r in self.results if r.status == ValidationResult.PASS),
            "warnings": sum(1 for r in self.results if r.status == ValidationResult.WARN),
            "failures": sum(1 for r in self.results if r.status == ValidationResult.FAIL),
            "results": [
                {"status": r.status, "rule": r.rule, "message": r.message, "path": r.filepath}
                for r in self.results
            ],
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        logger.debug("Report exported to: %s", filepath)
        return filepath

    # Private helpers ----------------------------------------------------------

    def _check_folder_structure(self, root: Path) -> None:
        """Validate that required folders are present under root.

        Args:
            root: Root Path object to inspect.
        """
        existing = {d.name for d in root.iterdir() if d.is_dir()}
        required = set(self.rules.get("required_folders", []))
        missing = required - existing
        for folder in sorted(missing):
            logger.debug("Missing required folder: %s", folder)
            self.results.append(ValidationResult(
                ValidationResult.WARN, "structure",
                f"Missing recommended folder: {folder}/", str(root)
            ))
        for folder in sorted(required & existing):
            self.results.append(ValidationResult(
                ValidationResult.PASS, "structure",
                f"Found required folder: {folder}/", str(root)
            ))

    def _check_files(self, root: Path) -> None:
        """Run naming, metadata, and forbidden-character checks on every file.

        Args:
            root: Root Path object whose tree will be walked.
        """
        max_len  = self.rules["naming"]["max_length"]
        forbidden = self.rules["forbidden_chars"]
        max_size = self.rules["metadata_checks"]["max_file_size_mb"] * _MB
        max_age  = self.rules["metadata_checks"]["max_age_days"]

        for filepath in root.rglob("*"):
            if filepath.is_dir():
                continue
            name = filepath.name
            rel  = str(filepath.relative_to(root))

            # Naming convention (uses pre-compiled regex)
            if not self._naming_re.match(name):
                logger.debug("Naming rule FAIL: %s", rel)
                self.results.append(ValidationResult(
                    ValidationResult.FAIL, "naming",
                    f"Name doesn't match pattern: {name}", rel
                ))
            else:
                self.results.append(ValidationResult(
                    ValidationResult.PASS, "naming",
                    f"Valid name: {name}", rel
                ))

            # Length check
            if len(name) > max_len:
                logger.debug("Name too long (%d chars): %s", len(name), rel)
                self.results.append(ValidationResult(
                    ValidationResult.WARN, "naming",
                    f"Name exceeds {max_len} chars ({len(name)}): {name}", rel
                ))

            # Forbidden characters
            for char in forbidden:
                if char in name:
                    logger.debug("Forbidden char %r in: %s", char, rel)
                    self.results.append(ValidationResult(
                        ValidationResult.FAIL, "naming",
                        f"Forbidden character '{char}' in: {name}", rel
                    ))

            # File size
            if self.rules["metadata_checks"]["check_file_size"]:
                size = filepath.stat().st_size
                if size > max_size:
                    size_mb = size / _MB
                    logger.debug("Large file (%.1f MB): %s", size_mb, rel)
                    self.results.append(ValidationResult(
                        ValidationResult.WARN, "metadata",
                        f"Large file ({size_mb:.1f}MB): {name}", rel
                    ))

            # Modified date
            if self.rules["metadata_checks"]["check_modified_date"]:
                mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
                age = (datetime.now() - mtime).days
                if age > max_age:
                    logger.debug("Stale file (%d days): %s", age, rel)
                    self.results.append(ValidationResult(
                        ValidationResult.WARN, "metadata",
                        f"Stale file ({age} days old): {name}", rel
                    ))


class ValidatorWindow(QtWidgets.QMainWindow):
    """Main GUI window for the Asset Validator tool.

    Wraps AssetValidator with a PySide6/PyQt5 interface for browsing a
    directory, running validation, viewing results in a table, and exporting
    a JSON report.
    """

    STATUS_COLORS = {
        ValidationResult.PASS: COLOR_PASS,
        ValidationResult.WARN: COLOR_WARN,
        ValidationResult.FAIL: COLOR_FAIL,
    }

    def __init__(self) -> None:
        """Initialise the window, build UI, restore geometry."""
        super().__init__()
        self.validator = AssetValidator()
        self.settings = AppSettings("asset_validator")
        self.setWindowTitle("Asset Validator")
        self.setMinimumSize(900, 600)
        self._build_ui()
        self._apply_style()
        self._update_ui()

    def show(self) -> None:
        """Show the window and restore previously saved geometry."""
        super().show()
        self.settings.restore_geometry(self)

    def closeEvent(self, event: QtCore.QEvent) -> None:
        """Save window geometry on close.

        Args:
            event: The close event passed by Qt.
        """
        self.settings.save_geometry(self)
        super().closeEvent(event)

    # UI construction ----------------------------------------------------------

    def _build_ui(self) -> None:
        """Construct and lay out all child widgets."""
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Header
        header = QtWidgets.QLabel("Asset Validator")
        header.setObjectName("header")
        layout.addWidget(header)

        # Path selector
        path_row = QtWidgets.QHBoxLayout()
        self.path_input = QtWidgets.QLineEdit()
        self.path_input.setPlaceholderText("Select a directory to validate...")
        self.path_input.textChanged.connect(self._update_ui)
        browse_btn = QtWidgets.QPushButton("Browse")
        browse_btn.clicked.connect(self._browse)
        self.validate_btn = QtWidgets.QPushButton("▶ Validate")
        self.validate_btn.setObjectName("primary")
        self.validate_btn.clicked.connect(self._validate)
        path_row.addWidget(self.path_input, 1)
        path_row.addWidget(browse_btn)
        path_row.addWidget(self.validate_btn)
        layout.addLayout(path_row)

        # Stats bar
        self.stats_label = QtWidgets.QLabel("")
        self.stats_label.setObjectName("stats")
        layout.addWidget(self.stats_label)

        # Results table
        self.table = QtWidgets.QTreeWidget()
        self.table.setHeaderLabels(["Status", "Rule", "Message", "Path"])
        self.table.setColumnWidth(0, 60)
        self.table.setColumnWidth(1, 80)
        self.table.setColumnWidth(2, 400)
        self.table.setRootIsDecorated(False)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table, 1)

        # Export button
        export_row = QtWidgets.QHBoxLayout()
        export_row.addStretch()
        self.export_btn = QtWidgets.QPushButton("Export Report (JSON)")
        self.export_btn.clicked.connect(self._export)
        export_row.addWidget(self.export_btn)
        layout.addLayout(export_row)

    # Slots --------------------------------------------------------------------

    def _update_ui(self) -> None:
        """Enable or disable the Validate button based on whether a path is entered."""
        has_path = bool(self.path_input.text().strip())
        self.validate_btn.setEnabled(has_path)

    def _browse(self) -> None:
        """Open a directory-picker dialog and populate the path input."""
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Directory")
        if path:
            self.path_input.setText(path)

    def _validate(self) -> None:
        """Run validation on the selected directory and populate the results table."""
        path = self.path_input.text().strip()
        if not path:
            return
        logger.debug("UI triggered validation for: %s", path)
        self.table.clear()
        results = self.validator.validate(path)

        passes = sum(1 for r in results if r.status == ValidationResult.PASS)
        warns  = sum(1 for r in results if r.status == ValidationResult.WARN)
        fails  = sum(1 for r in results if r.status == ValidationResult.FAIL)
        self.stats_label.setText(
            f"✓ {passes} passed  ·  ⚠ {warns} warnings  ·  ✗ {fails} failures  ·  {len(results)} total checks"
        )

        for r in results:
            item = QtWidgets.QTreeWidgetItem([
                r.status.upper(), r.rule, r.message, r.filepath
            ])
            color = QtGui.QColor(self.STATUS_COLORS.get(r.status, COLOR_DEFAULT))
            item.setForeground(0, QtGui.QBrush(color))
            self.table.addTopLevelItem(item)

    def _export(self) -> None:
        """Prompt for a save location and export the current results as JSON."""
        if not self.validator.results:
            show_info(self, "Nothing to Export", "Run a validation first.")
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export Report", "validation_report.json", "JSON (*.json)"
        )
        if path:
            try:
                self.validator.export_report(path)
                logger.debug("Report exported via UI to: %s", path)
            except OSError as exc:
                logger.debug("Export failed: %s", exc)
                show_error(self, "Export Failed", str(exc))

    def _apply_style(self) -> None:
        """Apply the dark stylesheet to the main window."""
        self.setStyleSheet("""
            QMainWindow { background: #0a0a0f; }
            QWidget { color: #e0e0e8; font-family: 'JetBrains Mono', 'Consolas', monospace; font-size: 12px; }
            #header { font-size: 20px; font-weight: bold; color: #00e5a0; padding: 8px 0; }
            #stats { color: #7a7a8e; font-size: 11px; padding: 4px 0; }
            QLineEdit { background: #12121e; border: 1px solid #1e1e30; border-radius: 4px; padding: 8px; color: #e0e0e8; }
            QLineEdit:focus { border-color: #00e5a0; }
            QPushButton { background: #12121e; border: 1px solid #1e1e30; border-radius: 4px; padding: 8px 16px; color: #7a7a8e; }
            QPushButton:hover { border-color: #00e5a0; color: #00e5a0; }
            QPushButton#primary { background: #00e5a0; color: #0a0a0f; border-color: #00e5a0; font-weight: bold; }
            QPushButton#primary:hover { background: transparent; color: #00e5a0; }
            QPushButton:disabled { color: #3a3a4e; border-color: #1e1e30; }
            QTreeWidget { background: #0f0f18; border: 1px solid #1e1e30; border-radius: 4px; alternate-background-color: #12121e; }
            QTreeWidget::item { padding: 4px; }
            QHeaderView::section { background: #12121e; border: 1px solid #1e1e30; padding: 6px; color: #00e5a0; font-weight: bold; }
        """)


def main() -> None:
    """Entry point — create QApplication and show the ValidatorWindow."""
    app = QtWidgets.QApplication(sys.argv)
    window = ValidatorWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
