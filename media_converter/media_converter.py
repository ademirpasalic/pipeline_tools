"""
Media Converter
Convert between image and video formats with batch processing support.
Supports common production formats: EXR, PNG, JPG, TIFF, MOV, MP4, etc.

Author: Ademir Pasalic
Requirements: pip install PySide6 Pillow
Optional: ffmpeg in PATH for video conversion
"""

import os
import sys
import subprocess
from pathlib import Path

try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    from PyQt5 import QtWidgets, QtCore, QtGui


IMAGE_FORMATS = [".png", ".jpg", ".jpeg", ".tiff", ".tif", ".exr", ".bmp", ".tga"]
VIDEO_FORMATS = [".mov", ".mp4", ".avi", ".mkv", ".webm"]


class MediaConverter:
    """Core conversion engine using Pillow and ffmpeg."""

    @staticmethod
    def convert_image(source, target_format, output_dir=None, quality=95):
        try:
            from PIL import Image
        except ImportError:
            return None, "Pillow not installed"

        src = Path(source)
        out_dir = Path(output_dir) if output_dir else src.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        target = out_dir / f"{src.stem}{target_format}"

        try:
            img = Image.open(src)
            if target_format in (".jpg", ".jpeg") and img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.save(str(target), quality=quality)
            return str(target), None
        except Exception as e:
            return None, str(e)

    @staticmethod
    def convert_video(source, target_format, output_dir=None, codec=None):
        src = Path(source)
        out_dir = Path(output_dir) if output_dir else src.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        target = out_dir / f"{src.stem}{target_format}"

        codec_args = []
        if codec:
            codec_args = ["-c:v", codec]

        cmd = ["ffmpeg", "-y", "-i", str(src)] + codec_args + [str(target)]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return str(target), None
            return None, result.stderr[:400]
        except FileNotFoundError:
            return None, "ffmpeg not found in PATH"


class ConverterWindow(QtWidgets.QMainWindow):
    """Main GUI."""

    def __init__(self):
        super().__init__()
        self.converter = MediaConverter()
        self.files = []
        self.setWindowTitle("Media Converter")
        self.setMinimumSize(800, 550)
        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        header = QtWidgets.QLabel("Media Converter")
        header.setObjectName("header")
        layout.addWidget(header)

        # Source files
        src_row = QtWidgets.QHBoxLayout()
        add_files_btn = QtWidgets.QPushButton("+ Add Files")
        add_files_btn.clicked.connect(self._add_files)
        add_dir_btn = QtWidgets.QPushButton("+ Add Directory")
        add_dir_btn.clicked.connect(self._add_directory)
        clear_btn = QtWidgets.QPushButton("Clear")
        clear_btn.clicked.connect(self._clear)
        src_row.addWidget(add_files_btn)
        src_row.addWidget(add_dir_btn)
        src_row.addWidget(clear_btn)
        src_row.addStretch()
        layout.addLayout(src_row)

        # File list
        self.file_list = QtWidgets.QListWidget()
        self.file_list.setAlternatingRowColors(True)
        layout.addWidget(self.file_list, 1)

        # Options
        opt_row = QtWidgets.QHBoxLayout()
        opt_row.addWidget(QtWidgets.QLabel("Convert to:"))
        self.format_combo = QtWidgets.QComboBox()
        all_formats = IMAGE_FORMATS + VIDEO_FORMATS
        for fmt in all_formats:
            self.format_combo.addItem(fmt)
        opt_row.addWidget(self.format_combo)

        opt_row.addWidget(QtWidgets.QLabel("Output:"))
        self.output_input = QtWidgets.QLineEdit()
        self.output_input.setPlaceholderText("Same as source (or browse)")
        opt_row.addWidget(self.output_input, 1)
        out_browse = QtWidgets.QPushButton("Browse")
        out_browse.clicked.connect(self._browse_output)
        opt_row.addWidget(out_browse)
        layout.addLayout(opt_row)

        # Convert button
        bottom = QtWidgets.QHBoxLayout()
        self.status_label = QtWidgets.QLabel("")
        self.status_label.setObjectName("stats")
        bottom.addWidget(self.status_label, 1)
        convert_btn = QtWidgets.QPushButton("▶ Convert All")
        convert_btn.setObjectName("primary")
        convert_btn.clicked.connect(self._convert)
        bottom.addWidget(convert_btn)
        layout.addLayout(bottom)

    def _add_files(self):
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(self, "Select Files")
        for f in files:
            if f not in self.files:
                self.files.append(f)
                self.file_list.addItem(Path(f).name)
        self.status_label.setText(f"{len(self.files)} files loaded")

    def _add_directory(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Directory")
        if directory:
            for f in Path(directory).iterdir():
                if f.is_file() and f.suffix.lower() in IMAGE_FORMATS + VIDEO_FORMATS:
                    path = str(f)
                    if path not in self.files:
                        self.files.append(path)
                        self.file_list.addItem(f.name)
        self.status_label.setText(f"{len(self.files)} files loaded")

    def _clear(self):
        self.files = []
        self.file_list.clear()
        self.status_label.setText("")

    def _browse_output(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Output Directory")
        if path:
            self.output_input.setText(path)

    def _convert(self):
        if not self.files:
            return
        target_fmt = self.format_combo.currentText()
        output_dir = self.output_input.text().strip() or None
        success = 0
        error_details = []

        for i, filepath in enumerate(self.files):
            ext = Path(filepath).suffix.lower()
            if ext in IMAGE_FORMATS and target_fmt in IMAGE_FORMATS:
                result, err = self.converter.convert_image(filepath, target_fmt, output_dir)
            elif ext in VIDEO_FORMATS and target_fmt in VIDEO_FORMATS:
                result, err = self.converter.convert_video(filepath, target_fmt, output_dir)
            else:
                result, err = None, f"Unsupported: {ext} → {target_fmt}"

            item = self.file_list.item(i)
            if result:
                success += 1
                if item:
                    item.setForeground(QtGui.QColor("#00e5a0"))
            else:
                error_details.append(f"{Path(filepath).name}: {err}")
                if item:
                    item.setForeground(QtGui.QColor("#ff4060"))

        msg = f"✓ {success} converted"
        if error_details:
            msg += f"  ·  ✗ {len(error_details)} failed"
        self.status_label.setText(msg)

        if error_details:
            QtWidgets.QMessageBox.warning(
                self, "Conversion Errors",
                "\n".join(error_details),
            )

    def _apply_style(self):
        self.setStyleSheet("""
            QMainWindow { background: #0a0a0f; }
            QWidget { color: #e0e0e8; font-family: 'JetBrains Mono', 'Consolas', monospace; font-size: 12px; }
            #header { font-size: 20px; font-weight: bold; color: #00e5a0; padding: 8px 0; }
            #stats { color: #7a7a8e; font-size: 11px; }
            QLabel { color: #7a7a8e; }
            QLineEdit { background: #12121e; border: 1px solid #1e1e30; border-radius: 4px; padding: 8px; color: #e0e0e8; }
            QComboBox { background: #12121e; border: 1px solid #1e1e30; border-radius: 4px; padding: 6px; color: #e0e0e8; }
            QListWidget { background: #0f0f18; border: 1px solid #1e1e30; border-radius: 4px; alternate-background-color: #12121e; }
            QListWidget::item { padding: 4px; }
            QPushButton { background: #12121e; border: 1px solid #1e1e30; border-radius: 4px; padding: 8px 16px; color: #7a7a8e; }
            QPushButton:hover { border-color: #00e5a0; color: #00e5a0; }
            QPushButton#primary { background: #00e5a0; color: #0a0a0f; border-color: #00e5a0; font-weight: bold; }
            QPushButton#primary:hover { background: transparent; color: #00e5a0; }
        """)


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = ConverterWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
