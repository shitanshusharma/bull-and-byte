#!/usr/bin/env python3
"""Bull & Byte - a daily tech + finance news digest for Telegram.

Pipeline: fetch curated RSS -> keep last ~26h -> drop already-sent (seen.json)
-> per-category keyword filter -> cross-source de-dupe -> cap per section
-> render a sectioned HTML digest -> send via the Telegram Bot API
-> record what was sent so it never repeats.

Usage:
  python bot.py                # fetch + send, then update state/seen.json
  python bot.py --dry-run      # print the digest to stdout, send nothing
  python bot.py --dry-run --save-state   # like dry-run but still records seen
                                         # (handy to "prime" state silently)
"""

import argparse
import calendar
import html
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser
import requests

from feeds import (
    CATEGORY_CAPS,
    CATEGORY_KEYWORDS,
    FEEDS,
    SECTIONS,
    USER_AGENT,
)

BASE_DIR = Path(__file__).resolve().parent
SEEN_PATH = BASE_DIR / "state" / "seen.json"


def log(msg):
    print(f"[bull-and-byte] {msg}", flush=True)


def _positive_int_env(name, default):
    """Read a positive int from the env; warn and fall back if unset/invalid."""
    raw = os.environ.get(name, "")
    if not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError:
        log(f"WARN  {name}={raw!r} is not a valid integer; using {default}")
        return default
    if value <= 0:
        log(f"WARN  {name}={value} must be > 0; using {default}")
        return default
    return value


WINDOW_HOURS = _positive_int_env("WINDOW_HOURS", 26)
SEEN_CAP = 1000               # max remembered article ids
DEDUPE_THRESHOLD = 0.6        # title token overlap above this == duplicate
FETCH_TIMEOUT = 25            # seconds per feed
TELEGRAM_LIMIT = 3900         # safety margin under Telegram's 4096 hard cap
IST = timezone(timedelta(hours=5, minutes=30))

_STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "is", "are",
    "as", "at", "by", "with", "from", "this", "that", "be", "it", "its", "after",
    "over", "amid", "says", "say", "will", "new", "how", "why", "what", "vs",
    "into", "out", "up", "down", "his", "her", "you", "your", "we", "amp",
}


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def load_dotenv():
    """Minimal .env loader (no dependency). Only sets vars not already set."""
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def load_seen():
    try:
        data = json.loads(SEEN_PATH.read_text(encoding="utf-8"))
        return list(data.get("sent", []))
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_seen(existing, new_ids):
    combined = list(existing)
    have = set(existing)
    for item_id in new_ids:
        if item_id not in have:
            combined.append(item_id)
            have.add(item_id)
    combined = combined[-SEEN_CAP:]
    SEEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    SEEN_PATH.write_text(
        json.dumps({"sent": combined}, ensure_ascii=False, indent=0) + "\n",
        encoding="utf-8",
    )


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
    return (now - dt) <= timedelta(hours=WINDOW_HOURS)


def title_tokens(text):
    text = re.sub(r"<[^>]+>", " ", text or "").lower()
    raw = re.findall(r"[a-z0-9]+", text)
    return {t for t in raw if len(t) >= 2 and t not in _STOPWORDS}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def matches_keywords(text, keywords):
    text = (text or "").lower()
    for kw in keywords:
        if re.search(r"(?<!\w)" + re.escape(kw) + r"(?!\w)", text):
            return True
    return False


# --------------------------------------------------------------------------- #
# Fetch + assemble
# --------------------------------------------------------------------------- #
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
            {
                "id": (entry.get("id") or link).strip(),
                "link": link,
                "title": title,
                "summary": summary,
                "category": feed["category"],
                "source": feed["name"],
                "priority": feed["priority"],
                "dt": entry_datetime(entry),
                "tokens": title_tokens(title),
            }
        )
    return items


def collect_items(now):
    """Fetch every feed (failures are non-fatal) and keep in-window items."""
    by_category = {cat: [] for cat, _ in SECTIONS}
    for feed in FEEDS:
        try:
            items = fetch_feed(feed)
        except Exception as exc:  # network / parse / status errors are per-feed
            log(f"WARN  {feed['name']} ({feed['category']}): {exc}")
            continue
        kept = [it for it in items if in_window(it["dt"], now)]
        log(f"ok    {feed['name']:<18} {len(kept)}/{len(items)} items in window")
        by_category.setdefault(feed["category"], []).extend(kept)
    return by_category


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
                if matches_keywords(it["title"] + " " + it["summary"], keywords)
            ]

        # 2) drop already-sent (cross-run) and exact-link repeats (this run)
        fresh = []
        for it in items:
            if it["id"] in seen_ids:
                continue
            link_key = it["link"].split("#", 1)[0].rstrip("/").lower()
            if link_key in used_links:
                continue
            used_links.add(link_key)
            fresh.append(it)

        # 3) cross-source fuzzy de-dupe: highest priority / newest wins
        fresh.sort(key=lambda it: (it["priority"], -(it["dt"] or datetime.min.replace(tzinfo=timezone.utc)).timestamp()))
        kept = []
        for it in fresh:
            if any(jaccard(it["tokens"], k["tokens"]) >= DEDUPE_THRESHOLD for k in kept):
                continue
            kept.append(it)

        # 4) newest first, then cap
        kept.sort(key=lambda it: (it["dt"] or datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
        selected[cat] = kept[: CATEGORY_CAPS.get(cat, 6)]
    return selected


# --------------------------------------------------------------------------- #
# Render
# --------------------------------------------------------------------------- #
def _truncate_escaped(raw, room):
    """Longest HTML-escaped prefix of ``raw`` whose length fits in ``room``.

    Truncating the raw string *before* escaping guarantees we never split an
    HTML entity (e.g. ``&amp;``) and emit malformed markup to Telegram.
    """
    if room <= 0:
        return ""
    lo, hi, best = 0, len(raw), ""
    while lo <= hi:
        mid = (lo + hi) // 2
        candidate = html.escape(raw[:mid])
        if len(candidate) <= room:
            best = candidate
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def render_line(it, limit):
    """Render one bullet, guaranteed to be at most ``limit`` characters.

    Normal-length items render in full; a pathologically long title (or link)
    is truncated so a single bullet can never exceed Telegram's hard cap and
    trigger a 400 / partial-send failure.
    """
    # html.unescape first: some feeds (e.g. The Verge) double-encode entities,
    # so decode them before re-escaping for Telegram HTML.
    raw_title = html.unescape(it["title"])
    safe_link = html.escape(it["link"], quote=True)
    safe_source = html.escape(it["source"])
    prefix = f"\u2022 <a href=\"{safe_link}\">"
    suffix = f"</a> <i>({safe_source})</i>"

    full = prefix + html.escape(raw_title) + suffix
    if len(full) <= limit:
        return full

    ellipsis = "\u2026"
    room = limit - len(prefix) - len(suffix) - len(ellipsis)
    truncated = _truncate_escaped(raw_title, room)
    if truncated:
        return prefix + truncated + ellipsis + suffix

    # Link + source alone exceed the budget: drop the link, emit plain text.
    plain_room = limit - len("\u2022 ") - len(ellipsis)
    return "\u2022 " + _truncate_escaped(raw_title, plain_room) + ellipsis


def render_messages(selected, now):
    """Split selected items into one or more <=4096-char HTML messages.

    Returns a list of ``(text, ids)`` pairs, where ``ids`` are the article ids
    whose bullets actually landed in that message. Tracking ids per message
    lets the caller persist only what was truly delivered, so a partial send
    never silently drops the undelivered sections from future digests.
    """
    date_str = now.astimezone(IST).strftime("%d %b %Y")
    title_line = f"<b>Bull &amp; Byte</b> \u2014 daily digest \u00b7 {date_str}"

    total = sum(len(v) for v in selected.values())
    if total == 0:
        return [(f"{title_line}\n\nNo new items in the last {WINDOW_HOURS}h.", [])]

    messages = []
    buf = [title_line]
    buf_ids = []
    length = len(title_line) + 1

    def flush():
        nonlocal buf, buf_ids, length
        if buf:
            messages.append(("\n".join(buf), buf_ids))
        buf = []
        buf_ids = []
        length = 0

    for cat, title in SECTIONS:
        items = selected.get(cat, [])
        if not items:
            continue
        header = f"\n<b>{html.escape(title)}</b>"
        if length + len(header) + 1 > TELEGRAM_LIMIT:
            flush()
        buf.append(header)
        length += len(header) + 1

        for it in items:
            line = render_line(it, TELEGRAM_LIMIT)
            if length + len(line) + 1 > TELEGRAM_LIMIT:
                flush()
                reheader = f"<b>{html.escape(title)} (cont.)</b>"
                buf.append(reheader)
                length += len(reheader) + 1
            buf.append(line)
            buf_ids.append(it["id"])
            length += len(line) + 1

    flush()
    return messages


# --------------------------------------------------------------------------- #
# Telegram delivery (pattern adapted from worldmonitor's notification-relay)
# --------------------------------------------------------------------------- #
def send_telegram(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    for attempt in range(4):
        try:
            resp = requests.post(url, json=payload, timeout=20)
        except requests.RequestException as exc:
            log(f"Telegram request error: {exc}")
            return False

        if resp.status_code == 200:
            return True
        if resp.status_code == 429:
            retry_after = 5
            try:
                retry_after = resp.json().get("parameters", {}).get("retry_after", 5)
            except ValueError:
                pass
            wait = retry_after + 1
            log(f"Telegram 429, waiting {wait}s")
            time.sleep(wait)
            continue
        if resp.status_code in (400, 403):
            log(f"Telegram {resp.status_code}: {resp.text[:200]} - skipping message")
            return False
        if resp.status_code == 401:
            log("Telegram 401 Unauthorized - TELEGRAM_BOT_TOKEN is invalid")
            return False
        log(f"Telegram send failed: {resp.status_code} {resp.text[:200]}")
        return False
    return False


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    parser = argparse.ArgumentParser(description="Bull & Byte Telegram digest")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the digest instead of sending it")
    parser.add_argument("--save-state", action="store_true",
                        help="update seen.json even on a dry run")
    parser.add_argument("--notify-empty", action="store_true",
                        help="send a message even when there are no new items")
    args = parser.parse_args()

    # Make stdout UTF-8 so the --dry-run preview renders dashes/bullets and
    # non-Latin (CJK/emoji) headlines correctly on Windows consoles.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    load_dotenv()
    now = datetime.now(timezone.utc)

    seen = load_seen()
    seen_ids = set(seen)

    by_category = collect_items(now)
    selected = dedupe_and_cap(by_category, seen_ids)

    counts = ", ".join(f"{cat}={len(selected.get(cat, []))}" for cat, _ in SECTIONS)
    log(f"selected: {counts}")

    messages = render_messages(selected, now)
    has_items = any(ids for _text, ids in messages)

    if args.dry_run:
        for i, (text, _ids) in enumerate(messages, 1):
            print(f"\n===== message {i}/{len(messages)} ({len(text)} chars) =====")
            print(text)
        if args.save_state:
            primed = [item_id for _text, ids in messages for item_id in ids]
            if primed:
                save_seen(seen, primed)
                log(f"state updated (dry-run): +{len(primed)} ids")
        return 0

    if not has_items and not args.notify_empty:
        log("no new items in window - nothing to send "
            "(use --notify-empty to send anyway)")
        return 0

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        log("ERROR  TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set "
            "(or use --dry-run).")
        return 1

    delivered_ids = []
    failures = 0
    for text, ids in messages:
        if send_telegram(token, chat_id, text):
            delivered_ids.extend(ids)
        else:
            failures += 1
        time.sleep(1)  # stay well under Telegram rate limits

    log(f"delivered {len(messages) - failures}/{len(messages)} message(s)")

    # Persist only the ids from messages that actually went through, so a
    # partial send never marks undelivered stories as "seen". Save before the
    # failure return below so delivered progress is always recorded.
    if delivered_ids:
        save_seen(seen, delivered_ids)
        log(f"state updated: +{len(delivered_ids)} ids (cap {SEEN_CAP})")

    if failures:
        log(f"WARN  {failures}/{len(messages)} message(s) failed - "
            "their items kept for retry")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
