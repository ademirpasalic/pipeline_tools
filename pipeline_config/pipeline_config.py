"""
Pipeline Config Manager
Manage multi-project pipeline settings via YAML/JSON with a GUI editor.
Supports hierarchical configs, environment overrides, and validation.

Author: Ademir Pasalic
Requirements: pip install PySide6 PyYAML
"""

import copy
import os
import sys
import json
from pathlib import Path

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    from PyQt5 import QtWidgets, QtCore, QtGui


DEFAULT_PIPELINE_CONFIG = {
    "pipeline": {
        "version": "1.0",
        "studio": "My Studio",
    },
    "paths": {
        "project_root": "/projects/{project}",
        "asset_root": "{project_root}/assets/{asset_type}/{asset_name}",
        "shot_root": "{project_root}/shots/{sequence}/{shot}",
        "publish_root": "{project_root}/publish",
        "cache_root": "{project_root}/cache",
        "render_root": "{project_root}/renders",
    },
    "naming": {
        "asset_pattern": "{project}_{asset_type}_{asset_name}_v{version:03d}",
        "shot_pattern": "{project}_{sequence}_{shot}_{department}_v{version:03d}",
        "version_padding": 3,
    },
    "departments": ["model", "rig", "lookdev", "layout", "animation", "fx", "lighting", "comp"],
    "software": {
        "maya": {"version": "2024", "plugins": ["mtoa", "redshift"]},
        "houdini": {"version": "20.0", "plugins": []},
        "nuke": {"version": "15.0", "plugins": []},
    },
}


class ConfigManager:
    """Core config management."""

    def __init__(self, filepath=None):
        self.config = {}
        self.filepath = None
        if filepath:
            p = Path(filepath)
            if p.exists():
                self.load(filepath)
            else:
                self.config = copy.deepcopy(DEFAULT_PIPELINE_CONFIG)
                self.filepath = p
        else:
            self.config = copy.deepcopy(DEFAULT_PIPELINE_CONFIG)

    def new(self):
        self.config = copy.deepcopy(DEFAULT_PIPELINE_CONFIG)
        self.filepath = None

    def load(self, filepath):
        self.filepath = Path(filepath)
        try:
            with open(self.filepath) as f:
                if self.filepath.suffix in (".yaml", ".yml") and HAS_YAML:
                    self.config = yaml.safe_load(f)
                else:
                    self.config = json.load(f)
        except OSError as e:
            raise OSError(f"Cannot read config file: {e}") from e

    def save(self, filepath=None):
        path = Path(filepath) if filepath else self.filepath
        if not path:
            return
        self.filepath = path
        try:
            with open(path, "w") as f:
                if path.suffix in (".yaml", ".yml") and HAS_YAML:
                    yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)
                else:
                    json.dump(self.config, f, indent=2)
        except OSError as e:
            raise OSError(f"Cannot write config file: {e}") from e

    def get(self, dotted_key, default=None):
        """Get a config value using dot-notation (e.g. 'pipeline.studio')."""
        node = self.config
        for part in dotted_key.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def set(self, dotted_key, value):
        """Set a config value using dot-notation (e.g. 'pipeline.studio')."""
        parts = dotted_key.split(".")
        node = self.config
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value

    def resolve_path(self, dotted_key, **kwargs):
        """Look up a path template by dotted key and resolve it with kwargs."""
        template = self.get(dotted_key, dotted_key)
        if not isinstance(template, str):
            return ""
        # Build context: seed with kwargs, then resolve config path vars in order
        ctx = {**kwargs}
        for k, v in self.config.get("paths", {}).items():
            if isinstance(v, str):
                try:
                    ctx.setdefault(k, v.format(**ctx))
                except (KeyError, ValueError):
                    ctx.setdefault(k, v)
        try:
            return template.format(**ctx)
        except (KeyError, ValueError):
            return template

    def validate(self):
        errors = []
        if "paths" not in self.config:
            errors.append("Missing 'paths' section")
        if "naming" not in self.config:
            errors.append("Missing 'naming' section")
        if "departments" not in self.config:
            errors.append("Missing 'departments' section")
        return errors


class ConfigWindow(QtWidgets.QMainWindow):
    """Main GUI."""

    def __init__(self):
        super().__init__()
        self.manager = ConfigManager()
        self.manager.new()
        self._dirty = False
        self.setWindowTitle("Pipeline Config Manager")
        self.setMinimumSize(900, 600)
        self._build_ui()
        self._apply_style()
        self._display_config()

    def _build_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        header = QtWidgets.QLabel("Pipeline Config Manager")
        header.setObjectName("header")
        layout.addWidget(header)

        # Toolbar
        toolbar = QtWidgets.QHBoxLayout()
        new_btn = QtWidgets.QPushButton("New")
        new_btn.clicked.connect(self._new)
        load_btn = QtWidgets.QPushButton("Open")
        load_btn.clicked.connect(self._open)
        save_btn = QtWidgets.QPushButton("Save")
        save_btn.clicked.connect(self._save)
        save_as_btn = QtWidgets.QPushButton("Save As")
        save_as_btn.clicked.connect(self._save_as)
        validate_btn = QtWidgets.QPushButton("✓ Validate")
        validate_btn.setObjectName("primary")
        validate_btn.clicked.connect(self._validate)
        toolbar.addWidget(new_btn)
        toolbar.addWidget(load_btn)
        toolbar.addWidget(save_btn)
        toolbar.addWidget(save_as_btn)
        toolbar.addStretch()
        toolbar.addWidget(validate_btn)
        layout.addLayout(toolbar)

        # Split view: tree + editor
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        # Tree view of keys
        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderLabels(["Key", "Value"])
        self.tree.setColumnWidth(0, 250)
        self.tree.itemClicked.connect(self._on_tree_click)
        splitter.addWidget(self.tree)

        # Raw editor
        self.editor = QtWidgets.QTextEdit()
        self.editor.setPlaceholderText("Raw JSON/YAML editor")
        self.editor.setFontFamily("JetBrains Mono")
        splitter.addWidget(self.editor)

        splitter.setSizes([400, 500])
        layout.addWidget(splitter, 1)

        # Status
        bottom = QtWidgets.QHBoxLayout()
        self.status_label = QtWidgets.QLabel("New config")
        self.status_label.setObjectName("stats")
        bottom.addWidget(self.status_label)
        apply_btn = QtWidgets.QPushButton("Apply Editor Changes")
        apply_btn.clicked.connect(self._apply_editor)
        bottom.addWidget(apply_btn)
        layout.addLayout(bottom)

    def _display_config(self):
        self.tree.clear()
        self._add_dict_to_tree(self.manager.config, self.tree.invisibleRootItem())
        self.tree.expandAll()
        self._update_editor()

    def _add_dict_to_tree(self, data, parent):
        if isinstance(data, dict):
            for key, value in data.items():
                item = QtWidgets.QTreeWidgetItem(parent, [str(key), ""])
                item.setForeground(0, QtGui.QBrush(QtGui.QColor("#00e5a0")))
                self._add_dict_to_tree(value, item)
        elif isinstance(data, list):
            for i, value in enumerate(data):
                item = QtWidgets.QTreeWidgetItem(parent, [f"[{i}]", str(value)])
                item.setForeground(0, QtGui.QBrush(QtGui.QColor("#ffc040")))
        else:
            parent.setText(1, str(data))

    def _update_editor(self):
        if HAS_YAML:
            text = yaml.dump(self.manager.config, default_flow_style=False, sort_keys=False)
        else:
            text = json.dumps(self.manager.config, indent=2)
        self.editor.setPlainText(text)

    def _apply_editor(self):
        text = self.editor.toPlainText()
        try:
            if HAS_YAML:
                self.manager.config = yaml.safe_load(text)
            else:
                self.manager.config = json.loads(text)
            self._dirty = True
            self._display_config()
            self.status_label.setText("✓ Editor changes applied")
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Parse Error", f"Could not parse editor content:\n{e}")

    def _on_tree_click(self, item, col):
        path_parts = []
        current = item
        while current:
            path_parts.insert(0, current.text(0))
            current = current.parent()
        self.status_label.setText(" → ".join(path_parts))

    def _confirm_discard(self):
        """Return True if it's safe to discard unsaved changes."""
        if not self._dirty:
            return True
        reply = QtWidgets.QMessageBox.question(
            self, "Unsaved Changes",
            "You have unsaved changes. Discard them?",
            QtWidgets.QMessageBox.Discard | QtWidgets.QMessageBox.Cancel,
        )
        return reply == QtWidgets.QMessageBox.Discard

    def closeEvent(self, event):
        if self._confirm_discard():
            event.accept()
        else:
            event.ignore()

    def _new(self):
        if not self._confirm_discard():
            return
        self.manager.new()
        self._dirty = False
        self._display_config()
        self.status_label.setText("New config created")

    def _open(self):
        if not self._confirm_discard():
            return
        filters = "Config files (*.json *.yaml *.yml);;All files (*)"
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open Config", "", filters)
        if path:
            try:
                self.manager.load(path)
                self._dirty = False
                self._display_config()
                self.status_label.setText(f"Loaded: {path}")
            except OSError as e:
                QtWidgets.QMessageBox.warning(self, "Open Failed", str(e))

    def _save(self):
        if self.manager.filepath:
            try:
                self.manager.save()
                self._dirty = False
                self.status_label.setText(f"Saved: {self.manager.filepath}")
            except OSError as e:
                QtWidgets.QMessageBox.warning(self, "Save Failed", str(e))
        else:
            self._save_as()

    def _save_as(self):
        filters = "JSON (*.json);;YAML (*.yaml);;All files (*)"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Config", "pipeline_config.json", filters)
        if path:
            try:
                self.manager.save(path)
                self._dirty = False
                self.status_label.setText(f"Saved: {path}")
            except OSError as e:
                QtWidgets.QMessageBox.warning(self, "Save Failed", str(e))

    def _validate(self):
        errors = self.manager.validate()
        if errors:
            QtWidgets.QMessageBox.warning(self, "Validation", "\n".join(errors))
        else:
            QtWidgets.QMessageBox.information(self, "Validation", "✓ Config is valid!")

    def _apply_style(self):
        self.setStyleSheet("""
            QMainWindow { background: #0a0a0f; }
            QWidget { color: #e0e0e8; font-family: 'JetBrains Mono', 'Consolas', monospace; font-size: 12px; }
            #header { font-size: 20px; font-weight: bold; color: #00e5a0; padding: 8px 0; }
            #stats { color: #7a7a8e; font-size: 11px; }
            QLabel { color: #7a7a8e; }
            QTextEdit { background: #0f0f18; border: 1px solid #1e1e30; border-radius: 4px; padding: 8px; color: #e0e0e8; font-size: 12px; }
            QPushButton { background: #12121e; border: 1px solid #1e1e30; border-radius: 4px; padding: 8px 16px; color: #7a7a8e; }
            QPushButton:hover { border-color: #00e5a0; color: #00e5a0; }
            QPushButton#primary { background: #00e5a0; color: #0a0a0f; border-color: #00e5a0; font-weight: bold; }
            QPushButton#primary:hover { background: transparent; color: #00e5a0; }
            QTreeWidget { background: #0f0f18; border: 1px solid #1e1e30; border-radius: 4px; }
            QTreeWidget::item { padding: 3px; }
            QHeaderView::section { background: #12121e; border: 1px solid #1e1e30; padding: 6px; color: #00e5a0; font-weight: bold; }
            QSplitter::handle { background: #1e1e30; width: 2px; }
        """)

def main():
    app = QtWidgets.QApplication(sys.argv)
    window = ConfigWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
