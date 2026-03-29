"""Tests for TrackerDatabase (no Qt required)."""
import pytest
from production_tracker import TrackerDatabase, STATUSES, DEPARTMENTS


class TestTrackerDatabase:
    def test_empty_on_new_db(self, tmp_path):
        db = TrackerDatabase(str(tmp_path / "test_db.json"))
        assert db.shots == []

    def test_add_shot(self, tmp_path):
        db = TrackerDatabase(str(tmp_path / "test_db.json"))
        db.add(name="101_0010", department="Layout", artist="Alice", status="Not Started")
        assert len(db.shots) == 1
        assert db.shots[0]["name"] == "101_0010"

    def test_update_shot_status(self, tmp_path):
        db = TrackerDatabase(str(tmp_path / "test_db.json"))
        db.add(name="101_0010", department="Layout", artist="Alice", status="Not Started")
        shot_id = db.shots[0]["id"]
        db.update(shot_id, status="In Progress")
        assert db.shots[0]["status"] == "In Progress"

    def test_delete_shot(self, tmp_path):
        db = TrackerDatabase(str(tmp_path / "test_db.json"))
        db.add(name="101_0010", department="Layout", artist="Alice", status="Not Started")
        shot_id = db.shots[0]["id"]
        db.delete(shot_id)
        assert db.shots == []

    def test_get_stats(self, tmp_path):
        db = TrackerDatabase(str(tmp_path / "test_db.json"))
        db.add(name="101_0010", department="Layout", artist="Alice", status="Not Started")
        db.add(name="101_0020", department="Animation", artist="Bob", status="In Progress")
        stats = db.get_stats()
        assert stats["total"] == 2
        assert stats["Not Started"] == 1
        assert stats["In Progress"] == 1

    def test_persistence(self, tmp_path):
        path = str(tmp_path / "test_db.json")
        db1 = TrackerDatabase(path)
        db1.add(name="persist_shot", department="FX", artist="Charlie", status="Review")
        db2 = TrackerDatabase(path)
        assert len(db2.shots) == 1
        assert db2.shots[0]["name"] == "persist_shot"

    def test_valid_statuses_defined(self):
        for s in ("Not Started", "In Progress", "Review", "Approved", "Final"):
            assert s in STATUSES
