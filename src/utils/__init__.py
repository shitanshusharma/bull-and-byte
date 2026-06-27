"""Generic, dependency-free helpers (logging and text utilities)."""

from .log import log
from .text import jaccard, matches_keywords, title_tokens

__all__ = ["log", "jaccard", "matches_keywords", "title_tokens"]
