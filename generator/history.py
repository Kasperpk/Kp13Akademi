"""Session history tracking — read/write JSON log."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from models import HistoryEntry

HISTORY_FILE = Path(__file__).parent / "history" / "log.json"


def _serialize(entries: list[HistoryEntry]) -> str:
    return json.dumps(
        [e.model_dump(mode="json") for e in entries],
        indent=2,
        ensure_ascii=False,
    )


def load_history(path: Path = HISTORY_FILE) -> list[HistoryEntry]:
    """Load history entries from JSON file."""
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8-sig").strip()
    if not text or text == "[]":
        return []
    raw = json.loads(text)
    return [HistoryEntry(**entry) for entry in raw]


def save_history(entries: list[HistoryEntry], path: Path = HISTORY_FILE) -> None:
    """Write history entries to JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_serialize(entries), encoding="utf-8")


def append_entry(entry: HistoryEntry, path: Path = HISTORY_FILE) -> None:
    """Append a single entry to the history log."""
    entries = load_history(path)
    entries.append(entry)
    save_history(entries, path)


def last_used_map(path: Path = HISTORY_FILE) -> dict[str, date]:
    """Return a mapping of exercise_id → most recent date used."""
    entries = load_history(path)
    result: dict[str, date] = {}
    for entry in entries:
        for eid in entry.exercise_ids:
            existing = result.get(eid)
            if existing is None or entry.date > existing:
                result[eid] = entry.date
    return result
