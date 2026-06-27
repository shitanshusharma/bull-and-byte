"""Turn selected items into one or more Telegram-ready HTML messages."""

import html

from .. import config
from ..constants import IST, TELEGRAM_LIMIT
from ..feeds import SECTIONS


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
    raw_title = html.unescape(it.title)
    safe_link = html.escape(it.link, quote=True)
    safe_source = html.escape(it.source)
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


def render_summary_line(summary_ai, limit):
    """Render the optional AI summary as an indented, escaped sub-line.

    The summary is untrusted model output, so it is always HTML-escaped (via
    the same entity-safe truncation as titles) before being wrapped in markup.
    Returns "" when there is no summary or no room.
    """
    if not summary_ai:
        return ""
    prefix = "    \u21b3 <i>"
    suffix = "</i>"
    room = limit - len(prefix) - len(suffix)
    body = _truncate_escaped(html.unescape(summary_ai), room)
    if not body:
        return ""
    return prefix + body + suffix


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
        return [(f"{title_line}\n\nNo new items in the last {config.WINDOW_HOURS}h.", [])]

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
            sublines = [render_line(it, TELEGRAM_LIMIT)]
            summary_line = render_summary_line(it.summary_ai, TELEGRAM_LIMIT)
            if summary_line:
                sublines.append(summary_line)
            block_len = sum(len(s) + 1 for s in sublines)

            if length + block_len > TELEGRAM_LIMIT:
                flush()
                reheader = f"<b>{html.escape(title)} (cont.)</b>"
                buf.append(reheader)
                length += len(reheader) + 1
            buf.extend(sublines)
            buf_ids.append(it.id)
            length += block_len

    flush()
    return messages
