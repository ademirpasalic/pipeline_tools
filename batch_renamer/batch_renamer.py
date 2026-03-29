"""
Batch Renamer / File Organizer
Rename and organize production files with regex patterns, presets,
find-and-replace, numbering, and preview before applying.

Author: Ademir Pasalic
Requirements: pip install PySide6
"""

import os
import re
import sys
from pathlib import Path

try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    from PyQt5 import QtWidgets, QtCore, QtGui


PRESETS = {
    "lowercase_snake": {
        "description": "Convert to lowercase_snake_case",
        "find": r"[\s\-\.]+",
        "replace": "_",
        "lowercase": True,
    },
    "remove_version": {
        "description": "Strip version suffix (_v001, _v02, etc)",
        "find": r"_v\d+",
        "replace": "",
        "lowercase": False,
    },
    "add_prefix": {
        "description": "Add project prefix",
        "find": r"^",
        "replace": "proj_",
        "lowercase": False,
    },
    "clean_spaces": {
        "description": "Replace spaces and special chars with underscores",
        "find": r"[^\w\.]",
        "replace": "_",
        "lowercase": False,
    },
}


class RenameEngine:
    """Core rename logic with preview."""

    def __init__(self):
        self.files = []

    def load_files(self, paths):
        self.files = [Path(p) for p in paths if Path(p).is_file()]

    def load_directory(self, directory, recursive=False):
        root = Path(directory)
        if recursive:
            self.files = [f for f in root.rglob("*") if f.is_file()]
        else:
            self.files = [f for f in root.iterdir() if f.is_file()]

    def preview(self, find, replace, lowercase=False, add_number=False, start_num=1, padding=3):
        """Return list of (old_name, new_name, full_old, full_new) tuples."""
        results = []
        for i, filepath in enumerate(self.files):
            old_name = filepath.stem
            ext = filepath.suffix

            new_name = re.sub(find, replace, old_name) if find else old_name

            if lowercase:
                new_name = new_name.lower()

            if add_number:
                num = str(start_num + i).zfill(padding)
                new_name = f"{new_name}_{num}"

            # Clean double underscores
            new_name = re.sub(r"_+", "_", new_name).strip("_")

            new_full = filepath.parent / f"{new_name}{ext}"
            results.append((filepath.name, f"{new_name}{ext}", str(filepath), str(new_full)))
        return results

    def apply(self, preview_results):
        """Execute the rename."""
        renamed = []
        for old_name, new_name, old_path, new_path in preview_results:
            if old_path != new_path:
                os.rename(old_path, new_path)
                renamed.append((old_name, new_name))
        return renamed


class BatchRenamerWindow(QtWidgets.QMainWindow):
    """Main GUI."""

    def __init__(self):
        super().__init__()
        self.engine = RenameEngine()
        self.setWindowTitle("Batch Renamer")
        self.setMinimumSize(900, 600)
        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        header = QtWidgets.QLabel("Batch Renamer")
        header.setObjectName("header")
        layout.addWidget(header)

        # Directory selector
        dir_row = QtWidgets.QHBoxLayout()
        self.dir_input = QtWidgets.QLineEdit()
        self.dir_input.setPlaceholderText("Select a directory...")
        browse_btn = QtWidgets.QPushButton("Browse")
        browse_btn.clicked.connect(self._browse)
        self.recursive_cb = QtWidgets.QCheckBox("Recursive")
        load_btn = QtWidgets.QPushButton("Load Files")
        load_btn.clicked.connect(self._load)
        dir_row.addWidget(self.dir_input, 1)
        dir_row.addWidget(browse_btn)
        dir_row.addWidget(self.recursive_cb)
        dir_row.addWidget(load_btn)
        layout.addLayout(dir_row)

        # Presets
        preset_row = QtWidgets.QHBoxLayout()
        preset_row.addWidget(QtWidgets.QLabel("Preset:"))
        self.preset_combo = QtWidgets.QComboBox()
        self.preset_combo.addItem("Custom")
        for name, p in PRESETS.items():
            self.preset_combo.addItem(f"{name} — {p['description']}", userData=name)
        self.preset_combo.currentIndexChanged.connect(self._apply_preset)
        preset_row.addWidget(self.preset_combo, 1)
        layout.addLayout(preset_row)

        # Find / Replace
        find_row = QtWidgets.QHBoxLayout()
        find_row.addWidget(QtWidgets.QLabel("Find (regex):"))
        self.find_input = QtWidgets.QLineEdit()
        self.find_input.setPlaceholderText(r"e.g. [\s]+")
        self.find_input.textChanged.connect(self._preview)
        find_row.addWidget(self.find_input, 1)
        find_row.addWidget(QtWidgets.QLabel("Replace:"))
        self.replace_input = QtWidgets.QLineEdit()
        self.replace_input.setPlaceholderText("e.g. _")
        self.replace_input.textChanged.connect(self._preview)
        find_row.addWidget(self.replace_input, 1)
        layout.addLayout(find_row)

        # Options
        opt_row = QtWidgets.QHBoxLayout()
        self.lower_cb = QtWidgets.QCheckBox("Lowercase")
        self.lower_cb.stateChanged.connect(self._preview)
        self.number_cb = QtWidgets.QCheckBox("Add numbering")
        self.number_cb.stateChanged.connect(self._preview)
        opt_row.addWidget(self.lower_cb)
        opt_row.addWidget(self.number_cb)
        opt_row.addStretch()
        layout.addLayout(opt_row)

        # Preview table
        self.table = QtWidgets.QTreeWidget()
        self.table.setHeaderLabels(["Original", "→", "New Name"])
        self.table.setColumnWidth(0, 350)
        self.table.setColumnWidth(1, 30)
        self.table.setRootIsDecorated(False)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table, 1)

        # Status + apply
        bottom_row = QtWidgets.QHBoxLayout()
        self.status_label = QtWidgets.QLabel("")
        self.status_label.setObjectName("stats")
        bottom_row.addWidget(self.status_label, 1)
        apply_btn = QtWidgets.QPushButton("▶ Apply Rename")
        apply_btn.setObjectName("primary")
        apply_btn.clicked.connect(self._apply)
        bottom_row.addWidget(apply_btn)
        layout.addLayout(bottom_row)

    def _browse(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Directory")
        if path:
            self.dir_input.setText(path)

    def _load(self):
        path = self.dir_input.text().strip()
        if path:
            self.engine.load_directory(path, self.recursive_cb.isChecked())
            self.status_label.setText(f"Loaded {len(self.engine.files)} files")
            self._preview()

    def _apply_preset(self, index):
        preset_name = self.preset_combo.currentData()
        if not preset_name or preset_name not in PRESETS:
            return
        preset = PRESETS[preset_name]
        self.find_input.setText(preset["find"])
        self.replace_input.setText(preset["replace"])
        self.lower_cb.setChecked(preset["lowercase"])

    def _preview(self):
        self.table.clear()
        if not self.engine.files:
            return
        results = self.engine.preview(
            self.find_input.text(),
            self.replace_input.text(),
            self.lower_cb.isChecked(),
            self.number_cb.isChecked(),
        )
        changes = 0
        for old, new, _, _ in results:
            item = QtWidgets.QTreeWidgetItem([old, "→", new])
            if old != new:
                item.setForeground(2, QtGui.QBrush(QtGui.QColor("#00e5a0")))
                changes += 1
            else:
                item.setForeground(2, QtGui.QBrush(QtGui.QColor("#4a4a5e")))
            self.table.addTopLevelItem(item)
        self.status_label.setText(f"{changes} files will be renamed")
        self._last_preview = results

    def _apply(self):
        if not hasattr(self, "_last_preview"):
            return
        confirm = QtWidgets.QMessageBox.question(
            self, "Confirm", "Apply rename to all files?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if confirm == QtWidgets.QMessageBox.Yes:
            renamed = self.engine.apply(self._last_preview)
            self.status_label.setText(f"✓ Renamed {len(renamed)} files")
            self._load()

    def _apply_style(self):
        self.setStyleSheet("""
            QMainWindow { background: #0a0a0f; }
            QWidget { color: #e0e0e8; font-family: 'JetBrains Mono', 'Consolas', monospace; font-size: 12px; }
            #header { font-size: 20px; font-weight: bold; color: #00e5a0; padding: 8px 0; }
            #stats { color: #7a7a8e; font-size: 11px; }
            QLabel { color: #7a7a8e; }
            QLineEdit { background: #12121e; border: 1px solid #1e1e30; border-radius: 4px; padding: 8px; color: #e0e0e8; }
            QLineEdit:focus { border-color: #00e5a0; }
            QComboBox { background: #12121e; border: 1px solid #1e1e30; border-radius: 4px; padding: 6px; color: #e0e0e8; }
            QCheckBox { color: #7a7a8e; }
            QCheckBox::indicator:checked { background: #00e5a0; border: 1px solid #00e5a0; }
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
    window = BatchRenamerWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
