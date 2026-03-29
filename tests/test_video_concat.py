"""Tests for VideoConcatenator (no Qt required)."""
import pytest
from unittest.mock import patch, MagicMock
from video_concat import VideoConcatenator


class TestVideoConcatenator:
    def test_concatenate_builds_ffmpeg_command(self, tmp_path):
        captured = {}
        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            m = MagicMock()
            m.returncode = 0
            m.stderr = ""
            return m

        clips = [str(tmp_path / "a.mp4"), str(tmp_path / "b.mp4")]
        output = str(tmp_path / "out.mp4")

        with patch("video_concat.subprocess.run", side_effect=fake_run):
            VideoConcatenator.concatenate(clips, output, include_audio=True)

        assert "ffmpeg" in captured["cmd"]
        assert output in captured["cmd"]

    def test_strip_audio_adds_an_flag(self, tmp_path):
        captured = {}
        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            m = MagicMock()
            m.returncode = 0
            m.stderr = ""
            return m

        clips = [str(tmp_path / "a.mp4")]
        output = str(tmp_path / "out.mp4")

        with patch("video_concat.subprocess.run", side_effect=fake_run):
            VideoConcatenator.concatenate(clips, output, include_audio=False)

        assert "-an" in captured["cmd"]

    def test_include_audio_omits_an_flag(self, tmp_path):
        captured = {}
        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            m = MagicMock()
            m.returncode = 0
            m.stderr = ""
            return m

        with patch("video_concat.subprocess.run", side_effect=fake_run):
            VideoConcatenator.concatenate([str(tmp_path / "a.mp4")], str(tmp_path / "out.mp4"), include_audio=True)

        assert "-an" not in captured["cmd"]
