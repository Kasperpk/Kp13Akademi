"""SQLite persistence layer for players, EPM scores, session observations."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Any, Generator

from .config import DB_PATH

# ---- schema ------------------------------------------------------------------

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS players (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    age_group     TEXT,
    position      TEXT,
    club          TEXT,
    dominant_foot TEXT,
    started_date  TEXT,
    parent_name   TEXT,
    notes         TEXT DEFAULT '',
    created_at    TEXT DEFAULT (datetime('now')),
    active        INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS epm_scores (
    player_id         TEXT NOT NULL,
    dimension         TEXT NOT NULL,
    score             REAL NOT NULL DEFAULT 5.0,
    confidence        TEXT DEFAULT 'low',
    observation_count INTEGER DEFAULT 0,
    updated_at        TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (player_id, dimension),
    FOREIGN KEY (player_id) REFERENCES players(id)
);

CREATE TABLE IF NOT EXISTS epm_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id   TEXT NOT NULL,
    dimension   TEXT NOT NULL,
    score       REAL NOT NULL,
    recorded_at TEXT DEFAULT (datetime('now')),
    source      TEXT DEFAULT 'session',
    FOREIGN KEY (player_id) REFERENCES players(id)
);

CREATE TABLE IF NOT EXISTS session_observations (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    date              TEXT NOT NULL,
    player_id         TEXT NOT NULL,
    session_type      TEXT NOT NULL,
    theme             TEXT,
    coach_notes       TEXT,
    extracted_scores  TEXT,
    coach_adjusted    INTEGER DEFAULT 0,
    exercises_used    TEXT,
    transfer_observed INTEGER,
    created_at        TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (player_id) REFERENCES players(id)
);

CREATE TABLE IF NOT EXISTS daily_plans (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date            TEXT NOT NULL,
    player_id       TEXT NOT NULL,
    focus_dimension TEXT,
    plan_content    TEXT,
    completed       INTEGER DEFAULT 0,
    player_feedback TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (player_id) REFERENCES players(id)
);
"""

# ---- connection helpers ------------------------------------------------------


def _ensure_dir() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Yield a connection with row_factory set to sqlite3.Row."""
    _ensure_dir()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create all tables if they don't exist."""
    with get_db() as conn:
        conn.executescript(_SCHEMA)


# ---- players -----------------------------------------------------------------


def upsert_player(
    player_id: str,
    name: str,
    *,
    age_group: str = "",
    position: str = "",
    club: str = "",
    dominant_foot: str = "",
    started_date: str = "",
    parent_name: str = "",
    notes: str = "",
) -> None:
    with get_db() as conn:
        conn.execute(
            """INSERT INTO players (id, name, age_group, position, club,
                                    dominant_foot, started_date, parent_name, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 name=excluded.name, age_group=excluded.age_group,
                 position=excluded.position, club=excluded.club,
                 dominant_foot=excluded.dominant_foot,
                 started_date=excluded.started_date,
                 parent_name=excluded.parent_name,
                 notes=excluded.notes""",
            (player_id, name, age_group, position, club, dominant_foot,
             started_date, parent_name, notes),
        )


def get_players(active_only: bool = True) -> list[dict[str, Any]]:
    with get_db() as conn:
        q = "SELECT * FROM players"
        if active_only:
            q += " WHERE active = 1"
        q += " ORDER BY name"
        return [dict(r) for r in conn.execute(q).fetchall()]


def get_player(player_id: str) -> dict[str, Any] | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM players WHERE id = ?", (player_id,)
        ).fetchone()
        return dict(row) if row else None


# ---- EPM scores --------------------------------------------------------------


def get_epm_scores(player_id: str) -> dict[str, dict[str, Any]]:
    """Return {dimension: {score, confidence, observation_count, updated_at}}."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM epm_scores WHERE player_id = ?", (player_id,)
        ).fetchall()
    return {r["dimension"]: dict(r) for r in rows}


def set_epm_score(
    player_id: str,
    dimension: str,
    score: float,
    confidence: str = "low",
    observation_count: int = 0,
) -> None:
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO epm_scores (player_id, dimension, score, confidence,
                                       observation_count, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(player_id, dimension) DO UPDATE SET
                 score=excluded.score, confidence=excluded.confidence,
                 observation_count=excluded.observation_count,
                 updated_at=excluded.updated_at""",
            (player_id, dimension, score, confidence, observation_count, now),
        )
        # Also record in history
        conn.execute(
            "INSERT INTO epm_history (player_id, dimension, score, source) VALUES (?, ?, ?, 'session')",
            (player_id, dimension, score),
        )


def get_epm_history(
    player_id: str, dimension: str | None = None, limit: int = 100
) -> list[dict[str, Any]]:
    with get_db() as conn:
        if dimension:
            rows = conn.execute(
                """SELECT * FROM epm_history
                   WHERE player_id = ? AND dimension = ?
                   ORDER BY recorded_at DESC LIMIT ?""",
                (player_id, dimension, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT * FROM epm_history
                   WHERE player_id = ?
                   ORDER BY recorded_at DESC LIMIT ?""",
                (player_id, limit),
            ).fetchall()
    return [dict(r) for r in rows]


# ---- session observations ----------------------------------------------------


def save_observation(
    obs_date: str,
    player_id: str,
    session_type: str,
    theme: str,
    coach_notes: str,
    extracted_scores: dict[str, float],
    coach_adjusted: bool = False,
    exercises_used: list[str] | None = None,
    transfer_observed: bool | None = None,
) -> int:
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO session_observations
               (date, player_id, session_type, theme, coach_notes,
                extracted_scores, coach_adjusted, exercises_used, transfer_observed)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                obs_date,
                player_id,
                session_type,
                theme,
                coach_notes,
                json.dumps(extracted_scores),
                1 if coach_adjusted else 0,
                json.dumps(exercises_used or []),
                None if transfer_observed is None else (1 if transfer_observed else 0),
            ),
        )
        return cur.lastrowid  # type: ignore[return-value]


def get_observations(
    player_id: str, limit: int = 50
) -> list[dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute(
            """SELECT * FROM session_observations
               WHERE player_id = ?
               ORDER BY date DESC, created_at DESC
               LIMIT ?""",
            (player_id, limit),
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["extracted_scores"] = json.loads(d["extracted_scores"]) if d["extracted_scores"] else {}
        d["exercises_used"] = json.loads(d["exercises_used"]) if d["exercises_used"] else []
        result.append(d)
    return result


# ---- daily plans -------------------------------------------------------------


def save_daily_plan(
    plan_date: str,
    player_id: str,
    focus_dimension: str,
    plan_content: dict[str, Any],
) -> int:
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO daily_plans (date, player_id, focus_dimension, plan_content)
               VALUES (?, ?, ?, ?)""",
            (plan_date, player_id, focus_dimension, json.dumps(plan_content, ensure_ascii=False)),
        )
        return cur.lastrowid  # type: ignore[return-value]


def get_daily_plan(player_id: str, plan_date: str) -> dict[str, Any] | None:
    with get_db() as conn:
        row = conn.execute(
            """SELECT * FROM daily_plans
               WHERE player_id = ? AND date = ?
               ORDER BY created_at DESC LIMIT 1""",
            (player_id, plan_date),
        ).fetchone()
    if not row:
        return None
    d = dict(row)
    d["plan_content"] = json.loads(d["plan_content"]) if d["plan_content"] else {}
    return d


def mark_plan_completed(plan_id: int, feedback: str = "") -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE daily_plans SET completed = 1, player_feedback = ? WHERE id = ?",
            (feedback, plan_id),
        )
