"""Telegram delivery (pattern adapted from worldmonitor's notification-relay)."""

import time

import requests

from ..constants import TELEGRAM_MAX_RETRIES, TELEGRAM_SEND_TIMEOUT
from ..utils import log


def send_telegram(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    for _attempt in range(TELEGRAM_MAX_RETRIES):
        try:
            resp = requests.post(url, json=payload, timeout=TELEGRAM_SEND_TIMEOUT)
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


def send_all(token, chat_ids, messages):
    """Send every message to every chat id (same digest fanned out to all).

    A story id is treated as delivered if its message reached at least one
    chat, because seen.json is shared across chats - "at least one" prevents
    endless resends while a failed chat simply misses that story.

    Returns ``(delivered_ids, failures, delivered_per_chat)``:
      - delivered_ids: ids from messages that reached >=1 chat (deduped)
      - failures: count of (message, chat) sends that failed
      - delivered_per_chat: {chat_id: messages_delivered}
    """
    delivered_ids = []
    seen_ids = set()
    failures = 0
    delivered_per_chat = {cid: 0 for cid in chat_ids}

    for text, ids in messages:
        reached_any = False
        for chat_id in chat_ids:
            if send_telegram(token, chat_id, text):
                reached_any = True
                delivered_per_chat[chat_id] += 1
            else:
                failures += 1
            time.sleep(1)  # stay well under Telegram rate limits
        if reached_any:
            for item_id in ids:
                if item_id not in seen_ids:
                    seen_ids.add(item_id)
                    delivered_ids.append(item_id)

    return delivered_ids, failures, delivered_per_chat
