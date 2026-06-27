"""Text tokenization and matching helpers (no third-party deps)."""

import re

from ..constants import STOPWORDS


def title_tokens(text):
    text = re.sub(r"<[^>]+>", " ", text or "").lower()
    raw = re.findall(r"[a-z0-9]+", text)
    return {t for t in raw if len(t) >= 2 and t not in STOPWORDS}


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
