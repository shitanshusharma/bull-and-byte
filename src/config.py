"""Environment parsing.

All env access is centralized here so the rest of the package depends on plain
Python values rather than scattered ``os.environ`` reads. Literal constants
live in ``constants.py``.
"""

import os

from .constants import BASE_DIR, DEFAULT_GROQ_MODEL, DEFAULT_WINDOW_HOURS
from .utils import log


def positive_int_env(name, default):
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


# Resolved at import so importers always have a value; load_dotenv() re-resolves
# it once .env is read (see its docstring), since .env is loaded after import.
WINDOW_HOURS = positive_int_env("WINDOW_HOURS", DEFAULT_WINDOW_HOURS)


def load_dotenv():
    """Minimal .env loader (no dependency). Only sets vars not already set.

    After loading, re-resolves env-derived module globals (``WINDOW_HOURS``).
    Those are first computed at import time, before ``.env`` is read, so without
    this refresh a value set only in ``.env`` would be silently ignored. Callers
    must run this before the pipeline reads ``WINDOW_HOURS``.
    """
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value

    global WINDOW_HOURS
    WINDOW_HOURS = positive_int_env("WINDOW_HOURS", DEFAULT_WINDOW_HOURS)


def get_chat_ids():
    """Collect Telegram chat ids from TELEGRAM_CHAT_ID and TELEGRAM_CHAT_IDS.

    Both env vars are supported (TELEGRAM_CHAT_ID kept for back-compat); ids may
    be separated by commas or whitespace. Order is preserved and duplicates are
    dropped so the same chat never receives a digest twice.
    """
    raw = " ".join(
        os.environ.get(name, "")
        for name in ("TELEGRAM_CHAT_ID", "TELEGRAM_CHAT_IDS")
    )
    ids = []
    seen = set()
    for token in raw.replace(",", " ").split():
        if token and token not in seen:
            seen.add(token)
            ids.append(token)
    return ids


def ai_summaries_enabled():
    """True when a Groq key is present and the kill-switch is not set to 0."""
    if not os.environ.get("GROQ_API_KEY", "").strip():
        return False
    return os.environ.get("AI_SUMMARIES", "1").strip() not in ("0", "false", "False")


def groq_model():
    return os.environ.get("GROQ_MODEL", "").strip() or DEFAULT_GROQ_MODEL
