"""Fetch and normalize RSS/Atom feeds into Item objects."""

import feedparser
import requests

from ..constants import FETCH_TIMEOUT, USER_AGENT
from ..feeds import FEEDS, SECTIONS
from ..models import Item
from ..utils import log, title_tokens
from .pipeline import entry_datetime, in_window


def fetch_feed(feed):
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, */*;q=0.8",
    }
    resp = requests.get(feed["url"], headers=headers, timeout=FETCH_TIMEOUT)
    resp.raise_for_status()
    parsed = feedparser.parse(resp.content)
    items = []
    for entry in parsed.entries:
        link = (entry.get("link") or "").strip()
        title = (entry.get("title") or "").strip()
        if not link or not title:
            continue
        summary = entry.get("summary", "") or ""
        items.append(
            Item(
                id=(entry.get("id") or link).strip(),
                link=link,
                title=title,
                summary=summary,
                category=feed["category"],
                source=feed["name"],
                priority=feed["priority"],
                dt=entry_datetime(entry),
                tokens=title_tokens(title),
            )
        )
    return items


def collect_items(now, stats):
    """Fetch every feed (failures are non-fatal) and keep in-window items."""
    by_category = {cat: [] for cat, _ in SECTIONS}
    for feed in FEEDS:
        try:
            items = fetch_feed(feed)
        except Exception as exc:  # network / parse / status errors are per-feed
            log(f"WARN  {feed['name']} ({feed['category']}): {exc}")
            stats.record_feed(feed["name"], feed["category"], 0, 0,
                              ok=False, error=str(exc)[:200])
            continue
        kept = [it for it in items if in_window(it.dt, now)]
        log(f"ok    {feed['name']:<18} {len(kept)}/{len(items)} items in window")
        stats.record_feed(feed["name"], feed["category"], len(kept), len(items))
        by_category.setdefault(feed["category"], []).extend(kept)
    return by_category
