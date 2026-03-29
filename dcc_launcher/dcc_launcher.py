"""
DCC Launcher / Environment Manager
Manages software versions, environment variables, and project configs.
Launch DCCs with the right environment per project.

Author: Ademir Pasalic
Requirements: pip install PySide6
"""

import os
import sys
import json
import subprocess
from pathlib import Path

try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    from PyQt5 import QtWidgets, QtCore, QtGui


DEFAULT_CONFIG = {
    "projects": {
        "example_project": {
            "name": "Example Project",
            "root": "/projects/example",
            "env": {
                "PROJECT_NAME": "example_project",
                "PROJECT_ROOT": "/projects/example",
                "ASSET_DIR": "/projects/example/assets",
                "SHOT_DIR": "/projects/example/shots",
                "CACHE_DIR": "/projects/example/cache",
            },
        }
    },
    "software": {
        "maya_2024": {
            "name": "Maya 2024",
            "executable": "C:/Program Files/Autodesk/Maya2024/bin/maya.exe",
            "icon": "maya",
            "env": {"MAYA_MODULE_PATH": "", "MAYA_PLUG_IN_PATH": ""},
        },
        "blender_4": {
            "name": "Blender 4.5.7",
            "executable": "C:/Program Files/Blender Foundation/Blender 4.5/blender.exe",
            "icon": "blender",
            "env": {},
        },
        "houdini_20": {
            "name": "Houdini 20",
            "executable": "C:/Program Files/Side Effects Software/Houdini 20.0/bin/houdini.exe",
            "icon": "houdini",
            "env": {},
        },
        "nuke_15": {
            "name": "Nuke 15",
            "executable": "C:/Program Files/Nuke15.0v1/Nuke15.0.exe",
            "icon": "nuke",
            "env": {},
        },
    },
}


class LauncherWindow(QtWidgets.QMainWindow):
    """Main GUI."""

    def __init__(self):
        super().__init__()
        self.config_path = Path("launcher_config.json")
        self.config = self._load_config()
        self.setWindowTitle("DCC Launcher")
        self.setMinimumSize(750, 500)
        self._build_ui()
        self._apply_style()

    def _load_config(self):
        if self.config_path.exists():
            with open(self.config_path) as f:
                return json.load(f)
        with open(self.config_path, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        return DEFAULT_CONFIG.copy()

    def _save_config(self):
        with open(self.config_path, "w") as f:
            json.dump(self.config, f, indent=2)

    def _build_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        header = QtWidgets.QLabel("DCC Launcher")
        header.setObjectName("header")
        layout.addWidget(header)
        layout.addWidget(QtWidgets.QLabel("Launch your tools with the right environment, every time."))

        # Project selector
        proj_row = QtWidgets.QHBoxLayout()
        proj_row.addWidget(QtWidgets.QLabel("Project:"))
        self.project_combo = QtWidgets.QComboBox()
        for key, proj in self.config["projects"].items():
            self.project_combo.addItem(proj["name"], key)
        self.project_combo.currentIndexChanged.connect(self._on_project_change)
        proj_row.addWidget(self.project_combo, 1)
        add_proj_btn = QtWidgets.QPushButton("+ Add Project")
        add_proj_btn.clicked.connect(self._add_project)
        proj_row.addWidget(add_proj_btn)
        layout.addLayout(proj_row)

        # Environment display
        self.env_display = QtWidgets.QTextEdit()
        self.env_display.setReadOnly(True)
        self.env_display.setMaximumHeight(120)
        self.env_display.setPlaceholderText("Select a project to see environment variables...")
        layout.addWidget(self.env_display)

        # Software grid
        layout.addWidget(QtWidgets.QLabel("Software"))
        self.software_grid = QtWidgets.QGridLayout()
        self.software_grid.setSpacing(12)
        self._populate_software_grid()
        layout.addLayout(self.software_grid)

        layout.addStretch()

        # Config buttons
        bottom = QtWidgets.QHBoxLayout()
        edit_config_btn = QtWidgets.QPushButton("Edit Config (JSON)")
        edit_config_btn.clicked.connect(self._edit_config)
        bottom.addWidget(edit_config_btn)
        bottom.addStretch()
        self.status_label = QtWidgets.QLabel("")
        self.status_label.setObjectName("stats")
        bottom.addWidget(self.status_label)
        layout.addLayout(bottom)

        self._on_project_change()

    def _populate_software_grid(self):
        col = 0
        for key, sw in self.config["software"].items():
            card = QtWidgets.QFrame()
            card.setObjectName("softwareCard")
            card_layout = QtWidgets.QVBoxLayout(card)
            card_layout.setSpacing(8)

            name_label = QtWidgets.QLabel(sw["name"])
            name_label.setObjectName("softwareName")
            card_layout.addWidget(name_label)

            path_label = QtWidgets.QLabel(sw["executable"])
            path_label.setObjectName("softwarePath")
            path_label.setWordWrap(True)
            card_layout.addWidget(path_label)

            launch_btn = QtWidgets.QPushButton(f"▶ Launch")
            launch_btn.setObjectName("primary")
            launch_btn.clicked.connect(lambda checked=False, k=key: self._launch(k))
            card_layout.addWidget(launch_btn)

            self.software_grid.addWidget(card, col // 3, col % 3)
            col += 1

    def _on_project_change(self):
        key = self.project_combo.currentData()
        if key and key in self.config["projects"]:
            env = self.config["projects"][key].get("env", {})
            lines = [f"{k} = {v}" for k, v in env.items()]
            self.env_display.setPlainText("\n".join(lines))

    def _launch(self, software_key):
        sw = self.config["software"].get(software_key, {})
        exe = sw.get("executable", "")

        # Build environment
        env = os.environ.copy()
        proj_key = self.project_combo.currentData()
        if proj_key and proj_key in self.config["projects"]:
            proj_env = self.config["projects"][proj_key].get("env", {})
            env.update(proj_env)
        sw_env = sw.get("env", {})
        env.update({k: v for k, v in sw_env.items() if v})

        if not Path(exe).exists():
            self.status_label.setText(f"⚠ Executable not found: {exe}")
            return

        try:
            subprocess.Popen([exe], env=env)
            self.status_label.setText(f"✓ Launched {sw['name']}")
        except Exception as e:
            self.status_label.setText(f"✗ Failed: {e}")

    def _add_project(self):
        name, ok = QtWidgets.QInputDialog.getText(self, "New Project", "Project name:")
        if ok and name:
            key = name.lower().replace(" ", "_")
            self.config["projects"][key] = {
                "name": name,
                "root": "",
                "env": {"PROJECT_NAME": key},
            }
            self._save_config()
            self.project_combo.addItem(name, key)

    def _edit_config(self):
        if sys.platform == "win32":
            os.startfile(str(self.config_path))
        else:
            subprocess.Popen(["xdg-open", str(self.config_path)])

    def _apply_style(self):
        self.setStyleSheet("""
            QMainWindow { background: #0a0a0f; }
            QWidget { color: #e0e0e8; font-family: 'JetBrains Mono', 'Consolas', monospace; font-size: 12px; }
            #header { font-size: 20px; font-weight: bold; color: #00e5a0; padding: 8px 0; }
            #stats { color: #7a7a8e; font-size: 11px; }
            QLabel { color: #7a7a8e; }
            QLineEdit, QTextEdit { background: #12121e; border: 1px solid #1e1e30; border-radius: 4px; padding: 8px; color: #e0e0e8; }
            QComboBox { background: #12121e; border: 1px solid #1e1e30; border-radius: 4px; padding: 6px; color: #e0e0e8; }
            QPushButton { background: #12121e; border: 1px solid #1e1e30; border-radius: 4px; padding: 8px 16px; color: #7a7a8e; }
            QPushButton:hover { border-color: #00e5a0; color: #00e5a0; }
            QPushButton#primary { background: #00e5a0; color: #0a0a0f; border-color: #00e5a0; font-weight: bold; }
            QPushButton#primary:hover { background: transparent; color: #00e5a0; }
            #softwareCard { background: #12121e; border: 1px solid #1e1e30; border-radius: 6px; padding: 16px; }
            #softwareCard:hover { border-color: #2a2a40; }
            #softwareName { color: #e0e0e8; font-size: 14px; font-weight: bold; }
            #softwarePath { color: #4a4a5e; font-size: 10px; }
        """)


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = LauncherWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
