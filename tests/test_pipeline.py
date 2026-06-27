from datetime import datetime, timedelta, timezone

from src.core import pipeline
from src.core.pipeline import dedupe_and_cap, in_window

from .conftest import make_item

NOW = datetime(2026, 6, 27, 12, 0, tzinfo=timezone.utc)


def test_in_window_keeps_recent_and_undated():
    assert in_window(NOW - timedelta(hours=1), NOW)
    assert in_window(None, NOW)  # undated kept


def test_in_window_drops_old():
    assert not in_window(NOW - timedelta(hours=100), NOW)


def test_in_window_keeps_future_dated():
    assert in_window(NOW + timedelta(hours=10), NOW)


def test_dedupe_drops_already_seen():
    item = make_item("Some tech story", category="tech", item_id="id-1")
    selected = dedupe_and_cap({"tech": [item]}, seen_ids={"id-1"})
    assert selected["tech"] == []


def test_dedupe_collapses_similar_titles_keeps_priority():
    a = make_item("Apple unveils new chip today", category="tech",
                  priority=1, source="A", link="https://a.com/1")
    b = make_item("Apple unveils new chip today", category="tech",
                  priority=3, source="B", link="https://b.com/1")
    selected = dedupe_and_cap({"tech": [a, b]}, seen_ids=set())
    assert len(selected["tech"]) == 1
    assert selected["tech"][0].source == "A"  # lower priority number wins


def test_keyword_filter_applies_to_ai_category():
    relevant = make_item("New LLM beats benchmarks", category="ai")
    noise = make_item("Local bakery opens downtown", category="ai")
    selected = dedupe_and_cap({"ai": [relevant, noise]}, seen_ids=set())
    titles = [it.title for it in selected["ai"]]
    assert "New LLM beats benchmarks" in titles
    assert "Local bakery opens downtown" not in titles


def test_cap_limits_items_per_section(monkeypatch):
    monkeypatch.setitem(pipeline.CATEGORY_CAPS, "tech", 2)
    # Deliberately dissimilar titles so fuzzy de-dupe does not collapse them.
    titles = [
        "Apple unveils foldable iPhone",
        "Google launches quantum processor",
        "Amazon expands warehouse robotics",
        "Microsoft rewrites Windows kernel",
        "Tesla recalls Cybertruck batteries",
    ]
    items = [
        make_item(t, category="tech", link=f"https://x.com/{i}")
        for i, t in enumerate(titles)
    ]
    selected = dedupe_and_cap({"tech": items}, seen_ids=set())
    assert len(selected["tech"]) == 2
