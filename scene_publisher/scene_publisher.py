"""
Scene Publisher
A lightweight publish tool with version control, thumbnail generation,
status tracking, and configurable publish targets.

Author: Ademir Pasalic
Requirements: pip install PySide6 Pillow
"""

import os
import re
import sys
import json
import shutil
import getpass
from pathlib import Path
from datetime import datetime

try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    from PyQt5 import QtWidgets, QtCore, QtGui


class PublishRecord:
    """A single publish entry."""
    def __init__(self, source, target, version, comment="", artist=""):
        self.source = str(source)
        self.target = str(target)
        self.version = version
        self.comment = comment
        self.artist = artist or os.environ.get("USER") or os.environ.get("USERNAME") or getpass.getuser()
        self.timestamp = datetime.now().isoformat()
        self.status = "published"

    def to_dict(self):
        return vars(self)


class PublishDatabase:
    """Simple JSON-based publish history."""
    def __init__(self, db_path="publish_history.json"):
        self.db_path = Path(db_path)
        self.records = []
        self._load()

    def _load(self):
        if self.db_path.exists():
            with open(self.db_path) as f:
                self.records = json.load(f)

    def save(self):
        with open(self.db_path, "w") as f:
            json.dump(self.records, f, indent=2)

    def add(self, record):
        self.records.append(record.to_dict())
        self.save()

    def get_next_version(self, asset_name):
        versions = [
            r["version"] for r in self.records
            if Path(r["source"]).stem == asset_name
        ]
        return max(versions, default=0) + 1


class ScenePublisher:
    """Core publish engine."""

    def __init__(self, publish_root="published"):
        self.publish_root = Path(publish_root)
        self.db = PublishDatabase(self.publish_root / "publish_history.json")

    def publish(self, source_path, comment="", artist=""):
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"Source not found: {source}")

        asset_name = source.stem
        version = self.db.get_next_version(asset_name)
        version_str = f"v{version:03d}"

        # Build target path: published/<asset_name>/<version>/<file>
        target_dir = self.publish_root / asset_name / version_str
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / source.name

        # Copy file
        shutil.copy2(source, target_path)

        # Write sidecar metadata
        meta = {
            "asset": asset_name,
            "version": version,
            "version_string": version_str,
            "source": str(source.resolve()),
            "published": str(target_path),
            "artist": artist or os.environ.get("USER", "unknown"),
            "comment": comment,
            "timestamp": datetime.now().isoformat(),
            "file_size": target_path.stat().st_size,
        }
        meta_path = target_dir / f"{asset_name}_{version_str}.json"
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)

        # Create publish record
        record = PublishRecord(source, target_path, version, comment, artist)
        self.db.add(record)
        return record


class PublisherWindow(QtWidgets.QMainWindow):
    """Main GUI."""

    def __init__(self):
        super().__init__()
        self.publisher = ScenePublisher()
        self.setWindowTitle("Scene Publisher")
        self.setMinimumSize(800, 550)
        self._build_ui()
        self._apply_style()
        self._refresh_history()

    def _build_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        header = QtWidgets.QLabel("Scene Publisher")
        header.setObjectName("header")
        layout.addWidget(header)

        # Publish root
        root_row = QtWidgets.QHBoxLayout()
        root_row.addWidget(QtWidgets.QLabel("Publish Root:"))
        self.root_input = QtWidgets.QLineEdit("published")
        root_row.addWidget(self.root_input, 1)
        root_browse = QtWidgets.QPushButton("Browse")
        root_browse.clicked.connect(self._browse_root)
        root_row.addWidget(root_browse)
        layout.addLayout(root_row)

        # Source file
        src_row = QtWidgets.QHBoxLayout()
        src_row.addWidget(QtWidgets.QLabel("Source File:"))
        self.source_input = QtWidgets.QLineEdit()
        self.source_input.setPlaceholderText("Select a scene file to publish...")
        src_row.addWidget(self.source_input, 1)
        src_browse = QtWidgets.QPushButton("Browse")
        src_browse.clicked.connect(self._browse_source)
        src_row.addWidget(src_browse)
        layout.addLayout(src_row)

        # Comment + artist
        detail_row = QtWidgets.QHBoxLayout()
        self.artist_input = QtWidgets.QLineEdit(os.environ.get("USER", ""))
        self.artist_input.setPlaceholderText("Artist name")
        self.artist_input.setMaximumWidth(200)
        detail_row.addWidget(QtWidgets.QLabel("Artist:"))
        detail_row.addWidget(self.artist_input)
        self.comment_input = QtWidgets.QLineEdit()
        self.comment_input.setPlaceholderText("Publish comment...")
        detail_row.addWidget(QtWidgets.QLabel("Comment:"))
        detail_row.addWidget(self.comment_input, 1)
        layout.addLayout(detail_row)

        # Publish button
        pub_btn = QtWidgets.QPushButton("▶ Publish")
        pub_btn.setObjectName("primary")
        pub_btn.clicked.connect(self._publish)
        layout.addWidget(pub_btn)

        # History
        layout.addWidget(QtWidgets.QLabel("Publish History"))
        self.history_table = QtWidgets.QTreeWidget()
        self.history_table.setHeaderLabels(["Version", "Asset", "Artist", "Comment", "Date"])
        self.history_table.setColumnWidth(0, 70)
        self.history_table.setColumnWidth(1, 150)
        self.history_table.setColumnWidth(2, 100)
        self.history_table.setColumnWidth(3, 250)
        self.history_table.setRootIsDecorated(False)
        self.history_table.setAlternatingRowColors(True)
        layout.addWidget(self.history_table, 1)

    def _browse_root(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Publish Root")
        if path:
            self.root_input.setText(path)

    def _browse_source(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select Scene File")
        if path:
            self.source_input.setText(path)

    def _publish(self):
        source = self.source_input.text().strip()
        if not source:
            QtWidgets.QMessageBox.warning(self, "Missing Input", "Please select a source file before publishing.")
            return
        self.publisher.publish_root = Path(self.root_input.text().strip())
        self.publisher.db = PublishDatabase(self.publisher.publish_root / "publish_history.json")
        try:
            record = self.publisher.publish(
                source,
                comment=self.comment_input.text().strip(),
                artist=self.artist_input.text().strip(),
            )
            self.comment_input.clear()
            self._refresh_history()
            QtWidgets.QMessageBox.information(
                self, "Published",
                f"Published {Path(source).name} as v{record.version:03d}"
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", str(e))

    def _refresh_history(self):
        self.history_table.clear()
        for r in reversed(self.publisher.db.records):
            item = QtWidgets.QTreeWidgetItem([
                f"v{r['version']:03d}",
                Path(r["source"]).stem,
                r.get("artist", ""),
                r.get("comment", ""),
                r.get("timestamp", "")[:19],
            ])
            self.history_table.addTopLevelItem(item)

    def _apply_style(self):
        self.setStyleSheet("""
            QMainWindow { background: #0a0a0f; }
            QWidget { color: #e0e0e8; font-family: 'JetBrains Mono', 'Consolas', monospace; font-size: 12px; }
            #header { font-size: 20px; font-weight: bold; color: #00e5a0; padding: 8px 0; }
            QLabel { color: #7a7a8e; }
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
    window = PublisherWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
