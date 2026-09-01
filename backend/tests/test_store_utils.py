import pytest
from pathlib import Path
from app.services.store_utils import read_json, write_json, safe_join


def test_write_read_roundtrip(tmp_path):
    p = tmp_path / "sub" / "data.json"
    write_json(p, {"a": 1})
    assert read_json(p) == {"a": 1}


def test_safe_join_rejects_traversal(tmp_path):
    with pytest.raises(ValueError):
        safe_join(tmp_path, "../escape.json")


def test_read_json_missing_returns_none(tmp_path):
    assert read_json(tmp_path / "nope.json") is None
