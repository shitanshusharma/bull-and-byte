"""Optional one-line AI summaries via Groq's OpenAI-compatible API.

This module is strictly best-effort: it runs only when GROQ_API_KEY is set and
the AI_SUMMARIES kill-switch is not 0. Any missing key, network error, timeout,
or unparseable response is swallowed so the digest still renders without
summaries (keeping the "no API keys beyond Telegram" default true).
"""

import json
import os
import re

import requests

from ..config import ai_summaries_enabled, groq_model
from ..constants import AI_SUMMARY_MAX_CHARS, GROQ_ENDPOINT, GROQ_TIMEOUT
from ..utils import log

_TAG_RE = re.compile(r"<[^>]+>")


def _plain(text, limit=300):
    text = _TAG_RE.sub(" ", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def _build_prompt(items):
    lines = []
    for idx, it in enumerate(items):
        snippet = _plain(it.summary)
        entry = f"{idx}. {it.title}"
        if snippet:
            entry += f" - {snippet}"
        lines.append(entry)
    return "\n".join(lines)


def _parse_summaries(content):
    """Extract a {index: summary} JSON object from the model response."""
    content = content.strip()
    start, end = content.find("{"), content.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("no JSON object in response")
    return json.loads(content[start:end + 1])


def _request_summaries(items):
    prompt = (
        "You are a concise financial/tech news editor. For each numbered "
        "headline below, write a single plain-text sentence (max 20 words, no "
        "markdown, no quotes) capturing why it matters. Respond with ONLY a "
        "JSON object mapping each number (as a string) to its sentence.\n\n"
        + _build_prompt(items)
    )
    payload = {
        "model": groq_model(),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {os.environ['GROQ_API_KEY']}",
        "Content-Type": "application/json",
    }
    resp = requests.post(GROQ_ENDPOINT, json=payload, headers=headers,
                         timeout=GROQ_TIMEOUT)
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    return _parse_summaries(content)


def attach_summaries(selected, stats):
    """Attach a one-line ``summary_ai`` to each selected item, in place.

    Updates ``stats`` with whether AI was enabled, how many items were
    summarized, and a short note when it was skipped or failed.
    """
    if not ai_summaries_enabled():
        stats.ai_enabled = False
        stats.ai_note = "disabled (no GROQ_API_KEY or AI_SUMMARIES=0)"
        return

    stats.ai_enabled = True
    items = [it for cat_items in selected.values() for it in cat_items]
    if not items:
        stats.ai_note = "no items to summarize"
        return

    try:
        mapping = _request_summaries(items)
    except Exception as exc:  # network / status / parse - all non-fatal
        log(f"WARN  AI summaries skipped: {exc}")
        stats.ai_note = f"error: {str(exc)[:120]}"
        return

    count = 0
    for idx, it in enumerate(items):
        summary = mapping.get(str(idx)) or mapping.get(idx)
        if isinstance(summary, str) and summary.strip():
            it.summary_ai = summary.strip()[:AI_SUMMARY_MAX_CHARS]
            count += 1

    stats.ai_summarized = count
    stats.ai_note = f"summarized {count}/{len(items)}"
    log(f"AI summaries: {count}/{len(items)} items")
