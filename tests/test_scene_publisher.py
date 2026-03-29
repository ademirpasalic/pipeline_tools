"""Tests for ScenePublisher / PublishDatabase (no Qt required)."""
import pytest
from scene_publisher import ScenePublisher, PublishDatabase, PublishRecord


class TestPublishRecord:
    def test_fields(self):
        r = PublishRecord(source="/src/scene.ma", target="/pub/v001/scene.ma", version="v001")
        assert r.source == "/src/scene.ma"
        assert r.version == "v001"
        assert r.status == "published"
        assert r.timestamp

    def test_to_dict_is_serializable(self):
        import json
        r = PublishRecord("/src/s.ma", "/pub/v001/s.ma", "v001", comment="initial", artist="ada")
        d = r.to_dict()
        json.dumps(d)  # must not raise


class TestPublishDatabase:
    def test_empty_on_init(self, tmp_path):
        db = PublishDatabase(str(tmp_path / "pub_db.json"))
        assert db.records == []

    def test_add_and_retrieve(self, tmp_path):
        db = PublishDatabase(str(tmp_path / "pub_db.json"))
        r = PublishRecord("/src/s.ma", "/pub/v001/s.ma", "v001")
        db.add(r)
        assert len(db.records) == 1

    def test_persistence(self, tmp_path):
        path = str(tmp_path / "pub_db.json")
        db1 = PublishDatabase(path)
        db1.add(PublishRecord("/src/s.ma", "/pub/v001/s.ma", "v001", artist="ada"))
        db2 = PublishDatabase(path)
        assert len(db2.records) == 1


class TestScenePublisher:
    def test_next_version_starts_at_v001(self, tmp_path):
        publisher = ScenePublisher(publish_root=str(tmp_path))
        ver = publisher.next_version("my_asset")
        assert ver == "v001"

    def test_next_version_increments(self, tmp_path):
        publisher = ScenePublisher(publish_root=str(tmp_path))
        (tmp_path / "my_asset" / "v001").mkdir(parents=True)
        ver = publisher.next_version("my_asset")
        assert ver == "v002"

    def test_publish_creates_files(self, tmp_path):
        src = tmp_path / "scene.ma"
        src.write_text("dummy scene")
        publisher = ScenePublisher(publish_root=str(tmp_path / "publish"))
        record = publisher.publish(str(src), asset_name="my_asset", comment="first", artist="ada")
        assert record is not None
        assert record.version == "v001"
