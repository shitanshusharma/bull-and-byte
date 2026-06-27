import pytest

from src.core import summarize
from src.models import RunStats

from .conftest import make_item


def test_parse_summaries_extracts_embedded_json():
    content = 'Sure! {"0": "First.", "1": "Second."} done'
    assert summarize._parse_summaries(content) == {"0": "First.", "1": "Second."}


def test_parse_summaries_raises_without_json():
    with pytest.raises(ValueError):
        summarize._parse_summaries("no json here")


def test_attach_summaries_disabled_is_noop(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    stats = RunStats()
    selected = {"tech": [make_item("Title")]}
    summarize.attach_summaries(selected, stats)
    assert stats.ai_enabled is False
    assert selected["tech"][0].summary_ai is None


def test_attach_summaries_applies_and_truncates(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "secret")
    monkeypatch.setenv("AI_SUMMARIES", "1")
    long_summary = "x" * 500
    monkeypatch.setattr(summarize, "_request_summaries",
                        lambda items: {"0": long_summary})
    stats = RunStats()
    item = make_item("Title")
    summarize.attach_summaries({"tech": [item]}, stats)
    assert stats.ai_enabled is True
    assert stats.ai_summarized == 1
    assert len(item.summary_ai) == summarize.AI_SUMMARY_MAX_CHARS


def test_attach_summaries_swallows_errors(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "secret")
    monkeypatch.setenv("AI_SUMMARIES", "1")

    def boom(_items):
        raise RuntimeError("api down")

    monkeypatch.setattr(summarize, "_request_summaries", boom)
    stats = RunStats()
    item = make_item("Title")
    summarize.attach_summaries({"tech": [item]}, stats)
    assert item.summary_ai is None
    assert "error" in stats.ai_note
