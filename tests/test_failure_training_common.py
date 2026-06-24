import json

from local_harness.failure_training.common import read_jsonl, sha256_text, write_jsonl


def test_sha256_text_is_stable():
    assert sha256_text("abc") == sha256_text("abc")
    assert sha256_text("abc") != sha256_text("abcd")


def test_jsonl_round_trip(tmp_path):
    path = tmp_path / "rows.jsonl"
    rows = [{"b": 2, "a": 1}, {"x": "y"}]

    write_jsonl(path, rows)

    assert path.exists()
    loaded = read_jsonl(path)
    assert loaded == rows

    raw_lines = path.read_text(encoding="utf-8").splitlines()
    assert len(raw_lines) == 2
    assert json.loads(raw_lines[0]) == {"a": 1, "b": 2}


def test_read_jsonl_missing_file_returns_empty_list(tmp_path):
    assert read_jsonl(tmp_path / "missing.jsonl") == []
