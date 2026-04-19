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
    goals         TEXT DEFAULT '',
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

CREATE TABLE IF NOT EXISTS access_tokens (
    token      TEXT PRIMARY KEY,
    player_id  TEXT,
    role       TEXT NOT NULL DEFAULT 'player',
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (player_id) REFERENCES players(id)
);

CREATE TABLE IF NOT EXISTS weekly_schedules (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id  TEXT NOT NULL,
    week_start TEXT NOT NULL,
    schedule   TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (player_id) REFERENCES players(id),
    UNIQUE(player_id, week_start)
);

CREATE TABLE IF NOT EXISTS session_completions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id    TEXT NOT NULL,
    week_start   TEXT NOT NULL,
    day          TEXT NOT NULL,
    feedback     TEXT DEFAULT '',
    completed_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (player_id) REFERENCES players(id),
    UNIQUE(player_id, week_start, day)
);

CREATE TABLE IF NOT EXISTS ugentlig_planer (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id        TEXT NOT NULL,
    week_start       TEXT NOT NULL,
    content          TEXT NOT NULL,
    sessions_per_week INTEGER DEFAULT 3,
    created_at       TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (player_id) REFERENCES players(id),
    UNIQUE(player_id, week_start)
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
    """Create all tables if they don't exist, and run column migrations."""
    with get_db() as conn:
        conn.executescript(_SCHEMA)
        # Migrations for existing databases
        existing_cols = {
            row[1] for row in conn.execute("PRAGMA table_info(players)").fetchall()
        }
        if "goals" not in existing_cols:
            conn.execute("ALTER TABLE players ADD COLUMN goals TEXT DEFAULT ''")
        plan_cols = {
            row[1] for row in conn.execute("PRAGMA table_info(ugentlig_planer)").fetchall()
        }
        if "sessions_per_week" not in plan_cols:
            conn.execute("ALTER TABLE ugentlig_planer ADD COLUMN sessions_per_week INTEGER DEFAULT 3")


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
    goals: str = "",
) -> None:
    with get_db() as conn:
        conn.execute(
            """INSERT INTO players (id, name, age_group, position, club,
                                    dominant_foot, started_date, parent_name, notes, goals)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 name=excluded.name, age_group=excluded.age_group,
                 position=excluded.position, club=excluded.club,
                 dominant_foot=excluded.dominant_foot,
                 started_date=excluded.started_date,
                 parent_name=excluded.parent_name,
                 notes=excluded.notes""",
            (player_id, name, age_group, position, club, dominant_foot,
             started_date, parent_name, notes, goals),
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


# ---- access tokens -----------------------------------------------------------

import secrets as _secrets


def create_access_token(player_id: str | None = None, role: str = "player") -> str:
    """Generate a short URL-safe token and store it."""
    token = _secrets.token_urlsafe(12)
    with get_db() as conn:
        conn.execute(
            "INSERT INTO access_tokens (token, player_id, role) VALUES (?, ?, ?)",
            (token, player_id, role),
        )
    return token


def verify_access_token(token: str) -> dict[str, Any] | None:
    """Return {player_id, role} if valid, else None."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT player_id, role FROM access_tokens WHERE token = ?", (token,)
        ).fetchone()
    return dict(row) if row else None


def get_player_token(player_id: str) -> str | None:
    """Get existing token for a player, or None."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT token FROM access_tokens WHERE player_id = ? AND role = 'player'",
            (player_id,),
        ).fetchone()
    return row["token"] if row else None


# ---- weekly schedules --------------------------------------------------------


def save_weekly_schedule(
    player_id: str, week_start: str, schedule: dict[str, Any]
) -> None:
    with get_db() as conn:
        conn.execute(
            """INSERT INTO weekly_schedules (player_id, week_start, schedule)
               VALUES (?, ?, ?)
               ON CONFLICT(player_id, week_start) DO UPDATE SET
                 schedule=excluded.schedule""",
            (player_id, week_start, json.dumps(schedule, ensure_ascii=False)),
        )


def get_weekly_schedule(
    player_id: str, week_start: str
) -> dict[str, Any] | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT schedule FROM weekly_schedules WHERE player_id = ? AND week_start = ?",
            (player_id, week_start),
        ).fetchone()
    if not row:
        return None
    return json.loads(row["schedule"])


# ---- session completions -----------------------------------------------------


def mark_session_complete(
    player_id: str, week_start: str, day: str, feedback: str = ""
) -> None:
    with get_db() as conn:
        conn.execute(
            """INSERT INTO session_completions (player_id, week_start, day, feedback)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(player_id, week_start, day) DO UPDATE SET
                 feedback=excluded.feedback""",
            (player_id, week_start, day, feedback),
        )


def get_completions(player_id: str, week_start: str) -> dict[str, str]:
    """Return {day: feedback} for completed sessions this week."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT day, feedback FROM session_completions WHERE player_id = ? AND week_start = ?",
            (player_id, week_start),
        ).fetchall()
    return {r["day"]: r["feedback"] for r in rows}


# ---- player goals ------------------------------------------------------------


def update_player_goals(player_id: str, goals: str) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE players SET goals = ? WHERE id = ?",
            (goals, player_id),
        )


# ---- training hours ----------------------------------------------------------

_SESSION_TYPE_MINUTES = {
    "coached": 60,
    "team": 90,
    "match": 90,
    "home": 30,
}
_DAILY_PLAN_MINUTES = 25


def get_training_hours(player_id: str) -> dict[str, Any]:
    """Return training hour stats: total, this month, this week session count."""
    from datetime import date as _date, timedelta as _timedelta
    today = _date.today()
    month_start = today.replace(day=1).isoformat()
    week_start = (today - _timedelta(days=today.weekday())).isoformat()

    with get_db() as conn:
        obs_rows = conn.execute(
            "SELECT date, session_type FROM session_observations WHERE player_id = ?",
            (player_id,),
        ).fetchall()
        completion_rows = conn.execute(
            "SELECT completed_at FROM session_completions WHERE player_id = ?",
            (player_id,),
        ).fetchall()
        plan_rows = conn.execute(
            "SELECT date FROM daily_plans WHERE player_id = ? AND completed = 1",
            (player_id,),
        ).fetchall()

    total_minutes = 0
    month_minutes = 0
    week_sessions = 0

    for r in obs_rows:
        mins = _SESSION_TYPE_MINUTES.get(r["session_type"], 45)
        total_minutes += mins
        if r["date"] >= month_start:
            month_minutes += mins
        if r["date"] >= week_start:
            week_sessions += 1

    completed_dates = set()
    for r in completion_rows:
        d = r["completed_at"][:10]
        completed_dates.add(d)
    for r in plan_rows:
        completed_dates.add(r["date"])

    for d in completed_dates:
        total_minutes += _DAILY_PLAN_MINUTES
        if d >= month_start:
            month_minutes += _DAILY_PLAN_MINUTES
        if d >= week_start:
            week_sessions += 1

    return {
        "total_hours": round(total_minutes / 60, 1),
        "month_hours": round(month_minutes / 60, 1),
        "week_sessions": week_sessions,
    }


# ---- ugentlig planer (Danish weekly plans) -----------------------------------


def save_ugentlig_plan(player_id: str, week_start: str, content: str, sessions_per_week: int = 3) -> None:
    with get_db() as conn:
        conn.execute(
            """INSERT INTO ugentlig_planer (player_id, week_start, content, sessions_per_week)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(player_id, week_start) DO UPDATE SET
                 content=excluded.content,
                 sessions_per_week=excluded.sessions_per_week,
                 created_at=datetime('now')""",
            (player_id, week_start, content, sessions_per_week),
        )


def get_ugentlig_plan(player_id: str, week_start: str) -> dict[str, Any] | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT content, sessions_per_week FROM ugentlig_planer WHERE player_id = ? AND week_start = ?",
            (player_id, week_start),
        ).fetchone()
    return dict(row) if row else None
