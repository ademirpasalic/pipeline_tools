"""Tests for FileCollector engine (no Qt required)."""
import json
import pytest
from file_collector import FileCollector


class TestFileCollector:
    def test_add_file(self, tmp_path):
        f = tmp_path / "render.exr"
        f.write_text("x")
        fc = FileCollector()
        fc.add_file(str(f), category="renders")
        assert len(fc.sources) == 1
        assert fc.sources[0][1] == "renders"

    def test_add_directory(self, tmp_path):
        for name in ("a.png", "b.exr", "c.ma"):
            (tmp_path / name).write_text("x")
        fc = FileCollector()
        fc.add_directory(str(tmp_path))
        assert len(fc.sources) == 3

    def test_add_directory_extension_filter(self, tmp_path):
        (tmp_path / "a.png").write_text("x")
        (tmp_path / "b.exr").write_text("x")
        fc = FileCollector()
        fc.add_directory(str(tmp_path), extensions=[".png"])
        assert len(fc.sources) == 1

    def test_clear(self, tmp_path):
        f = tmp_path / "a.txt"
        f.write_text("x")
        fc = FileCollector()
        fc.add_file(str(f))
        fc.clear()
        assert fc.sources == []

    def test_collect_copies_files_and_writes_manifest(self, tmp_path):
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        (src / "render_001.exr").write_bytes(b"fake")
        fc = FileCollector()
        fc.add_file(str(src / "render_001.exr"), category="renders")
        manifest_path, errors = fc.collect(str(dst))
        assert errors == []
        assert (dst / "renders" / "render_001.exr").exists()
        with open(manifest_path) as fh:
            manifest = json.load(fh)
        assert manifest["total_files"] == 1

    def test_collect_computes_md5(self, tmp_path):
        src = tmp_path / "file.txt"
        src.write_bytes(b"hello")
        fc = FileCollector()
        fc.add_file(str(src))
        manifest_path, _ = fc.collect(str(tmp_path / "out"))
        with open(manifest_path) as fh:
            manifest = json.load(fh)
        assert manifest["files"][0]["md5"]
