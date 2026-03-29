"""Tests for RenameEngine (no Qt required)."""
import pytest
from batch_renamer import RenameEngine, PRESETS


class TestRenameEngine:
    def test_preview_returns_list(self, tmp_path):
        f = tmp_path / "My File.txt"
        f.write_text("x")
        engine = RenameEngine()
        previews = engine.preview([str(f)], find=r"\s", replace="_")
        assert isinstance(previews, list)
        assert len(previews) == 1

    def test_preview_does_not_rename(self, tmp_path):
        f = tmp_path / "My File.txt"
        f.write_text("x")
        engine = RenameEngine()
        engine.preview([str(f)], find=r"\s", replace="_")
        assert f.exists(), "preview must not rename files"

    def test_lowercase_snake_preset(self, tmp_path):
        f = tmp_path / "My-File Name.txt"
        f.write_text("x")
        engine = RenameEngine()
        preset = PRESETS["lowercase_snake"]
        previews = engine.preview(
            [str(f)],
            find=preset["find"],
            replace=preset["replace"],
            lowercase=preset["lowercase"],
        )
        new_name = previews[0][1]
        assert new_name == "my_file_name.txt"

    def test_remove_version_preset(self, tmp_path):
        f = tmp_path / "asset_v003.ma"
        f.write_text("x")
        engine = RenameEngine()
        preset = PRESETS["remove_version"]
        previews = engine.preview([str(f)], find=preset["find"], replace=preset["replace"])
        new_name = previews[0][1]
        assert "v003" not in new_name

    def test_apply_renames_file(self, tmp_path):
        f = tmp_path / "My File.txt"
        f.write_text("x")
        engine = RenameEngine()
        previews = engine.preview([str(f)], find=r"\s", replace="_")
        engine.apply(previews)
        assert (tmp_path / "My_File.txt").exists()
        assert not f.exists()
