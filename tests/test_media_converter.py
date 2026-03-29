"""Tests for MediaConverter (no Qt required)."""
import pytest
from unittest.mock import patch, MagicMock
from media_converter import MediaConverter, IMAGE_FORMATS, VIDEO_FORMATS


class TestMediaConverter:
    def test_format_lists(self):
        assert ".png" in IMAGE_FORMATS
        assert ".exr" in IMAGE_FORMATS
        assert ".mp4" in VIDEO_FORMATS
        assert ".mov" in VIDEO_FORMATS

    def test_convert_image_missing_pillow_returns_error(self, tmp_path):
        src = tmp_path / "test.png"
        src.write_bytes(b"fake png")
        with patch.dict("sys.modules", {"PIL": None, "PIL.Image": None}):
            result, error = MediaConverter.convert_image(str(src), ".jpg")
        assert error is not None

    def test_convert_image_success(self, tmp_path):
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("Pillow not installed")

        img = Image.new("RGB", (10, 10), color=(255, 0, 0))
        src = tmp_path / "test.png"
        img.save(str(src))
        result, error = MediaConverter.convert_image(str(src), ".jpg", output_dir=str(tmp_path))
        assert error is None
        assert result is not None
        assert result.endswith(".jpg")

    def test_convert_video_calls_ffmpeg(self, tmp_path):
        captured = {}
        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            m = MagicMock()
            m.returncode = 0
            m.stderr = ""
            return m

        with patch("media_converter.subprocess.run", side_effect=fake_run):
            MediaConverter.convert_video(str(tmp_path / "clip.mov"), ".mp4", str(tmp_path))

        assert "ffmpeg" in captured["cmd"]
