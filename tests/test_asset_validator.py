"""Tests for AssetValidator engine (no Qt required)."""
import pytest
from asset_validator import AssetValidator, ValidationResult, DEFAULT_RULES


class TestValidationResult:
    def test_status_constants(self):
        assert ValidationResult.PASS == "pass"
        assert ValidationResult.WARN == "warn"
        assert ValidationResult.FAIL == "fail"

    def test_fields(self):
        r = ValidationResult(ValidationResult.FAIL, "naming", "bad name", "/a/b.txt")
        assert r.status == "fail"
        assert r.rule == "naming"
        assert r.message == "bad name"
        assert r.filepath == "/a/b.txt"
        assert r.timestamp


class TestAssetValidator:
    def test_uses_default_rules(self):
        v = AssetValidator()
        assert v.rules is DEFAULT_RULES

    def test_accepts_custom_rules(self):
        rules = {"naming": {"pattern": r".*", "max_length": 50, "description": "any"}}
        v = AssetValidator(rules=rules)
        assert v.rules is rules

    def test_validate_missing_path_returns_failures(self, tmp_path):
        v = AssetValidator()
        results = v.validate(str(tmp_path / "does_not_exist"))
        assert any(r.status == ValidationResult.FAIL for r in results)

    def test_validate_empty_dir_warns_missing_folders(self, tmp_path):
        v = AssetValidator()
        results = v.validate(str(tmp_path))
        statuses = {r.status for r in results}
        assert ValidationResult.WARN in statuses or ValidationResult.FAIL in statuses

    def test_valid_filename_passes_naming_rule(self, tmp_path):
        (tmp_path / "assets").mkdir()
        (tmp_path / "textures").mkdir()
        (tmp_path / "scenes").mkdir()
        (tmp_path / "cache").mkdir()
        (tmp_path / "output").mkdir()
        f = tmp_path / "assets" / "my_asset_v001.ma"
        f.write_text("dummy")
        v = AssetValidator()
        results = v.validate(str(tmp_path))
        naming_failures = [r for r in results if r.rule == "naming" and r.status == ValidationResult.FAIL]
        assert len(naming_failures) == 0

    def test_forbidden_char_in_filename_fails(self, tmp_path):
        (tmp_path / "assets").mkdir()
        f = tmp_path / "assets" / "bad name#.ma"
        f.write_text("dummy")
        v = AssetValidator()
        results = v.validate(str(tmp_path))
        assert any(r.status == ValidationResult.FAIL for r in results)
