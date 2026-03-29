"""
Frames ↔ Video Converter
Convert image sequences to video and video to image sequences.
Supports EXR, PNG, JPG frames and MOV, MP4 video outputs.

Author: Ademir Pasalic
Requirements: pip install PySide6
Optional: ffmpeg in PATH
"""

import re
import sys
import subprocess
from pathlib import Path

try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    from PyQt5 import QtWidgets, QtCore, QtGui


# Formats recognised as image sequences
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".exr", ".tiff", ".tif")

# Video formats shown in the extract-frames combobox and file dialog filter
VIDEO_FORMATS = ("mov", "mp4", "avi", "mkv")

# Maximum characters of ffmpeg stderr to surface to the user
MAX_FFMPEG_ERROR = 400


class FramesVideoConverter:
    """Core conversion engine using ffmpeg."""

    @staticmethod
    def frames_to_video(frame_dir, pattern, output_path, fps=24, codec="libx264", crf=18):
        """Convert image sequence to video. Pattern uses ffmpeg syntax e.g. 'frame_%04d.png'."""
        input_pattern = str(Path(frame_dir) / pattern)
        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", input_pattern,
            "-c:v", codec,
            "-crf", str(crf),
            "-pix_fmt", "yuv420p",
            str(output_path),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0, result.stderr[:MAX_FFMPEG_ERROR] if result.returncode != 0 else ""
        except FileNotFoundError:
            return False, "ffmpeg not found in PATH"

    @staticmethod
    def video_to_frames(video_path, output_dir, fmt=".png", prefix="frame"):
        """Extract frames from video to image sequence."""
        fmt = fmt if fmt.startswith(".") else f".{fmt}"
        try:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
        except OSError as e:
            return False, f"Cannot create output directory: {e}"
        output_pattern = str(Path(output_dir) / f"{prefix}_%06d{fmt}")
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            output_pattern,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                count = len(list(Path(output_dir).glob(f"{prefix}_*{fmt}")))
                return True, f"Extracted {count} frames"
            return False, result.stderr[:MAX_FFMPEG_ERROR]
        except FileNotFoundError:
            return False, "ffmpeg not found in PATH"

    @staticmethod
    def detect_sequence(directory):
        """Auto-detect image sequence pattern in a directory.

        Returns (pattern, prefix, padding) where pattern uses ffmpeg %0Nd syntax.
        Returns (None, '', 0) if no numbered image sequence is found.
        """
        files = sorted(Path(directory).iterdir())
        image_files = [f for f in files if f.suffix.lower() in IMAGE_EXTENSIONS]
        if not image_files:
            return None, "", 0

        first = image_files[0].stem
        match = re.search(r"(\d+)$", first)
        if match:
            padding = len(match.group(1))
            prefix = first[:match.start()]
            ext = image_files[0].suffix
            pattern = f"{prefix}%0{padding}d{ext}"
            return pattern, prefix, padding
        return None, "", 0


class FramesVideoWindow(QtWidgets.QMainWindow):
    """Main GUI."""

    def __init__(self):
        super().__init__()
        self.converter = FramesVideoConverter()
        self.setWindowTitle("Frames ↔ Video")
        self.setMinimumSize(700, 480)
        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        header = QtWidgets.QLabel("Frames ↔ Video")
        header.setObjectName("header")
        layout.addWidget(header)

        # Mode tabs
        self.tabs = QtWidgets.QTabWidget()

        # ── Frames → Video tab ──
        f2v = QtWidgets.QWidget()
        f2v_layout = QtWidgets.QVBoxLayout(f2v)
        f2v_layout.setSpacing(10)

        row1 = QtWidgets.QHBoxLayout()
        row1.addWidget(QtWidgets.QLabel("Frame Directory:"))
        self.frame_dir_input = QtWidgets.QLineEdit()
        row1.addWidget(self.frame_dir_input, 1)
        browse1 = QtWidgets.QPushButton("Browse")
        browse1.clicked.connect(self._browse_frame_dir)
        row1.addWidget(browse1)
        f2v_layout.addLayout(row1)

        row2 = QtWidgets.QHBoxLayout()
        row2.addWidget(QtWidgets.QLabel("Pattern:"))
        self.pattern_input = QtWidgets.QLineEdit()
        self.pattern_input.setPlaceholderText("Auto-detected or e.g. frame_%04d.png")
        row2.addWidget(self.pattern_input, 1)
        detect_btn = QtWidgets.QPushButton("Auto-Detect")
        detect_btn.clicked.connect(self._detect_pattern)
        row2.addWidget(detect_btn)
        f2v_layout.addLayout(row2)

        row3 = QtWidgets.QHBoxLayout()
        row3.addWidget(QtWidgets.QLabel("FPS:"))
        self.fps_spin = QtWidgets.QSpinBox()
        self.fps_spin.setRange(1, 120)
        self.fps_spin.setValue(24)
        row3.addWidget(self.fps_spin)
        row3.addWidget(QtWidgets.QLabel("Output:"))
        self.f2v_output = QtWidgets.QLineEdit()
        self.f2v_output.setPlaceholderText("output.mp4")
        row3.addWidget(self.f2v_output, 1)
        f2v_layout.addLayout(row3)

        f2v_btn = QtWidgets.QPushButton("▶ Convert Frames → Video")
        f2v_btn.setObjectName("primary")
        f2v_btn.clicked.connect(self._frames_to_video)
        f2v_layout.addWidget(f2v_btn)
        f2v_layout.addStretch()

        self.tabs.addTab(f2v, "Frames → Video")

        # ── Video → Frames tab ──
        v2f = QtWidgets.QWidget()
        v2f_layout = QtWidgets.QVBoxLayout(v2f)
        v2f_layout.setSpacing(10)

        row4 = QtWidgets.QHBoxLayout()
        row4.addWidget(QtWidgets.QLabel("Video File:"))
        self.video_input = QtWidgets.QLineEdit()
        row4.addWidget(self.video_input, 1)
        browse2 = QtWidgets.QPushButton("Browse")
        browse2.clicked.connect(self._browse_video)
        row4.addWidget(browse2)
        v2f_layout.addLayout(row4)

        row5 = QtWidgets.QHBoxLayout()
        row5.addWidget(QtWidgets.QLabel("Output Dir:"))
        self.v2f_output = QtWidgets.QLineEdit()
        row5.addWidget(self.v2f_output, 1)
        browse3 = QtWidgets.QPushButton("Browse")
        browse3.clicked.connect(self._browse_v2f_output)
        row5.addWidget(browse3)
        row5.addWidget(QtWidgets.QLabel("Format:"))
        self.v2f_format = QtWidgets.QComboBox()
        self.v2f_format.addItems([f".{ext}" for ext in ("png", "jpg", "exr", "tiff")])
        row5.addWidget(self.v2f_format)
        v2f_layout.addLayout(row5)

        v2f_btn = QtWidgets.QPushButton("▶ Convert Video → Frames")
        v2f_btn.setObjectName("primary")
        v2f_btn.clicked.connect(self._video_to_frames)
        v2f_layout.addWidget(v2f_btn)
        v2f_layout.addStretch()

        self.tabs.addTab(v2f, "Video → Frames")
        layout.addWidget(self.tabs, 1)

        # Status
        self.status_label = QtWidgets.QLabel("")
        self.status_label.setObjectName("stats")
        layout.addWidget(self.status_label)

    def _browse_frame_dir(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Frame Directory")
        if path:
            self.frame_dir_input.setText(path)
            self._detect_pattern()

    def _browse_video(self):
        video_filter = "Video (" + " ".join(f"*.{f}" for f in VIDEO_FORMATS) + ")"
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select Video", "", video_filter)
        if path:
            self.video_input.setText(path)

    def _browse_v2f_output(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Output Directory")
        if path:
            self.v2f_output.setText(path)

    def _detect_pattern(self):
        directory = self.frame_dir_input.text().strip()
        if not directory:
            return
        files = list(Path(directory).iterdir()) if Path(directory).is_dir() else []
        image_files = [f for f in files if f.suffix.lower() in IMAGE_EXTENSIONS]
        if not image_files:
            self.status_label.setText("⚠ No image files found in directory")
            return
        pattern, prefix, padding = self.converter.detect_sequence(directory)
        if pattern:
            self.pattern_input.setText(pattern)
            self.status_label.setText(f"Detected: {pattern} ({len(image_files)} files)")
        else:
            self.status_label.setText(
                f"⚠ Found {len(image_files)} image files but no numbered sequence — "
                "ensure filenames end with digits (e.g. frame_001.png)"
            )

    def _frames_to_video(self):
        frame_dir = self.frame_dir_input.text().strip()
        pattern = self.pattern_input.text().strip()
        output = self.f2v_output.text().strip()
        if not all([frame_dir, pattern, output]):
            self.status_label.setText("⚠ Fill in all fields")
            return
        if not Path(output).is_absolute():
            output = str(Path(frame_dir) / output)
        self.status_label.setText("Converting…")
        QtWidgets.QApplication.processEvents()
        success, msg = self.converter.frames_to_video(frame_dir, pattern, output, self.fps_spin.value())
        self.status_label.setText(f"✓ Video created: {output}" if success else f"✗ {msg}")

    def _video_to_frames(self):
        video = self.video_input.text().strip()
        output_dir = self.v2f_output.text().strip()
        fmt = self.v2f_format.currentText()
        if not all([video, output_dir]):
            self.status_label.setText("⚠ Fill in all fields")
            return
        self.status_label.setText("Extracting frames…")
        QtWidgets.QApplication.processEvents()
        success, msg = self.converter.video_to_frames(video, output_dir, fmt)
        self.status_label.setText(f"✓ {msg}" if success else f"✗ {msg}")

    def _apply_style(self):
        self.setStyleSheet("""
            QMainWindow { background: #0a0a0f; }
            QWidget { color: #e0e0e8; font-family: 'JetBrains Mono', 'Consolas', monospace; font-size: 12px; }
            #header { font-size: 20px; font-weight: bold; color: #00e5a0; padding: 8px 0; }
            #stats { color: #7a7a8e; font-size: 11px; padding: 4px 0; }
            QLabel { color: #7a7a8e; }
            QLineEdit { background: #12121e; border: 1px solid #1e1e30; border-radius: 4px; padding: 8px; color: #e0e0e8; }
            QComboBox { background: #12121e; border: 1px solid #1e1e30; border-radius: 4px; padding: 6px; color: #e0e0e8; }
            QSpinBox { background: #12121e; border: 1px solid #1e1e30; border-radius: 4px; padding: 6px; color: #e0e0e8; }
            QTabWidget::pane { border: 1px solid #1e1e30; background: #0a0a0f; }
            QTabBar::tab { background: #12121e; border: 1px solid #1e1e30; padding: 8px 16px; color: #7a7a8e; }
            QTabBar::tab:selected { color: #00e5a0; border-bottom-color: #00e5a0; }
            QPushButton { background: #12121e; border: 1px solid #1e1e30; border-radius: 4px; padding: 8px 16px; color: #7a7a8e; }
            QPushButton:hover { border-color: #00e5a0; color: #00e5a0; }
            QPushButton#primary { background: #00e5a0; color: #0a0a0f; border-color: #00e5a0; font-weight: bold; }
            QPushButton#primary:hover { background: transparent; color: #00e5a0; }
        """)


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = FramesVideoWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
