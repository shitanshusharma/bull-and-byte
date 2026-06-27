"""The normalized article record produced by the fetch stage."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Item:
    """A single normalized article from a feed."""

    id: str
    link: str
    title: str
    summary: str
    category: str
    source: str
    priority: int
    dt: "datetime | None"
    tokens: set
    summary_ai: "str | None" = None
