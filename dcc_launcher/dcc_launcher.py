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

from shared.logging_config import get_logger
from shared.settings import AppSettings

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
WINDOW_TITLE = "DCC Launcher"
WINDOW_MIN_WIDTH = 750
WINDOW_MIN_HEIGHT = 500
ENV_DISPLAY_MAX_HEIGHT = 120
SOFTWARE_GRID_COLUMNS = 3
CONFIG_FILENAME = "launcher_config.json"
TOOL_NAME = "dcc_launcher"

# Config top-level keys
KEY_PROJECTS = "projects"
KEY_SOFTWARE = "software"
KEY_ENV = "env"
KEY_NAME = "name"
KEY_ROOT = "root"
KEY_EXECUTABLE = "executable"
KEY_ICON = "icon"

# Default project environment variable names
ENV_KEY_PROJECT_NAME = "PROJECT_NAME"
ENV_KEY_PROJECT_ROOT = "PROJECT_ROOT"
ENV_KEY_ASSET_DIR = "ASSET_DIR"
ENV_KEY_SHOT_DIR = "SHOT_DIR"
ENV_KEY_CACHE_DIR = "CACHE_DIR"

DEFAULT_CONFIG = {
    KEY_PROJECTS: {
        "example_project": {
            KEY_NAME: "Example Project",
            KEY_ROOT: "/projects/example",
            KEY_ENV: {
                ENV_KEY_PROJECT_NAME: "example_project",
                ENV_KEY_PROJECT_ROOT: "/projects/example",
                ENV_KEY_ASSET_DIR: "/projects/example/assets",
                ENV_KEY_SHOT_DIR: "/projects/example/shots",
                ENV_KEY_CACHE_DIR: "/projects/example/cache",
            },
        }
    },
    KEY_SOFTWARE: {
        "maya_2024": {
            KEY_NAME: "Maya 2024",
            KEY_EXECUTABLE: "C:/Program Files/Autodesk/Maya2024/bin/maya.exe",
            KEY_ICON: "maya",
            KEY_ENV: {"MAYA_MODULE_PATH": "", "MAYA_PLUG_IN_PATH": ""},
        },
        "blender_4": {
            KEY_NAME: "Blender 4.5.7",
            KEY_EXECUTABLE: "C:/Program Files/Blender Foundation/Blender 4.5/blender.exe",
            KEY_ICON: "blender",
            KEY_ENV: {},
        },
        "houdini_20": {
            KEY_NAME: "Houdini 20",
            KEY_EXECUTABLE: "C:/Program Files/Side Effects Software/Houdini 20.0/bin/houdini.exe",
            KEY_ICON: "houdini",
            KEY_ENV: {},
        },
        "nuke_15": {
            KEY_NAME: "Nuke 15",
            KEY_EXECUTABLE: "C:/Program Files/Nuke15.0v1/Nuke15.0.exe",
            KEY_ICON: "nuke",
            KEY_ENV: {},
        },
    },
}


class LauncherWindow(QtWidgets.QMainWindow):
    """Main window for the DCC Launcher application.

    Loads project and software configuration from ``launcher_config.json``,
    presents a project selector and a software card grid, and launches the
    selected DCC with a merged environment.
    """

    def __init__(self) -> None:
        """Initialise the launcher window, load config, and build the UI."""
        super().__init__()
        self.config_path = Path(CONFIG_FILENAME)
        self.config = self._load_config()
        self.settings = AppSettings(TOOL_NAME)
        self._launch_buttons: list[QtWidgets.QPushButton] = []
        self.setWindowTitle(WINDOW_TITLE)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self._build_ui()
        self._apply_style()

    def _load_config(self) -> dict:
        """Load launcher configuration from disk, creating defaults if absent.

        Returns:
            Parsed configuration dictionary with ``projects`` and ``software``
            top-level keys.
        """
        if self.config_path.exists():
            with open(self.config_path) as f:
                return json.load(f)
        logger.info("No config found at %s — writing defaults", self.config_path)
        with open(self.config_path, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        return DEFAULT_CONFIG.copy()

    def _save_config(self) -> None:
        """Persist the current in-memory config back to ``launcher_config.json``."""
        with open(self.config_path, "w") as f:
            json.dump(self.config, f, indent=2)

    def _build_ui(self) -> None:
        """Construct and lay out all widgets in the main window."""
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        header = QtWidgets.QLabel(WINDOW_TITLE)
        header.setObjectName("header")
        layout.addWidget(header)
        layout.addWidget(QtWidgets.QLabel("Launch your tools with the right environment, every time."))

        # Project selector
        proj_row = QtWidgets.QHBoxLayout()
        proj_row.addWidget(QtWidgets.QLabel("Project:"))
        self.project_combo = QtWidgets.QComboBox()
        for key, proj in self.config[KEY_PROJECTS].items():
            self.project_combo.addItem(proj[KEY_NAME], key)
        self.project_combo.currentIndexChanged.connect(self._on_project_change)
        self.project_combo.currentIndexChanged.connect(self._update_ui)
        proj_row.addWidget(self.project_combo, 1)
        add_proj_btn = QtWidgets.QPushButton("+ Add Project")
        add_proj_btn.clicked.connect(self._add_project)
        proj_row.addWidget(add_proj_btn)
        layout.addLayout(proj_row)

        # Environment display
        self.env_display = QtWidgets.QTextEdit()
        self.env_display.setReadOnly(True)
        self.env_display.setMaximumHeight(ENV_DISPLAY_MAX_HEIGHT)
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
        self._update_ui()

    def _populate_software_grid(self) -> None:
        """Create and add a card widget for each software entry in the config."""
        self._launch_buttons.clear()
        col = 0
        for key, sw in self.config[KEY_SOFTWARE].items():
            card = QtWidgets.QFrame()
            card.setObjectName("softwareCard")
            card_layout = QtWidgets.QVBoxLayout(card)
            card_layout.setSpacing(8)

            name_label = QtWidgets.QLabel(sw[KEY_NAME])
            name_label.setObjectName("softwareName")
            card_layout.addWidget(name_label)

            path_label = QtWidgets.QLabel(sw[KEY_EXECUTABLE])
            path_label.setObjectName("softwarePath")
            path_label.setWordWrap(True)
            card_layout.addWidget(path_label)

            launch_btn = QtWidgets.QPushButton("▶ Launch")
            launch_btn.setObjectName("primary")
            launch_btn.clicked.connect(lambda checked=False, k=key: self._launch(k))
            card_layout.addWidget(launch_btn)
            self._launch_buttons.append(launch_btn)

            self.software_grid.addWidget(card, col // SOFTWARE_GRID_COLUMNS, col % SOFTWARE_GRID_COLUMNS)
            col += 1

    def _update_ui(self) -> None:
        """Enable or disable all Launch buttons based on whether a project is selected."""
        has_project = self.project_combo.currentIndex() >= 0 and self.project_combo.currentData() is not None
        for btn in self._launch_buttons:
            btn.setEnabled(has_project)

    def _on_project_change(self) -> None:
        """Refresh the environment variable display when the selected project changes."""
        key = self.project_combo.currentData()
        if key and key in self.config[KEY_PROJECTS]:
            env = self.config[KEY_PROJECTS][key].get(KEY_ENV, {})
            lines = [f"{k} = {v}" for k, v in env.items()]
            self.env_display.setPlainText("\n".join(lines))

    def _launch(self, software_key: str) -> None:
        """Launch a DCC application with the merged project and software environment.

        Args:
            software_key: Key identifying the software entry in ``config["software"]``.
        """
        sw = self.config[KEY_SOFTWARE].get(software_key, {})
        exe = sw.get(KEY_EXECUTABLE, "")

        # Build environment
        env = os.environ.copy()
        proj_key = self.project_combo.currentData()
        if proj_key and proj_key in self.config[KEY_PROJECTS]:
            proj_env = self.config[KEY_PROJECTS][proj_key].get(KEY_ENV, {})
            env.update(proj_env)
        sw_env = sw.get(KEY_ENV, {})
        env.update({k: v for k, v in sw_env.items() if v})

        if not Path(exe).exists():
            logger.error("Executable not found for %s: %s", sw.get(KEY_NAME, software_key), exe)
            self.status_label.setText(f"⚠ Executable not found: {exe}")
            return

        try:
            subprocess.Popen([exe], env=env)
            logger.info("Launched %s (%s)", sw.get(KEY_NAME, software_key), exe)
            self.status_label.setText(f"✓ Launched {sw[KEY_NAME]}")
        except Exception as e:
            logger.error("Failed to launch %s: %s", sw.get(KEY_NAME, software_key), e)
            self.status_label.setText(f"✗ Failed: {e}")

    def _add_project(self) -> None:
        """Prompt the user for a new project name and add it to the config."""
        name, ok = QtWidgets.QInputDialog.getText(self, "New Project", "Project name:")
        if ok and name:
            key = name.lower().replace(" ", "_")
            self.config[KEY_PROJECTS][key] = {
                KEY_NAME: name,
                KEY_ROOT: "",
                KEY_ENV: {ENV_KEY_PROJECT_NAME: key},
            }
            self._save_config()
            self.project_combo.addItem(name, key)

    def _edit_config(self) -> None:
        """Open ``launcher_config.json`` in the platform default editor."""
        if sys.platform == "win32":
            os.startfile(str(self.config_path))
        else:
            subprocess.Popen(["xdg-open", str(self.config_path)])

    def _apply_style(self) -> None:
        """Apply the dark stylesheet to the main window."""
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

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        """Restore saved window geometry after the window is shown.

        Args:
            event: The Qt show event.
        """
        super().showEvent(event)
        self.settings.restore_geometry(self)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """Save window geometry before the window closes.

        Args:
            event: The Qt close event.
        """
        self.settings.save_geometry(self)
        super().closeEvent(event)


def main() -> None:
    """Create the QApplication and launch the DCC Launcher window."""
    app = QtWidgets.QApplication(sys.argv)
    window = LauncherWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
