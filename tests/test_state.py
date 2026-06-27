import json

from src.delivery import state


def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    path = tmp_path / "seen.json"
    monkeypatch.setattr(state, "SEEN_PATH", path)
    state.save_seen([], ["a", "b"])
    assert state.load_seen() == ["a", "b"]


def test_save_seen_dedupes_and_appends(tmp_path, monkeypatch):
    path = tmp_path / "seen.json"
    monkeypatch.setattr(state, "SEEN_PATH", path)
    state.save_seen(["a"], ["a", "b", "c"])
    assert state.load_seen() == ["a", "b", "c"]


def test_save_seen_respects_cap(tmp_path, monkeypatch):
    path = tmp_path / "seen.json"
    monkeypatch.setattr(state, "SEEN_PATH", path)
    monkeypatch.setattr(state, "SEEN_CAP", 3)
    state.save_seen(["a", "b", "c"], ["d", "e"])
    # Only the most recent 3 ids survive.
    assert state.load_seen() == ["c", "d", "e"]


def test_load_seen_missing_file_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "SEEN_PATH", tmp_path / "nope.json")
    assert state.load_seen() == []


def test_write_last_run(tmp_path, monkeypatch):
    from src.models import RunStats

    path = tmp_path / "last_run.json"
    monkeypatch.setattr(state, "LAST_RUN_PATH", path)
    stats = RunStats()
    stats.record_feed("CNBC", "finance_global", 5, 10)
    stats.selected_counts = {"tech": 3}
    state.write_last_run(stats)

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["feeds_ok"] == 1
    assert data["selected_counts"] == {"tech": 3}
