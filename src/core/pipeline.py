"""Time-windowing, de-duplication, and per-section capping."""

import calendar
from datetime import datetime, timedelta, timezone

from .. import config
from ..constants import DEDUPE_THRESHOLD, MIN_DT
from ..feeds import CATEGORY_CAPS, CATEGORY_KEYWORDS, SECTIONS
from ..utils import jaccard, matches_keywords


def entry_datetime(entry):
    """Return a tz-aware UTC datetime for an entry, or None if unknown."""
    for key in ("published_parsed", "updated_parsed"):
        struct = entry.get(key)
        if struct:
            return datetime.fromtimestamp(calendar.timegm(struct), tz=timezone.utc)
    return None


def in_window(dt, now):
    if dt is None:
        return True  # undated -> keep, rely on seen.json to avoid repeats
    if dt > now + timedelta(hours=2):
        return True  # clock skew / future-dated, keep
    return (now - dt) <= timedelta(hours=config.WINDOW_HOURS)


def dedupe_and_cap(by_category, seen_ids):
    """Drop seen items, keyword-filter, de-dupe across sources, then cap."""
    selected = {}
    used_links = set()  # exact-link de-dupe across the whole run
    for cat, _ in SECTIONS:
        items = by_category.get(cat, [])

        # 1) keyword relevance filter (only for configured categories)
        keywords = CATEGORY_KEYWORDS.get(cat)
        if keywords:
            items = [
                it for it in items
                if matches_keywords(it.title + " " + it.summary, keywords)
            ]

        # 2) drop already-sent (cross-run) and exact-link repeats (this run)
        fresh = []
        for it in items:
            if it.id in seen_ids:
                continue
            link_key = it.link.split("#", 1)[0].rstrip("/").lower()
            if link_key in used_links:
                continue
            used_links.add(link_key)
            fresh.append(it)

        # 3) cross-source fuzzy de-dupe: highest priority / newest wins
        fresh.sort(key=lambda it: (it.priority, -(it.dt or MIN_DT).timestamp()))
        kept = []
        for it in fresh:
            if any(jaccard(it.tokens, k.tokens) >= DEDUPE_THRESHOLD for k in kept):
                continue
            kept.append(it)

        # 4) newest first, then cap
        kept.sort(key=lambda it: (it.dt or MIN_DT), reverse=True)
        selected[cat] = kept[: CATEGORY_CAPS.get(cat, 6)]
    return selected
