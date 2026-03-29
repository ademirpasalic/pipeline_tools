"""Tests for FramesVideoConverter (no Qt required)."""
import pytest
from unittest.mock import patch, MagicMock
from frames_video import FramesVideoConverter


class TestFramesVideoConverter:
    def test_frames_to_video_builds_correct_command(self, tmp_path):
        captured = {}
        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            m = MagicMock()
            m.returncode = 0
            m.stderr = ""
            return m

        with patch("frames_video.subprocess.run", side_effect=fake_run):
            FramesVideoConverter.frames_to_video(
                str(tmp_path), "frame_%04d.png", str(tmp_path / "out.mp4"), fps=24
            )

        assert "ffmpeg" in captured["cmd"]
        assert "24" in captured["cmd"]
        assert str(tmp_path / "out.mp4") in captured["cmd"]

    def test_video_to_frames_builds_correct_command(self, tmp_path):
        captured = {}
        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            m = MagicMock()
            m.returncode = 0
            m.stderr = ""
            return m

        with patch("frames_video.subprocess.run", side_effect=fake_run):
            FramesVideoConverter.video_to_frames(
                str(tmp_path / "clip.mov"), str(tmp_path / "frames"), fmt="png"
            )

        assert "ffmpeg" in captured["cmd"]

    def test_detect_sequence_pattern(self, tmp_path):
        for i in range(1, 6):
            (tmp_path / f"frame_{i:04d}.png").write_bytes(b"")
        pattern, prefix, padding = FramesVideoConverter.detect_sequence(str(tmp_path))
        assert pattern is not None
        assert "png" in pattern
