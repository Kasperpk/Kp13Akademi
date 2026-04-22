"""Loader for per-player markdown files under `clients/<player_id>/`.

These files are the canonical narrative source of truth for each player:
  profile.md            — who the player is (identity, dimension anchors, context)
  goals.md              — what they're working toward (current focus, long-term)
  benchmarks.md         — hard numbers over time (append-only test log)
  history.md            — narrative milestones (append-only evidence of progress)
  notes/ongoing.md      — dated qualitative observations (most-recent first read)
  sessions/<date>.md    — full session plans + observation blocks

The DB stores derived state (EPM scores, observation rows, score history). The
markdown stores the why and the prose. Both flows write here when calibrating
a session.
"""

from __future__ import annotations

import re
from datetime import date as _date
from pathlib import Path

CLIENTS_ROOT = Path(__file__).resolve().parents[2] / "clients"

_DATED_HEADING = re.compile(r"^## (\d{4}-\d{2}-\d{2})", re.MULTILINE)
_OBSERVATIONS_HEADING = re.compile(r"^## Observations\s*$", re.MULTILINE)
_NEXT_H2 = re.compile(r"^## ", re.MULTILINE)


def _player_dir(player_id: str) -> Path:
    return CLIENTS_ROOT / player_id


def _load_file(player_id: str, *parts: str) -> str:
    """Read a markdown file under the player's directory, or '' if missing."""
    p = _player_dir(player_id).joinpath(*parts)
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8")


def load_profile(player_id: str) -> str:
    """Return the full text of `clients/<player_id>/profile.md`, or '' if missing."""
    return _load_file(player_id, "profile.md")


def load_goals(player_id: str) -> str:
    """Return the full text of `clients/<player_id>/goals.md`, or '' if missing."""
    return _load_file(player_id, "goals.md")


def load_benchmarks(player_id: str) -> str:
    """Return the full text of `clients/<player_id>/benchmarks.md`, or '' if missing."""
    return _load_file(player_id, "benchmarks.md")


def load_history(player_id: str) -> str:
    """Return the full text of `clients/<player_id>/history.md`, or '' if missing."""
    return _load_file(player_id, "history.md")


def load_ongoing_notes(player_id: str, max_entries: int = 5) -> str:
    """Return the most-recent `max_entries` dated entries from ongoing.md.

    Entries are delimited by `## YYYY-MM-DD ...` headings. Returns them in
    reverse-chronological order joined by the standard markdown separator.
    """
    p = _player_dir(player_id) / "notes" / "ongoing.md"
    if not p.exists():
        return ""
    text = p.read_text(encoding="utf-8")

    matches = list(_DATED_HEADING.finditer(text))
    if not matches:
        return text.strip()

    entries: list[tuple[str, str]] = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].rstrip()
        # strip trailing horizontal rule that often separates entries
        body = re.sub(r"\n---\s*$", "", body)
        entries.append((m.group(1), body))

    entries.sort(key=lambda kv: kv[0], reverse=True)
    return "\n\n---\n\n".join(body for _, body in entries[:max_entries])


def load_recent_session_observations(
    player_id: str, n: int = 3
) -> list[tuple[str, str, str]]:
    """Return the most-recent `n` session markdowns' observation blocks.

    Each tuple is (date_iso, theme_or_filename, observations_text).
    The observations block is the content under a `## Observations` heading,
    or the trailing free text after the structured exercise sections if no
    explicit heading is found. HTML comment placeholders are stripped.
    """
    sessions_dir = _player_dir(player_id) / "sessions"
    if not sessions_dir.exists():
        return []

    files = sorted(sessions_dir.glob("*.md"), key=lambda p: p.name, reverse=True)
    out: list[tuple[str, str, str]] = []
    for f in files[:n]:
        text = f.read_text(encoding="utf-8")
        date_iso = f.stem  # filenames are YYYY-MM-DD.md by convention

        theme = ""
        theme_match = re.search(r"## Session Theme\s*\n+\*\*(.+?)\*\*", text)
        if theme_match:
            theme = theme_match.group(1).strip()

        obs_text = ""
        obs_match = _OBSERVATIONS_HEADING.search(text)
        if obs_match:
            after = text[obs_match.end():]
            next_h2 = _NEXT_H2.search(after)
            block = after[: next_h2.start()] if next_h2 else after
            obs_text = re.sub(r"<!--.*?-->", "", block, flags=re.DOTALL).strip()

        if obs_text:
            out.append((date_iso, theme, obs_text))
    return out


def build_player_context(
    player_id: str,
    max_ongoing: int = 5,
    max_sessions: int = 3,
) -> str:
    """Concatenate profile + ongoing notes + recent session observations.

    Designed to be dropped into an LLM system prompt as the player's full
    narrative context. Returns '' if no markdown material exists.
    """
    parts: list[str] = []
    profile = load_profile(player_id)
    if profile.strip():
        parts.append("=== PLAYER PROFILE (profile.md) ===\n" + profile.strip())

    goals = load_goals(player_id)
    if goals.strip():
        parts.append("=== GOALS & FOCUS (goals.md) ===\n" + goals.strip())

    benchmarks = load_benchmarks(player_id)
    if benchmarks.strip():
        parts.append("=== BENCHMARKS (benchmarks.md) ===\n" + benchmarks.strip())

    history = load_history(player_id)
    if history.strip():
        parts.append("=== PROGRESS HISTORY (history.md) ===\n" + history.strip())

    ongoing = load_ongoing_notes(player_id, max_entries=max_ongoing)
    if ongoing.strip():
        parts.append("=== RECENT COACHING NOTES (notes/ongoing.md) ===\n" + ongoing.strip())

    sessions = load_recent_session_observations(player_id, n=max_sessions)
    if sessions:
        session_blocks = []
        for date_iso, theme, obs in sessions:
            header = f"### Session {date_iso}"
            if theme:
                header += f" — {theme}"
            session_blocks.append(f"{header}\n{obs}")
        parts.append(
            "=== RECENT SESSION OBSERVATIONS (sessions/<date>.md) ===\n"
            + "\n\n".join(session_blocks)
        )

    return "\n\n".join(parts)


def append_to_ongoing(
    player_id: str,
    entry_date: str | _date,
    title: str,
    body: str,
) -> Path:
    """Append a dated entry to `notes/ongoing.md`. Creates the file if needed.

    Returns the path written to.
    """
    if isinstance(entry_date, _date):
        entry_date = entry_date.isoformat()

    notes_dir = _player_dir(player_id) / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    p = notes_dir / "ongoing.md"

    if not p.exists():
        p.write_text(
            "# Coaching Notes\n\n"
            "Running observations about the player. "
            "Add a dated entry after sessions where something notable happened.\n\n"
            "---\n",
            encoding="utf-8",
        )

    existing = p.read_text(encoding="utf-8").rstrip()
    heading = f"## {entry_date} — {title}".rstrip(" —")
    new_block = f"\n\n{heading}\n\n{body.strip()}\n\n---\n"
    p.write_text(existing + new_block, encoding="utf-8")
    return p
