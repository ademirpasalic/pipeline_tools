"""
File Collector / Delivery Gatherer
Collect and package files from various locations for client/vendor delivery.
Validates, copies, and generates manifests.

Author: Ademir Pasalic
Requirements: pip install PySide6
"""

import sys
import json
import shutil
import hashlib
from pathlib import Path
from datetime import datetime

try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    from PyQt5 import QtWidgets, QtCore, QtGui


def _format_size(size):
    """Return a human-readable file size string."""
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


class FileCollector:
    """Core file gathering engine."""

    def __init__(self):
        self.sources = []  # List of (filepath, category) tuples

    def add_file(self, filepath, category="general"):
        self.sources.append((str(filepath), category))

    def add_directory(self, directory, category="general", extensions=None):
        for f in Path(directory).rglob("*"):
            if f.is_file():
                if extensions and f.suffix.lower() not in extensions:
                    continue
                self.sources.append((str(f), category))

    def clear(self):
        self.sources = []

    def collect(self, output_dir, flatten=False, create_manifest=True):
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        collected = []
        errors = []

        for filepath, category in self.sources:
            src = Path(filepath)
            if not src.exists():
                errors.append(f"Not found: {filepath}")
                continue

            dest = output / src.name if flatten else output / category / src.name
            dest.parent.mkdir(parents=True, exist_ok=True)

            # Handle name collisions
            if dest.exists():
                stem, ext, counter = dest.stem, dest.suffix, 1
                while dest.exists():
                    dest = dest.parent / f"{stem}_{counter}{ext}"
                    counter += 1

            try:
                shutil.copy2(src, dest)
            except OSError as e:
                errors.append(f"Copy failed ({src.name}): {e}")
                continue

            entry = {
                "source": str(src),
                "destination": str(dest.relative_to(output)),
                "category": category,
                "size": dest.stat().st_size,
                "md5": self._md5(dest) if create_manifest else "",
            }
            collected.append(entry)

        manifest_path = output / "delivery_manifest.json"
        if create_manifest:
            manifest = {
                "created": datetime.now().isoformat(),
                "total_files": len(collected),
                "total_size": sum(f["size"] for f in collected),
                "error_count": len(errors),
                "files": collected,
                "errors": errors,
            }
            try:
                with open(manifest_path, "w") as f:
                    json.dump(manifest, f, indent=2)
            except OSError as e:
                errors.append(f"Manifest write failed: {e}")

        return str(manifest_path), errors

    @staticmethod
    def _md5(filepath):
        h = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()


class CollectorWindow(QtWidgets.QMainWindow):
    """Main GUI."""

    def __init__(self):
        super().__init__()
        self.collector = FileCollector()
        self.setWindowTitle("File Collector")
        self.setMinimumSize(850, 550)
        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        header = QtWidgets.QLabel("File Collector")
        header.setObjectName("header")
        layout.addWidget(header)
        layout.addWidget(QtWidgets.QLabel("Gather files from anywhere, package them for delivery."))

        # Add controls
        add_row = QtWidgets.QHBoxLayout()
        self.category_input = QtWidgets.QLineEdit("general")
        self.category_input.setPlaceholderText("Category (= output subfolder)")
        self.category_input.setMaximumWidth(200)
        add_files_btn = QtWidgets.QPushButton("+ Add Files")
        add_files_btn.clicked.connect(self._add_files)
        add_dir_btn = QtWidgets.QPushButton("+ Add Directory")
        add_dir_btn.clicked.connect(self._add_directory)
        clear_btn = QtWidgets.QPushButton("Clear All")
        clear_btn.clicked.connect(self._clear)
        add_row.addWidget(QtWidgets.QLabel("Category:"))
        add_row.addWidget(self.category_input)
        add_row.addWidget(add_files_btn)
        add_row.addWidget(add_dir_btn)
        add_row.addStretch()
        add_row.addWidget(clear_btn)
        layout.addLayout(add_row)

        # File table
        self.table = QtWidgets.QTreeWidget()
        self.table.setHeaderLabels(["File", "Category", "Size", "Source Path"])
        self.table.setColumnWidth(0, 200)
        self.table.setColumnWidth(1, 100)
        self.table.setColumnWidth(2, 80)
        self.table.setRootIsDecorated(False)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table, 1)

        # Output options
        out_row = QtWidgets.QHBoxLayout()
        out_row.addWidget(QtWidgets.QLabel("Delivery Folder:"))
        self.output_input = QtWidgets.QLineEdit()
        self.output_input.setPlaceholderText("Select output directory...")
        out_row.addWidget(self.output_input, 1)
        browse_btn = QtWidgets.QPushButton("Browse")
        browse_btn.clicked.connect(self._browse_output)
        out_row.addWidget(browse_btn)
        layout.addLayout(out_row)

        opt_row = QtWidgets.QHBoxLayout()
        self.flatten_cb = QtWidgets.QCheckBox("Flatten (no subfolders)")
        self.manifest_cb = QtWidgets.QCheckBox("Generate manifest")
        self.manifest_cb.setChecked(True)
        opt_row.addWidget(self.flatten_cb)
        opt_row.addWidget(self.manifest_cb)
        opt_row.addStretch()
        layout.addLayout(opt_row)

        # Collect button
        bottom = QtWidgets.QHBoxLayout()
        self.status_label = QtWidgets.QLabel("")
        self.status_label.setObjectName("stats")
        bottom.addWidget(self.status_label, 1)
        collect_btn = QtWidgets.QPushButton("▶ Collect & Package")
        collect_btn.setObjectName("primary")
        collect_btn.clicked.connect(self._collect)
        bottom.addWidget(collect_btn)
        layout.addLayout(bottom)

    def _add_files(self):
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(self, "Select Files")
        category = self.category_input.text().strip() or "general"
        for f in files:
            self.collector.add_file(f, category)
            item = QtWidgets.QTreeWidgetItem([
                Path(f).name, category, _format_size(Path(f).stat().st_size), f
            ])
            self.table.addTopLevelItem(item)
        self._update_status()

    def _add_directory(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Directory")
        if directory:
            category = self.category_input.text().strip() or "general"
            for f in Path(directory).rglob("*"):
                if f.is_file():
                    self.collector.add_file(str(f), category)
                    item = QtWidgets.QTreeWidgetItem([
                        f.name, category, _format_size(f.stat().st_size), str(f)
                    ])
                    self.table.addTopLevelItem(item)
            self._update_status()

    def _clear(self):
        self.collector.clear()
        self.table.clear()
        self.status_label.setText("")

    def _browse_output(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Delivery Folder")
        if path:
            self.output_input.setText(path)

    def _collect(self):
        output = self.output_input.text().strip()
        if not output:
            self.status_label.setText("⚠ Select a delivery folder first")
            return
        if not self.collector.sources:
            self.status_label.setText("⚠ No files queued — add files or a directory first")
            return
        manifest_path, errors = self.collector.collect(
            output,
            flatten=self.flatten_cb.isChecked(),
            create_manifest=self.manifest_cb.isChecked(),
        )
        count = len(self.collector.sources) - len(errors)
        msg = f"✓ Collected {count} files → {output}"
        if self.manifest_cb.isChecked():
            msg += "  ·  manifest written"
        if errors:
            msg += f"  ·  ⚠ {len(errors)} errors"
            QtWidgets.QMessageBox.warning(self, "Collection errors", "\n".join(errors))
        self.status_label.setText(msg)

    def _update_status(self):
        self.status_label.setText(f"{len(self.collector.sources)} files queued")

    def _apply_style(self):
        self.setStyleSheet("""
            QMainWindow { background: #0a0a0f; }
            QWidget { color: #e0e0e8; font-family: 'JetBrains Mono', 'Consolas', monospace; font-size: 12px; }
            #header { font-size: 20px; font-weight: bold; color: #00e5a0; padding: 8px 0; }
            #stats { color: #7a7a8e; font-size: 11px; }
            QLabel { color: #7a7a8e; }
            QLineEdit { background: #12121e; border: 1px solid #1e1e30; border-radius: 4px; padding: 8px; color: #e0e0e8; }
            QCheckBox { color: #7a7a8e; }
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
    window = CollectorWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
