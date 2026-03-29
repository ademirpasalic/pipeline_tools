"""
File Ingestor
Digest and ingest files into a structured production pipeline.
Validates, renames, organizes, and registers incoming files.

Author: Ademir Pasalic
Requirements: pip install PySide6
"""

import re
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime

try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    from PyQt5 import QtWidgets, QtCore, QtGui


# Status colors for the results table
COLOR_PENDING  = "#ffc040"
COLOR_PREVIEW  = "#40a0ff"
COLOR_INGESTED = "#00e5a0"
COLOR_ERROR    = "#ff4060"

INGEST_RULES = {
    "image": {
        "extensions": [".png", ".jpg", ".jpeg", ".exr", ".tiff", ".tif", ".tga", ".bmp"],
        "target_folder": "textures",
    },
    "scene": {
        "extensions": [".ma", ".mb", ".blend", ".hip", ".hipnc", ".nk"],
        "target_folder": "scenes",
    },
    "cache": {
        "extensions": [".abc", ".usd", ".usda", ".usdc", ".usdz", ".bgeo", ".vdb"],
        "target_folder": "cache",
    },
    "video": {
        "extensions": [".mov", ".mp4", ".avi", ".mkv"],
        "target_folder": "video",
    },
    "audio": {
        "extensions": [".wav", ".mp3", ".aif", ".aiff", ".flac"],
        "target_folder": "audio",
    },
    "document": {
        "extensions": [".pdf", ".doc", ".docx", ".txt", ".csv", ".xlsx"],
        "target_folder": "docs",
    },
}

# Base fields present on every log entry regardless of status
_BASE_ENTRY = {
    "source": "",
    "original_name": "",
    "category": "",
    "target": "",
    "new_name": "",
    "size": 0,
    "timestamp": "",
    "status": "",
    "message": "",
}


class FileIngestor:
    """Core ingest engine."""

    def __init__(self, project_root=""):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.rules = INGEST_RULES
        self.log = []

    def classify(self, filepath):
        """Return the target folder name for a file based on its extension."""
        ext = Path(filepath).suffix.lower()
        for rule in self.rules.values():
            if ext in rule["extensions"]:
                return rule["target_folder"]
        return "other"

    def ingest(self, filepaths, project_root=None, rename_pattern=None, dry_run=False):
        """Ingest files into the pipeline structure."""
        root = Path(project_root) if project_root else self.project_root
        self.log = []
        results = []

        for filepath in filepaths:
            src = Path(filepath)
            ts = datetime.now().isoformat()

            if not src.exists():
                entry = {**_BASE_ENTRY,
                         "source": str(src), "original_name": src.name,
                         "timestamp": ts, "status": "error",
                         "message": "File not found"}
                self.log.append(entry)
                results.append(entry)
                continue

            target_folder = self.classify(filepath)
            target_dir = root / target_folder

            if rename_pattern:
                new_name, err = self._apply_rename(src.name, rename_pattern, len(results) + 1)
                if err:
                    entry = {**_BASE_ENTRY,
                             "source": str(src), "original_name": src.name,
                             "category": target_folder, "timestamp": ts,
                             "status": "error", "message": err}
                    self.log.append(entry)
                    results.append(entry)
                    continue
            else:
                new_name = re.sub(r"[^\w\.\-]", "_", src.name)
                new_name = re.sub(r"_+", "_", new_name)

            target_path = target_dir / new_name

            # Handle duplicates
            if target_path.exists():
                stem, ext, counter = target_path.stem, target_path.suffix, 1
                while target_path.exists():
                    target_path = target_dir / f"{stem}_{counter}{ext}"
                    counter += 1

            entry = {**_BASE_ENTRY,
                     "source": str(src),
                     "target": str(target_path),
                     "category": target_folder,
                     "original_name": src.name,
                     "new_name": target_path.name,
                     "size": src.stat().st_size,
                     "timestamp": ts}

            if not dry_run:
                target_dir.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copy2(src, target_path)
                    entry["status"] = "ingested"
                except OSError as e:
                    entry["status"] = "error"
                    entry["message"] = str(e)
            else:
                entry["status"] = "preview"

            results.append(entry)
            self.log.append(entry)

        # Write ingest log
        if not dry_run and results:
            log_dir = root / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_path = log_dir / f"ingest_{timestamp}.json"
            with open(log_path, "w") as f:
                json.dump({"ingest_log": results}, f, indent=2)

        return results

    @staticmethod
    def _apply_rename(filename, pattern, index):
        """Apply a format-string rename pattern. Returns (new_name, error_or_None)."""
        stem = Path(filename).stem
        ext = Path(filename).suffix
        try:
            return pattern.format(name=stem, ext=ext, index=index, i=f"{index:04d}"), None
        except KeyError as e:
            valid = "{name}, {ext}, {index}, {i}"
            return filename, f"Unknown variable {e} in pattern — valid: {valid}"


class IngestorWindow(QtWidgets.QMainWindow):
    """Main GUI."""

    def __init__(self):
        super().__init__()
        self.ingestor = FileIngestor()
        self.pending_files = []
        self.setWindowTitle("File Ingestor")
        self.setMinimumSize(900, 600)
        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        header = QtWidgets.QLabel("File Ingestor")
        header.setObjectName("header")
        layout.addWidget(header)
        layout.addWidget(QtWidgets.QLabel("Ingest incoming files into your pipeline structure."))

        # Project root
        root_row = QtWidgets.QHBoxLayout()
        root_row.addWidget(QtWidgets.QLabel("Project Root:"))
        self.root_input = QtWidgets.QLineEdit()
        self.root_input.setPlaceholderText("Select project root directory...")
        root_row.addWidget(self.root_input, 1)
        browse_root = QtWidgets.QPushButton("Browse")
        browse_root.clicked.connect(self._browse_root)
        root_row.addWidget(browse_root)
        layout.addLayout(root_row)

        # Add files
        add_row = QtWidgets.QHBoxLayout()
        add_files_btn = QtWidgets.QPushButton("+ Add Files")
        add_files_btn.clicked.connect(self._add_files)
        add_dir_btn = QtWidgets.QPushButton("+ Add Directory")
        add_dir_btn.clicked.connect(self._add_directory)
        clear_btn = QtWidgets.QPushButton("Clear")
        clear_btn.clicked.connect(self._clear)
        add_row.addWidget(add_files_btn)
        add_row.addWidget(add_dir_btn)
        add_row.addWidget(clear_btn)
        add_row.addStretch()
        preview_btn = QtWidgets.QPushButton("Preview Ingest")
        preview_btn.clicked.connect(self._preview)
        add_row.addWidget(preview_btn)
        layout.addLayout(add_row)

        # Rename pattern
        rename_row = QtWidgets.QHBoxLayout()
        rename_row.addWidget(QtWidgets.QLabel("Rename Pattern (optional):"))
        self.rename_input = QtWidgets.QLineEdit()
        self.rename_input.setPlaceholderText("{name}{ext}  |  Variables: {name}, {ext}, {index}, {i}")
        rename_row.addWidget(self.rename_input, 1)
        layout.addLayout(rename_row)

        # Results table
        self.table = QtWidgets.QTreeWidget()
        self.table.setHeaderLabels(["File", "Category", "Target", "Status"])
        self.table.setColumnWidth(0, 200)
        self.table.setColumnWidth(1, 80)
        self.table.setColumnWidth(2, 300)
        self.table.setRootIsDecorated(False)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table, 1)

        # Ingest button
        bottom = QtWidgets.QHBoxLayout()
        self.status_label = QtWidgets.QLabel("")
        self.status_label.setObjectName("stats")
        bottom.addWidget(self.status_label, 1)
        ingest_btn = QtWidgets.QPushButton("▶ Ingest Files")
        ingest_btn.setObjectName("primary")
        ingest_btn.clicked.connect(self._ingest)
        bottom.addWidget(ingest_btn)
        layout.addLayout(bottom)

    def _browse_root(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Project Root")
        if path:
            self.root_input.setText(path)

    def _add_files(self):
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(self, "Select Files")
        self.pending_files.extend(files)
        self._update_table_pending()

    def _add_directory(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Directory")
        if directory:
            for f in Path(directory).rglob("*"):
                if f.is_file():
                    self.pending_files.append(str(f))
            self._update_table_pending()

    def _clear(self):
        self.pending_files = []
        self.table.clear()
        self.status_label.setText("")

    def _update_table_pending(self):
        self.table.clear()
        for f in self.pending_files:
            cat = self.ingestor.classify(f)
            item = QtWidgets.QTreeWidgetItem([Path(f).name, cat, "—", "queued"])
            item.setForeground(3, QtGui.QBrush(QtGui.QColor(COLOR_PENDING)))
            self.table.addTopLevelItem(item)
        self.status_label.setText(f"{len(self.pending_files)} files queued")

    def _check_ready(self):
        """Return root if ready, else show status message and return None."""
        root = self.root_input.text().strip()
        if not root:
            self.status_label.setText("⚠ Select a project root first")
            return None
        if not self.pending_files:
            self.status_label.setText("⚠ No files queued — add files or a directory first")
            return None
        return root

    def _preview(self):
        root = self._check_ready()
        if not root:
            return
        pattern = self.rename_input.text().strip() or None
        results = self.ingestor.ingest(self.pending_files, root, pattern, dry_run=True)
        self.table.clear()
        for r in results:
            color = COLOR_ERROR if r["status"] == "error" else COLOR_PREVIEW
            item = QtWidgets.QTreeWidgetItem([
                r["original_name"], r["category"], r["target"], r["status"]
            ])
            item.setForeground(3, QtGui.QBrush(QtGui.QColor(color)))
            self.table.addTopLevelItem(item)
        self.status_label.setText(f"Preview: {len(results)} files")

    def _ingest(self):
        root = self._check_ready()
        if not root:
            return
        pattern = self.rename_input.text().strip() or None
        results = self.ingestor.ingest(self.pending_files, root, pattern, dry_run=False)
        self.table.clear()
        for r in results:
            color = COLOR_INGESTED if r["status"] == "ingested" else COLOR_ERROR
            item = QtWidgets.QTreeWidgetItem([
                r["original_name"], r["category"], r["target"], r["status"]
            ])
            item.setForeground(3, QtGui.QBrush(QtGui.QColor(color)))
            self.table.addTopLevelItem(item)
        ingested = sum(1 for r in results if r["status"] == "ingested")
        errors = sum(1 for r in results if r["status"] == "error")
        msg = f"✓ Ingested {ingested}/{len(results)} files"
        if errors:
            msg += f"  ·  ⚠ {errors} errors"
        self.status_label.setText(msg)
        self.pending_files = []

    def _apply_style(self):
        self.setStyleSheet("""
            QMainWindow { background: #0a0a0f; }
            QWidget { color: #e0e0e8; font-family: 'JetBrains Mono', 'Consolas', monospace; font-size: 12px; }
            #header { font-size: 20px; font-weight: bold; color: #00e5a0; padding: 8px 0; }
            #stats { color: #7a7a8e; font-size: 11px; }
            QLabel { color: #7a7a8e; }
            QLineEdit { background: #12121e; border: 1px solid #1e1e30; border-radius: 4px; padding: 8px; color: #e0e0e8; }
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
    window = IngestorWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
