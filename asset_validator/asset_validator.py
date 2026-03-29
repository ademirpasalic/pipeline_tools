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

try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    from PyQt5 import QtWidgets, QtCore, QtGui

# ── Default validation rules ──
DEFAULT_RULES = {
    "naming": {
        "pattern": r"^[a-z][a-z0-9]*(_[a-z0-9]+)*\.[a-z0-9]+$",
        "description": "lowercase_snake_case with extension",
        "max_length": 80,
    },
    "required_extensions": [".ma", ".mb", ".fbx", ".abc", ".usd", ".usda", ".usdz", ".png", ".exr", ".jpg"],
    "forbidden_chars": ["#", " ", "(", ")", "&", "!", "@"],
    "required_folders": ["assets", "textures", "scenes", "cache", "output"],
    "metadata_checks": {
        "check_file_size": True,
        "max_file_size_mb": 500,
        "check_modified_date": True,
        "max_age_days": 365,
    },
}


class ValidationResult:
    """Holds a single validation result."""
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"

    def __init__(self, status, rule, message, filepath=""):
        self.status = status
        self.rule = rule
        self.message = message
        self.filepath = filepath
        self.timestamp = datetime.now().isoformat()


class AssetValidator:
    """Core validation engine."""

    def __init__(self, rules=None):
        self.rules = rules or DEFAULT_RULES
        self.results = []

    def validate_path(self, root_path):
        """Run all checks on a directory."""
        self.results = []
        root = Path(root_path)

        if not root.exists():
            self.results.append(ValidationResult(
                ValidationResult.FAIL, "path", f"Path does not exist: {root_path}"
            ))
            return self.results

        self._check_folder_structure(root)
        self._check_files(root)
        return self.results

    def _check_folder_structure(self, root):
        existing = {d.name for d in root.iterdir() if d.is_dir()}
        required = set(self.rules.get("required_folders", []))
        missing = required - existing
        for folder in sorted(missing):
            self.results.append(ValidationResult(
                ValidationResult.WARN, "structure",
                f"Missing recommended folder: {folder}/", str(root)
            ))
        for folder in sorted(required & existing):
            self.results.append(ValidationResult(
                ValidationResult.PASS, "structure",
                f"Found required folder: {folder}/", str(root)
            ))

    def _check_files(self, root):
        pattern = self.rules["naming"]["pattern"]
        max_len = self.rules["naming"]["max_length"]
        forbidden = self.rules["forbidden_chars"]
        max_size = self.rules["metadata_checks"]["max_file_size_mb"] * 1024 * 1024
        max_age = self.rules["metadata_checks"]["max_age_days"]

        for filepath in root.rglob("*"):
            if filepath.is_dir():
                continue
            name = filepath.name
            rel = str(filepath.relative_to(root))

            # Naming convention
            if not re.match(pattern, name):
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
                self.results.append(ValidationResult(
                    ValidationResult.WARN, "naming",
                    f"Name exceeds {max_len} chars ({len(name)}): {name}", rel
                ))

            # Forbidden characters
            for char in forbidden:
                if char in name:
                    self.results.append(ValidationResult(
                        ValidationResult.FAIL, "naming",
                        f"Forbidden character '{char}' in: {name}", rel
                    ))

            # File size
            if self.rules["metadata_checks"]["check_file_size"]:
                size = filepath.stat().st_size
                if size > max_size:
                    size_mb = size / (1024 * 1024)
                    self.results.append(ValidationResult(
                        ValidationResult.WARN, "metadata",
                        f"Large file ({size_mb:.1f}MB): {name}", rel
                    ))

            # Modified date
            if self.rules["metadata_checks"]["check_modified_date"]:
                mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
                age = (datetime.now() - mtime).days
                if age > max_age:
                    self.results.append(ValidationResult(
                        ValidationResult.WARN, "metadata",
                        f"Stale file ({age} days old): {name}", rel
                    ))

    def export_report(self, filepath):
        """Export results as JSON."""
        data = {
            "timestamp": datetime.now().isoformat(),
            "total": len(self.results),
            "passed": sum(1 for r in self.results if r.status == ValidationResult.PASS),
            "warnings": sum(1 for r in self.results if r.status == ValidationResult.WARN),
            "failures": sum(1 for r in self.results if r.status == ValidationResult.FAIL),
            "results": [
                {"status": r.status, "rule": r.rule, "message": r.message, "path": r.filepath}
                for r in self.results
            ],
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        return filepath


class ValidatorWindow(QtWidgets.QMainWindow):
    """Main GUI window."""

    STATUS_COLORS = {
        "pass": "#00e5a0",
        "warn": "#ffc040",
        "fail": "#ff4060",
    }

    def __init__(self):
        super().__init__()
        self.validator = AssetValidator()
        self.setWindowTitle("Asset Validator")
        self.setMinimumSize(900, 600)
        self._build_ui()
        self._apply_style()

    def _build_ui(self):
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
        browse_btn = QtWidgets.QPushButton("Browse")
        browse_btn.clicked.connect(self._browse)
        validate_btn = QtWidgets.QPushButton("▶ Validate")
        validate_btn.setObjectName("primary")
        validate_btn.clicked.connect(self._validate)
        path_row.addWidget(self.path_input, 1)
        path_row.addWidget(browse_btn)
        path_row.addWidget(validate_btn)
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
        export_btn = QtWidgets.QPushButton("Export Report (JSON)")
        export_btn.clicked.connect(self._export)
        export_row.addWidget(export_btn)
        layout.addLayout(export_row)

    def _browse(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Directory")
        if path:
            self.path_input.setText(path)

    def _validate(self):
        path = self.path_input.text().strip()
        if not path:
            return
        self.table.clear()
        results = self.validator.validate_path(path)

        passes = sum(1 for r in results if r.status == "pass")
        warns = sum(1 for r in results if r.status == "warn")
        fails = sum(1 for r in results if r.status == "fail")
        self.stats_label.setText(
            f"✓ {passes} passed  ·  ⚠ {warns} warnings  ·  ✗ {fails} failures  ·  {len(results)} total checks"
        )

        for r in results:
            item = QtWidgets.QTreeWidgetItem([
                r.status.upper(), r.rule, r.message, r.filepath
            ])
            color = QtGui.QColor(self.STATUS_COLORS.get(r.status, "#ffffff"))
            item.setForeground(0, QtGui.QBrush(color))
            self.table.addTopLevelItem(item)

    def _export(self):
        if not self.validator.results:
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export Report", "validation_report.json", "JSON (*.json)"
        )
        if path:
            self.validator.export_report(path)

    def _apply_style(self):
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
            QTreeWidget { background: #0f0f18; border: 1px solid #1e1e30; border-radius: 4px; alternate-background-color: #12121e; }
            QTreeWidget::item { padding: 4px; }
            QHeaderView::section { background: #12121e; border: 1px solid #1e1e30; padding: 6px; color: #00e5a0; font-weight: bold; }
        """)


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = ValidatorWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
