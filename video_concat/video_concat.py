"""
Video Concatenator
Join multiple video files together with or without audio track.
Supports reordering, audio strip, and format output options.

Author: Ademir Pasalic
Requirements: pip install PySide6
Optional: ffmpeg in PATH
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path

try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    from PyQt5 import QtWidgets, QtCore, QtGui


class VideoConcatenator:
    """Core concatenation engine using ffmpeg."""

    @staticmethod
    def concatenate(video_paths, output_path, include_audio=True):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            for path in video_paths:
                f.write(f"file '{path}'\n")
            list_file = f.name

        audio_args = [] if include_audio else ["-an"]
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", list_file,
            "-c", "copy",
        ] + audio_args + [str(output_path)]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            os.unlink(list_file)
            if result.returncode == 0:
                return True, f"Created: {output_path}"
            return False, result.stderr[:300]
        except FileNotFoundError:
            os.unlink(list_file)
            return False, "ffmpeg not found in PATH"


class ConcatWindow(QtWidgets.QMainWindow):
    """Main GUI."""

    def __init__(self):
        super().__init__()
        self.concatenator = VideoConcatenator()
        self.video_paths = []
        self.setWindowTitle("Video Concatenator")
        self.setMinimumSize(700, 500)
        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        header = QtWidgets.QLabel("Video Concatenator")
        header.setObjectName("header")
        layout.addWidget(header)
        layout.addWidget(QtWidgets.QLabel("Drag to reorder. Videos will be joined top to bottom."))

        # Add buttons
        btn_row = QtWidgets.QHBoxLayout()
        add_btn = QtWidgets.QPushButton("+ Add Videos")
        add_btn.clicked.connect(self._add_videos)
        remove_btn = QtWidgets.QPushButton("Remove Selected")
        remove_btn.clicked.connect(self._remove_selected)
        clear_btn = QtWidgets.QPushButton("Clear All")
        clear_btn.clicked.connect(self._clear)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(remove_btn)
        btn_row.addWidget(clear_btn)
        move_up = QtWidgets.QPushButton("↑ Move Up")
        move_up.clicked.connect(self._move_up)
        move_down = QtWidgets.QPushButton("↓ Move Down")
        move_down.clicked.connect(self._move_down)
        btn_row.addStretch()
        btn_row.addWidget(move_up)
        btn_row.addWidget(move_down)
        layout.addLayout(btn_row)

        # Video list
        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        layout.addWidget(self.list_widget, 1)

        # Options
        opt_row = QtWidgets.QHBoxLayout()
        self.audio_cb = QtWidgets.QCheckBox("Include audio")
        self.audio_cb.setChecked(True)
        opt_row.addWidget(self.audio_cb)
        opt_row.addStretch()
        opt_row.addWidget(QtWidgets.QLabel("Output:"))
        self.output_input = QtWidgets.QLineEdit("concatenated_output.mp4")
        opt_row.addWidget(self.output_input, 1)
        browse_btn = QtWidgets.QPushButton("Browse")
        browse_btn.clicked.connect(self._browse_output)
        opt_row.addWidget(browse_btn)
        layout.addLayout(opt_row)

        # Concatenate
        bottom = QtWidgets.QHBoxLayout()
        self.status_label = QtWidgets.QLabel("")
        self.status_label.setObjectName("stats")
        bottom.addWidget(self.status_label, 1)
        concat_btn = QtWidgets.QPushButton("▶ Concatenate")
        concat_btn.setObjectName("primary")
        concat_btn.clicked.connect(self._concatenate)
        bottom.addWidget(concat_btn)
        layout.addLayout(bottom)

    def _add_videos(self):
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self, "Select Videos", "", "Video (*.mov *.mp4 *.avi *.mkv *.webm)"
        )
        for f in files:
            self.video_paths.append(f)
            self.list_widget.addItem(Path(f).name)
        self.status_label.setText(f"{len(self.video_paths)} videos in queue")

    def _remove_selected(self):
        for item in self.list_widget.selectedItems():
            row = self.list_widget.row(item)
            self.list_widget.takeItem(row)
            self.video_paths.pop(row)
        self.status_label.setText(f"{len(self.video_paths)} videos in queue")

    def _clear(self):
        self.video_paths = []
        self.list_widget.clear()
        self.status_label.setText("")

    def _move_up(self):
        row = self.list_widget.currentRow()
        if row > 0:
            self.video_paths[row], self.video_paths[row - 1] = self.video_paths[row - 1], self.video_paths[row]
            item = self.list_widget.takeItem(row)
            self.list_widget.insertItem(row - 1, item)
            self.list_widget.setCurrentRow(row - 1)

    def _move_down(self):
        row = self.list_widget.currentRow()
        if row < len(self.video_paths) - 1:
            self.video_paths[row], self.video_paths[row + 1] = self.video_paths[row + 1], self.video_paths[row]
            item = self.list_widget.takeItem(row)
            self.list_widget.insertItem(row + 1, item)
            self.list_widget.setCurrentRow(row + 1)

    def _browse_output(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Output File", "concatenated_output.mp4", "Video (*.mp4 *.mov *.mkv)"
        )
        if path:
            self.output_input.setText(path)

    def _concatenate(self):
        if len(self.video_paths) < 2:
            self.status_label.setText("⚠ Need at least 2 videos")
            return
        output = self.output_input.text().strip()
        if not output:
            return
        success, msg = self.concatenator.concatenate(
            self.video_paths, output, self.audio_cb.isChecked()
        )
        self.status_label.setText(f"✓ {msg}" if success else f"✗ {msg}")

    def _apply_style(self):
        self.setStyleSheet("""
            QMainWindow { background: #0a0a0f; }
            QWidget { color: #e0e0e8; font-family: 'JetBrains Mono', 'Consolas', monospace; font-size: 12px; }
            #header { font-size: 20px; font-weight: bold; color: #00e5a0; padding: 8px 0; }
            #stats { color: #7a7a8e; font-size: 11px; }
            QLabel { color: #7a7a8e; }
            QLineEdit { background: #12121e; border: 1px solid #1e1e30; border-radius: 4px; padding: 8px; color: #e0e0e8; }
            QCheckBox { color: #7a7a8e; }
            QListWidget { background: #0f0f18; border: 1px solid #1e1e30; border-radius: 4px; alternate-background-color: #12121e; }
            QListWidget::item { padding: 6px; }
            QListWidget::item:selected { background: #00e5a020; color: #00e5a0; }
            QPushButton { background: #12121e; border: 1px solid #1e1e30; border-radius: 4px; padding: 8px 16px; color: #7a7a8e; }
            QPushButton:hover { border-color: #00e5a0; color: #00e5a0; }
            QPushButton#primary { background: #00e5a0; color: #0a0a0f; border-color: #00e5a0; font-weight: bold; }
            QPushButton#primary:hover { background: transparent; color: #00e5a0; }
        """)


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = ConcatWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
