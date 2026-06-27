from datetime import datetime, timezone

from src.core import render
from src.core.render import render_messages

from .conftest import make_item

NOW = datetime(2026, 6, 27, 12, 0, tzinfo=timezone.utc)


def test_empty_digest_message():
    messages = render_messages({}, NOW)
    assert len(messages) == 1
    text, ids = messages[0]
    assert ids == []
    assert "No new items" in text


def test_basic_sectioning_includes_header_and_link():
    item = make_item("Hello world", category="tech",
                     link="https://example.com/x")
    messages = render_messages({"tech": [item]}, NOW)
    text = messages[0][0]
    assert "<b>Tech</b>" in text
    assert "https://example.com/x" in text
    assert messages[0][1] == [item.id]


def test_summary_line_is_html_escaped():
    item = make_item("Title", category="tech",
                     summary_ai="Tom & Jerry <script>alert(1)</script>")
    text = render_messages({"tech": [item]}, NOW)[0][0]
    assert "<script>" not in text
    assert "&amp;" in text
    assert "&lt;script&gt;" in text


def test_title_special_chars_escaped():
    item = make_item("AT&T <b>wins</b>", category="tech")
    text = render_messages({"tech": [item]}, NOW)[0][0]
    assert "AT&amp;T" in text
    # the literal title markup must not pass through unescaped
    assert "<b>wins</b>" not in text


def test_long_digest_splits_and_preserves_all_ids(monkeypatch):
    monkeypatch.setattr(render, "TELEGRAM_LIMIT", 400)
    items = [
        make_item(f"Headline number {i} about markets and technology today",
                  category="tech", link=f"https://example.com/{i}",
                  item_id=f"id-{i}")
        for i in range(12)
    ]
    messages = render_messages({"tech": items}, NOW)
    assert len(messages) > 1  # forced to split
    for text, _ids in messages:
        assert len(text) <= 400
    delivered = {i for _t, ids in messages for i in ids}
    assert delivered == {f"id-{i}" for i in range(12)}
