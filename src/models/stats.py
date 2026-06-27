"""Run-level statistics, serialized to state/last_run.json and the CI summary."""

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class FeedResult:
    """Per-feed fetch outcome, recorded for the run summary."""

    name: str
    category: str
    kept: int = 0
    total: int = 0
    ok: bool = True
    error: str = ""


@dataclass
class RunStats:
    """Accumulates everything worth reporting about a single run."""

    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    feeds: list = field(default_factory=list)
    selected_counts: dict = field(default_factory=dict)
    ai_enabled: bool = False
    ai_summarized: int = 0
    ai_note: str = ""
    messages_built: int = 0
    delivered_per_chat: dict = field(default_factory=dict)
    failures: int = 0
    duration_sec: float = 0.0

    def record_feed(self, name, category, kept, total, ok=True, error=""):
        self.feeds.append(
            FeedResult(name=name, category=category, kept=kept, total=total,
                       ok=ok, error=error)
        )

    @property
    def feeds_ok(self):
        return sum(1 for f in self.feeds if f.ok)

    @property
    def feeds_failed(self):
        return sum(1 for f in self.feeds if not f.ok)

    def to_dict(self):
        return {
            "started_at": self.started_at.isoformat(),
            "duration_sec": round(self.duration_sec, 2),
            "feeds_ok": self.feeds_ok,
            "feeds_failed": self.feeds_failed,
            "feeds": [
                {
                    "name": f.name,
                    "category": f.category,
                    "kept": f.kept,
                    "total": f.total,
                    "ok": f.ok,
                    "error": f.error,
                }
                for f in self.feeds
            ],
            "selected_counts": self.selected_counts,
            "ai_enabled": self.ai_enabled,
            "ai_summarized": self.ai_summarized,
            "ai_note": self.ai_note,
            "messages_built": self.messages_built,
            "delivered_per_chat": self.delivered_per_chat,
            "failures": self.failures,
        }
