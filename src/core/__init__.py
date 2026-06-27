"""Core pipeline stages: fetch -> process -> summarize -> render."""

from .fetch import collect_items, fetch_feed
from .pipeline import dedupe_and_cap, entry_datetime, in_window
from .render import render_messages
from .summarize import attach_summaries

__all__ = [
    "collect_items",
    "fetch_feed",
    "dedupe_and_cap",
    "entry_datetime",
    "in_window",
    "render_messages",
    "attach_summaries",
]
