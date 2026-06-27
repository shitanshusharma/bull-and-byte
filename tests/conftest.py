"""Shared test helpers."""

from datetime import datetime, timezone

from src.models import Item
from src.utils import title_tokens


def make_item(title, *, category="tech", source="Src", priority=1,
              link=None, summary="", dt=None, item_id=None, summary_ai=None):
    """Build an Item with sensible defaults for tests."""
    link = link or f"https://example.com/{abs(hash(title)) % 10000}"
    return Item(
        id=item_id or link,
        link=link,
        title=title,
        summary=summary,
        category=category,
        source=source,
        priority=priority,
        dt=dt or datetime(2026, 6, 27, tzinfo=timezone.utc),
        tokens=title_tokens(title),
        summary_ai=summary_ai,
    )
