"""Central place for all literal constants.

Intentionally logic-free: only plain value assignments (no functions, classes,
or conditionals) so the project's tunable knobs are easy to find and maintain.
Anything that reads the environment lives in ``config.py`` instead.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

# --- Paths (repo root is the parent of this package) ---------------------- #
BASE_DIR = Path(__file__).resolve().parent.parent
SEEN_PATH = BASE_DIR / "state" / "seen.json"
LAST_RUN_PATH = BASE_DIR / "state" / "last_run.json"

# --- Pipeline tuning ------------------------------------------------------ #
DEFAULT_WINDOW_HOURS = 26     # default lookback window (overridable via env)
SEEN_CAP = 1000               # max remembered article ids
DEDUPE_THRESHOLD = 0.6        # title token overlap above this == duplicate
FETCH_TIMEOUT = 25            # seconds per feed
MIN_DT = datetime.min.replace(tzinfo=timezone.utc)  # sort sentinel for undated

# --- Telegram delivery ---------------------------------------------------- #
TELEGRAM_LIMIT = 3900         # safety margin under Telegram's 4096 hard cap
TELEGRAM_SEND_TIMEOUT = 20    # seconds per sendMessage request
TELEGRAM_MAX_RETRIES = 4      # attempts per message (handles 429 backoff)

# --- Display -------------------------------------------------------------- #
IST = timezone(timedelta(hours=5, minutes=30))

# Browser-like User-Agent. Several feeds (Moneycontrol, Business Standard,
# The Verge, Engadget, InfoQ) reject default clients, so we always send this.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# --- Groq AI summaries (optional) ----------------------------------------- #
GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"
GROQ_TIMEOUT = 30             # seconds per Groq request
AI_SUMMARY_MAX_CHARS = 140    # one-line summary length cap

# --- Text processing ------------------------------------------------------ #
STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "is", "are",
    "as", "at", "by", "with", "from", "this", "that", "be", "it", "its", "after",
    "over", "amid", "says", "say", "will", "new", "how", "why", "what", "vs",
    "into", "out", "up", "down", "his", "her", "you", "your", "we", "amp",
}
