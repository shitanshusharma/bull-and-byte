"""Read/write the on-disk state: seen ids and the last-run summary."""

import json

from ..constants import LAST_RUN_PATH, SEEN_CAP, SEEN_PATH


def load_seen():
    try:
        data = json.loads(SEEN_PATH.read_text(encoding="utf-8"))
        return list(data.get("sent", []))
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_seen(existing, new_ids):
    combined = list(existing)
    have = set(existing)
    for item_id in new_ids:
        if item_id not in have:
            combined.append(item_id)
            have.add(item_id)
    combined = combined[-SEEN_CAP:]
    SEEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    SEEN_PATH.write_text(
        json.dumps({"sent": combined}, ensure_ascii=False, indent=0) + "\n",
        encoding="utf-8",
    )


def write_last_run(stats):
    """Persist a machine-readable summary of the run (never contains secrets)."""
    LAST_RUN_PATH.parent.mkdir(parents=True, exist_ok=True)
    LAST_RUN_PATH.write_text(
        json.dumps(stats.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
