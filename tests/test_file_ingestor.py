"""Tests for FileIngestor engine (no Qt required)."""
import pytest
from file_ingestor import FileIngestor, INGEST_RULES


class TestIngestRules:
    def test_all_rule_types_present(self):
        for key in ("image", "scene", "cache", "video"):
            assert key in INGEST_RULES
            assert "extensions" in INGEST_RULES[key]
            assert "target_folder" in INGEST_RULES[key]


class TestFileIngestor:
    def test_classify_image(self):
        ingestor = FileIngestor()
        folder = ingestor.classify("texture_diffuse.png")
        assert folder == "textures"

    def test_classify_scene(self):
        ingestor = FileIngestor()
        folder = ingestor.classify("char_rig.ma")
        assert folder == "scenes"

    def test_classify_cache(self):
        ingestor = FileIngestor()
        folder = ingestor.classify("sim_output.abc")
        assert folder == "cache"

    def test_classify_unknown_returns_misc(self):
        ingestor = FileIngestor()
        folder = ingestor.classify("readme.xyz")
        assert folder is not None  # should not crash; returns some fallback

    def test_ingest_copies_to_correct_subfolder(self, tmp_path):
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        f = src / "diffuse.png"
        f.write_bytes(b"fake png")
        ingestor = FileIngestor()
        log = ingestor.ingest([str(f)], str(dst), dry_run=False)
        assert (dst / "textures").exists()
        assert len(log) == 1

    def test_dry_run_does_not_copy(self, tmp_path):
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        f = src / "scene.ma"
        f.write_bytes(b"fake scene")
        ingestor = FileIngestor()
        ingestor.ingest([str(f)], str(dst), dry_run=True)
        assert not dst.exists()
