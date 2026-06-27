#!/usr/bin/env python3
"""Bull & Byte - a daily tech + finance news digest for Telegram.

Pipeline: fetch curated RSS -> keep last ~26h -> drop already-sent (seen.json)
-> per-category keyword filter -> cross-source de-dupe -> cap per section
-> optional Groq one-line summaries -> render a sectioned HTML digest
-> fan out via the Telegram Bot API -> record what was sent so it never repeats.

Usage:
  python bot.py                # fetch + send, then update state/seen.json
  python bot.py --dry-run      # print the digest to stdout, send nothing
  python bot.py --dry-run --save-state   # like dry-run but still records seen
  python bot.py --notify-empty           # send even when there are no new items
"""

import argparse
import os
import sys
import time
from datetime import datetime, timezone

from . import config
from .constants import SEEN_CAP
from .core import attach_summaries, collect_items, dedupe_and_cap, render_messages
from .delivery import load_seen, save_seen, send_all, write_last_run
from .feeds import SECTIONS
from .models import RunStats
from .utils import log


def _emit_step_summary(stats):
    """Write a human-readable run summary to the Actions step summary or stdout."""
    d = stats.to_dict()
    lines = [
        "## Bull & Byte run summary",
        "",
        f"- Duration: {d['duration_sec']}s",
        f"- Feeds: {d['feeds_ok']} ok, {d['feeds_failed']} failed",
        f"- AI summaries: {d['ai_note']}",
        f"- Messages built: {d['messages_built']}, failures: {d['failures']}",
        "",
        "| Section | Selected |",
        "| --- | --- |",
    ]
    for cat, title in SECTIONS:
        lines.append(f"| {title} | {d['selected_counts'].get(cat, 0)} |")
    if d["delivered_per_chat"]:
        lines += ["", "| Chat | Messages delivered |", "| --- | --- |"]
        for chat_id, count in d["delivered_per_chat"].items():
            lines.append(f"| {chat_id} | {count} |")
    if d["feeds_failed"]:
        lines += ["", "Failed feeds: " + ", ".join(
            f["name"] for f in d["feeds"] if not f["ok"])]
    text = "\n".join(lines) + "\n"

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        try:
            with open(summary_path, "a", encoding="utf-8") as fh:
                fh.write(text)
            return
        except OSError as exc:
            log(f"WARN  could not write step summary: {exc}")
    print(text)


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

    config.load_dotenv()
    start = time.monotonic()
    now = datetime.now(timezone.utc)

    stats = RunStats(started_at=now)

    seen = load_seen()
    seen_ids = set(seen)

    by_category = collect_items(now, stats)
    selected = dedupe_and_cap(by_category, seen_ids)
    attach_summaries(selected, stats)

    stats.selected_counts = {cat: len(selected.get(cat, [])) for cat, _ in SECTIONS}
    counts = ", ".join(f"{cat}={n}" for cat, n in stats.selected_counts.items())
    log(f"selected: {counts}")

    messages = render_messages(selected, now)
    stats.messages_built = len(messages)
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
        stats.duration_sec = time.monotonic() - start
        write_last_run(stats)
        _emit_step_summary(stats)
        return 0

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_ids = config.get_chat_ids()
    if not token or not chat_ids:
        log("ERROR  TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID/TELEGRAM_CHAT_IDS "
            "must be set (or use --dry-run).")
        return 1

    delivered_ids, failures, delivered_per_chat = send_all(token, chat_ids, messages)
    stats.failures = failures
    stats.delivered_per_chat = delivered_per_chat

    log(f"delivered to {len(chat_ids)} chat(s): " + ", ".join(
        f"{cid}={n}" for cid, n in delivered_per_chat.items()))

    # Persist only the ids from messages that reached at least one chat, so a
    # partial send never marks undelivered stories as "seen". Save before the
    # failure return below so delivered progress is always recorded.
    if delivered_ids:
        save_seen(seen, delivered_ids)
        log(f"state updated: +{len(delivered_ids)} ids (cap {SEEN_CAP})")

    stats.duration_sec = time.monotonic() - start
    write_last_run(stats)
    _emit_step_summary(stats)

    if failures:
        log(f"WARN  {failures} send(s) failed - their items kept for retry")
        return 1
    return 0
