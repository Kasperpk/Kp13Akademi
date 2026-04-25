"""Postgres persistence layer for players, EPM scores, session observations.

Connection info comes from ``DATABASE_URL`` (see ``core.config``). A fresh
schema is created on first run; there are no inline migrations — any schema
change is made by editing ``_SCHEMA`` and re-running against a dev branch.
"""

from __future__ import annotations

import json
import secrets as _secrets
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Generator

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .config import DATABASE_URL

# ---- schema ------------------------------------------------------------------

# ``created_at`` columns are TEXT rather than TIMESTAMP so callers that slice
# the value as an ISO string (e.g. ``r["completed_at"][:10]``) keep working.
_ISO_DEFAULT = "to_char(now() at time zone 'utc', 'YYYY-MM-DD\"T\"HH24:MI:SS')"

_SCHEMA_STATEMENTS = [
    f"""CREATE TABLE IF NOT EXISTS players (
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
        profile_image TEXT DEFAULT '',
        created_at    TEXT DEFAULT ({_ISO_DEFAULT}),
        active        INTEGER DEFAULT 1
    )""",
    """CREATE TABLE IF NOT EXISTS epm_scores (
        player_id         TEXT NOT NULL REFERENCES players(id),
        dimension         TEXT NOT NULL,
        score             REAL NOT NULL DEFAULT 5.0,
        confidence        TEXT DEFAULT 'low',
        observation_count INTEGER DEFAULT 0,
        updated_at        TEXT,
        PRIMARY KEY (player_id, dimension)
    )""",
    f"""CREATE TABLE IF NOT EXISTS epm_history (
        id          SERIAL PRIMARY KEY,
        player_id   TEXT NOT NULL REFERENCES players(id),
        dimension   TEXT NOT NULL,
        score       REAL NOT NULL,
        recorded_at TEXT DEFAULT ({_ISO_DEFAULT}),
        source      TEXT DEFAULT 'session'
    )""",
    f"""CREATE TABLE IF NOT EXISTS session_observations (
        id                SERIAL PRIMARY KEY,
        date              TEXT NOT NULL,
        player_id         TEXT NOT NULL REFERENCES players(id),
        session_type      TEXT NOT NULL,
        theme             TEXT,
        coach_notes       TEXT,
        extracted_scores  TEXT,
        coach_adjusted    INTEGER DEFAULT 0,
        exercises_used    TEXT,
        transfer_observed INTEGER,
        created_at        TEXT DEFAULT ({_ISO_DEFAULT})
    )""",
    f"""CREATE TABLE IF NOT EXISTS daily_plans (
        id              SERIAL PRIMARY KEY,
        date            TEXT NOT NULL,
        player_id       TEXT NOT NULL REFERENCES players(id),
        focus_dimension TEXT,
        plan_content    TEXT,
        completed       INTEGER DEFAULT 0,
        player_feedback TEXT,
        created_at      TEXT DEFAULT ({_ISO_DEFAULT})
    )""",
    f"""CREATE TABLE IF NOT EXISTS access_tokens (
        token      TEXT PRIMARY KEY,
        player_id  TEXT REFERENCES players(id),
        role       TEXT NOT NULL DEFAULT 'player',
        created_at TEXT DEFAULT ({_ISO_DEFAULT})
    )""",
    f"""CREATE TABLE IF NOT EXISTS weekly_schedules (
        id         SERIAL PRIMARY KEY,
        player_id  TEXT NOT NULL REFERENCES players(id),
        week_start TEXT NOT NULL,
        schedule   TEXT NOT NULL,
        created_at TEXT DEFAULT ({_ISO_DEFAULT}),
        UNIQUE (player_id, week_start)
    )""",
    f"""CREATE TABLE IF NOT EXISTS session_completions (
        id           SERIAL PRIMARY KEY,
        player_id    TEXT NOT NULL REFERENCES players(id),
        week_start   TEXT NOT NULL,
        day          TEXT NOT NULL,
        feedback     TEXT DEFAULT '',
        completed_at TEXT DEFAULT ({_ISO_DEFAULT}),
        UNIQUE (player_id, week_start, day)
    )""",
    f"""CREATE TABLE IF NOT EXISTS ugentlig_planer (
        id                SERIAL PRIMARY KEY,
        player_id         TEXT NOT NULL REFERENCES players(id),
        week_start        TEXT NOT NULL,
        content           TEXT NOT NULL,
        sessions_per_week INTEGER DEFAULT 3,
        created_at        TEXT DEFAULT ({_ISO_DEFAULT}),
        UNIQUE (player_id, week_start)
    )""",
    f"""CREATE TABLE IF NOT EXISTS player_sessions (
        id           SERIAL PRIMARY KEY,
        player_id    TEXT NOT NULL REFERENCES players(id),
        week_start   TEXT NOT NULL,
        day          TEXT NOT NULL,
        session_type TEXT NOT NULL,
        time_start   TEXT DEFAULT '',
        notes        TEXT DEFAULT '',
        created_at   TEXT DEFAULT ({_ISO_DEFAULT})
    )""",
    f"""CREATE TABLE IF NOT EXISTS player_videos (
        id          SERIAL PRIMARY KEY,
        player_id   TEXT NOT NULL REFERENCES players(id),
        posted_by   TEXT NOT NULL DEFAULT 'coach',
        video_type  TEXT NOT NULL DEFAULT 'player_training',
        title       TEXT NOT NULL DEFAULT '',
        video_url   TEXT NOT NULL,
        description TEXT DEFAULT '',
        coach_notes TEXT DEFAULT '',
        created_at  TEXT DEFAULT ({_ISO_DEFAULT})
    )""",
    f"""CREATE TABLE IF NOT EXISTS exercise_results (
        id            SERIAL PRIMARY KEY,
        player_id     TEXT NOT NULL REFERENCES players(id),
        week_start    TEXT NOT NULL,
        day           TEXT NOT NULL,
        exercise_id   TEXT NOT NULL,
        exercise_name TEXT NOT NULL,
        target        TEXT,
        result_value  REAL,
        result_unit   TEXT,
        note          TEXT DEFAULT '',
        recorded_at   TEXT DEFAULT ({_ISO_DEFAULT})
    )""",
    f"""CREATE TABLE IF NOT EXISTS player_assessments (
        id                 SERIAL PRIMARY KEY,
        player_id          TEXT NOT NULL REFERENCES players(id),
        assessment_date    TEXT NOT NULL,
        assessment_type    TEXT NOT NULL,
        metrics_json       TEXT DEFAULT '{{}}',
        questionnaire_json TEXT DEFAULT '{{}}',
        suggested_scores   TEXT DEFAULT '{{}}',
        applied_scores     TEXT DEFAULT '{{}}',
        notes              TEXT DEFAULT '',
        created_at         TEXT DEFAULT ({_ISO_DEFAULT})
    )""",
    # Additive migrations (safe to run on existing DBs)
    "ALTER TABLE players ADD COLUMN IF NOT EXISTS preferred_days TEXT DEFAULT NULL",
    "CREATE INDEX IF NOT EXISTS idx_epm_scores_player ON epm_scores(player_id)",
    "CREATE INDEX IF NOT EXISTS idx_epm_history_player_time ON epm_history(player_id, recorded_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_session_obs_player_date ON session_observations(player_id, date DESC)",
    "CREATE INDEX IF NOT EXISTS idx_exercise_results_player_ex ON exercise_results(player_id, exercise_id)",
    "CREATE INDEX IF NOT EXISTS idx_session_completions_player_week ON session_completions(player_id, week_start)",
    "CREATE INDEX IF NOT EXISTS idx_player_assessments_player_date ON player_assessments(player_id, assessment_date DESC)",
]

# ---- connection helpers ------------------------------------------------------


_POOL: ConnectionPool | None = None


def _get_pool() -> ConnectionPool:
    global _POOL
    if _POOL is None:
        if not DATABASE_URL:
            raise RuntimeError(
                "DATABASE_URL is not set. Add it to your .env (local) and "
                "Streamlit Cloud secrets (production)."
            )
        _POOL = ConnectionPool(
            DATABASE_URL,
            min_size=1,
            max_size=5,
            kwargs={"row_factory": dict_row},
            open=True,
        )
    return _POOL


@contextmanager
def get_db() -> Generator[psycopg.Connection, None, None]:
    """Yield a pooled psycopg connection configured to return dict rows."""
    with _get_pool().connection() as conn:
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def init_db() -> None:
    """Create all tables if they don't exist."""
    with get_db() as conn:
        with conn.cursor() as cur:
            for stmt in _SCHEMA_STATEMENTS:
                cur.execute(stmt)


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
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (id) DO UPDATE SET
                 name=EXCLUDED.name, age_group=EXCLUDED.age_group,
                 position=EXCLUDED.position, club=EXCLUDED.club,
                 dominant_foot=EXCLUDED.dominant_foot,
                 started_date=EXCLUDED.started_date,
                 parent_name=EXCLUDED.parent_name,
                 notes=EXCLUDED.notes""",
            (player_id, name, age_group, position, club, dominant_foot,
             started_date, parent_name, notes, goals),
        )


def get_players(active_only: bool = True) -> list[dict[str, Any]]:
    with get_db() as conn:
        q = "SELECT * FROM players"
        if active_only:
            q += " WHERE active = 1"
        q += " ORDER BY name"
        return list(conn.execute(q).fetchall())


def get_player(player_id: str) -> dict[str, Any] | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM players WHERE id = %s", (player_id,)
        ).fetchone()
        return row


_ALL_DAYS = ["Mandag", "Tirsdag", "Onsdag", "Torsdag", "Fredag", "Lørdag", "Søndag"]
_DEFAULT_DAYS_BY_COUNT = {
    2: ["Mandag", "Torsdag"],
    3: ["Mandag", "Onsdag", "Fredag"],
    4: ["Mandag", "Tirsdag", "Torsdag", "Lørdag"],
}


def get_preferred_days(player_id: str, fallback_sessions: int = 3) -> list[str]:
    """Return the player's preferred training days, or a sensible default."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT preferred_days FROM players WHERE id = %s", (player_id,)
        ).fetchone()
    if row and row.get("preferred_days"):
        return [d.strip() for d in row["preferred_days"].split(",") if d.strip()]
    return _DEFAULT_DAYS_BY_COUNT.get(fallback_sessions, _DEFAULT_DAYS_BY_COUNT[3])


def set_preferred_days(player_id: str, days: list[str]) -> None:
    """Persist preferred training days as a comma-separated string."""
    with get_db() as conn:
        conn.execute(
            "UPDATE players SET preferred_days = %s WHERE id = %s",
            (",".join(days), player_id),
        )


# ---- EPM scores --------------------------------------------------------------


def get_epm_scores(player_id: str) -> dict[str, dict[str, Any]]:
    """Return {dimension: {score, confidence, observation_count, updated_at}}."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM epm_scores WHERE player_id = %s", (player_id,)
        ).fetchall()
    return {r["dimension"]: r for r in rows}


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
               VALUES (%s, %s, %s, %s, %s, %s)
               ON CONFLICT (player_id, dimension) DO UPDATE SET
                 score=EXCLUDED.score, confidence=EXCLUDED.confidence,
                 observation_count=EXCLUDED.observation_count,
                 updated_at=EXCLUDED.updated_at""",
            (player_id, dimension, score, confidence, observation_count, now),
        )
        conn.execute(
            "INSERT INTO epm_history (player_id, dimension, score, source) "
            "VALUES (%s, %s, %s, 'session')",
            (player_id, dimension, score),
        )


def get_epm_history(
    player_id: str, dimension: str | None = None, limit: int = 100
) -> list[dict[str, Any]]:
    with get_db() as conn:
        if dimension:
            rows = conn.execute(
                """SELECT * FROM epm_history
                   WHERE player_id = %s AND dimension = %s
                   ORDER BY recorded_at DESC LIMIT %s""",
                (player_id, dimension, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT * FROM epm_history
                   WHERE player_id = %s
                   ORDER BY recorded_at DESC LIMIT %s""",
                (player_id, limit),
            ).fetchall()
    return list(rows)


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
        row = conn.execute(
            """INSERT INTO session_observations
               (date, player_id, session_type, theme, coach_notes,
                extracted_scores, coach_adjusted, exercises_used, transfer_observed)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
               RETURNING id""",
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
        ).fetchone()
        return row["id"]


def get_observations(
    player_id: str, limit: int = 50
) -> list[dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute(
            """SELECT * FROM session_observations
               WHERE player_id = %s
               ORDER BY date DESC, created_at DESC
               LIMIT %s""",
            (player_id, limit),
        ).fetchall()
    result = []
    for r in rows:
        r["extracted_scores"] = json.loads(r["extracted_scores"]) if r["extracted_scores"] else {}
        r["exercises_used"] = json.loads(r["exercises_used"]) if r["exercises_used"] else []
        result.append(r)
    return result


# ---- daily plans -------------------------------------------------------------


def save_daily_plan(
    plan_date: str,
    player_id: str,
    focus_dimension: str,
    plan_content: dict[str, Any],
) -> int:
    with get_db() as conn:
        row = conn.execute(
            """INSERT INTO daily_plans (date, player_id, focus_dimension, plan_content)
               VALUES (%s, %s, %s, %s)
               RETURNING id""",
            (plan_date, player_id, focus_dimension, json.dumps(plan_content, ensure_ascii=False)),
        ).fetchone()
        return row["id"]


def get_daily_plan(player_id: str, plan_date: str) -> dict[str, Any] | None:
    with get_db() as conn:
        row = conn.execute(
            """SELECT * FROM daily_plans
               WHERE player_id = %s AND date = %s
               ORDER BY created_at DESC LIMIT 1""",
            (player_id, plan_date),
        ).fetchone()
    if not row:
        return None
    row["plan_content"] = json.loads(row["plan_content"]) if row["plan_content"] else {}
    return row


def mark_plan_completed(plan_id: int, feedback: str = "") -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE daily_plans SET completed = 1, player_feedback = %s WHERE id = %s",
            (feedback, plan_id),
        )


# ---- access tokens -----------------------------------------------------------


def create_access_token(player_id: str | None = None, role: str = "player") -> str:
    """Generate a short URL-safe token and store it."""
    token = _secrets.token_urlsafe(12)
    with get_db() as conn:
        conn.execute(
            "INSERT INTO access_tokens (token, player_id, role) VALUES (%s, %s, %s)",
            (token, player_id, role),
        )
    return token


def verify_access_token(token: str) -> dict[str, Any] | None:
    """Return {player_id, role} if valid, else None."""
    with get_db() as conn:
        return conn.execute(
            "SELECT player_id, role FROM access_tokens WHERE token = %s", (token,)
        ).fetchone()


def get_player_token(player_id: str) -> str | None:
    """Get existing token for a player, or None."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT token FROM access_tokens WHERE player_id = %s AND role = 'player'",
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
               VALUES (%s, %s, %s)
               ON CONFLICT (player_id, week_start) DO UPDATE SET
                 schedule=EXCLUDED.schedule""",
            (player_id, week_start, json.dumps(schedule, ensure_ascii=False)),
        )


def get_weekly_schedule(
    player_id: str, week_start: str
) -> dict[str, Any] | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT schedule FROM weekly_schedules WHERE player_id = %s AND week_start = %s",
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
               VALUES (%s, %s, %s, %s)
               ON CONFLICT (player_id, week_start, day) DO UPDATE SET
                 feedback=EXCLUDED.feedback""",
            (player_id, week_start, day, feedback),
        )


def get_completions(player_id: str, week_start: str) -> dict[str, str]:
    """Return {day: feedback} for completed sessions this week."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT day, feedback FROM session_completions WHERE player_id = %s AND week_start = %s",
            (player_id, week_start),
        ).fetchall()
    return {r["day"]: r["feedback"] for r in rows}


# ---- player goals ------------------------------------------------------------


def update_player_goals(player_id: str, goals: str) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE players SET goals = %s WHERE id = %s",
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
            "SELECT date, session_type FROM session_observations WHERE player_id = %s",
            (player_id,),
        ).fetchall()
        completion_rows = conn.execute(
            "SELECT completed_at FROM session_completions WHERE player_id = %s",
            (player_id,),
        ).fetchall()
        plan_rows = conn.execute(
            "SELECT date FROM daily_plans WHERE player_id = %s AND completed = 1",
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
            f"""INSERT INTO ugentlig_planer (player_id, week_start, content, sessions_per_week)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (player_id, week_start) DO UPDATE SET
                  content=EXCLUDED.content,
                  sessions_per_week=EXCLUDED.sessions_per_week,
                  created_at={_ISO_DEFAULT}""",
            (player_id, week_start, content, sessions_per_week),
        )


def get_ugentlig_plan(player_id: str, week_start: str) -> dict[str, Any] | None:
    with get_db() as conn:
        return conn.execute(
            "SELECT content, sessions_per_week FROM ugentlig_planer WHERE player_id = %s AND week_start = %s",
            (player_id, week_start),
        ).fetchone()


# ---- player-added sessions ---------------------------------------------------


def add_player_session(
    player_id: str,
    week_start: str,
    day: str,
    session_type: str,
    time_start: str = "",
    notes: str = "",
) -> None:
    with get_db() as conn:
        conn.execute(
            """INSERT INTO player_sessions
               (player_id, week_start, day, session_type, time_start, notes)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (player_id, week_start, day, session_type, time_start, notes),
        )


def get_player_sessions(player_id: str, week_start: str) -> dict[str, list[dict[str, Any]]]:
    """Return {day: [session, ...]} for the given week."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT * FROM player_sessions
               WHERE player_id = %s AND week_start = %s
               ORDER BY time_start""",
            (player_id, week_start),
        ).fetchall()
    result: dict[str, list] = {}
    for r in rows:
        result.setdefault(r["day"], []).append(r)
    return result


def delete_player_session(session_id: int) -> None:
    with get_db() as conn:
        conn.execute("DELETE FROM player_sessions WHERE id = %s", (session_id,))


# ---- profile image -----------------------------------------------------------


def update_player_image(player_id: str, image_b64: str) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE players SET profile_image = %s WHERE id = %s",
            (image_b64, player_id),
        )


def get_player_image(player_id: str) -> str:
    """Return base64-encoded image string, or '' if none."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT profile_image FROM players WHERE id = %s", (player_id,)
        ).fetchone()
    return row["profile_image"] if row and row["profile_image"] else ""


# ---- video wall --------------------------------------------------------------


def add_video(
    player_id: str,
    title: str,
    video_url: str,
    posted_by: str = "coach",
    video_type: str = "player_training",
    description: str = "",
) -> int:
    with get_db() as conn:
        row = conn.execute(
            """INSERT INTO player_videos
               (player_id, posted_by, video_type, title, video_url, description)
               VALUES (%s, %s, %s, %s, %s, %s)
               RETURNING id""",
            (player_id, posted_by, video_type, title, video_url, description),
        ).fetchone()
        return row["id"]


def get_videos(player_id: str) -> list[dict[str, Any]]:
    with get_db() as conn:
        return list(conn.execute(
            "SELECT * FROM player_videos WHERE player_id = %s ORDER BY created_at DESC",
            (player_id,),
        ).fetchall())


def update_video_coach_notes(video_id: int, coach_notes: str) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE player_videos SET coach_notes = %s WHERE id = %s",
            (coach_notes, video_id),
        )


def delete_video(video_id: int) -> None:
    with get_db() as conn:
        conn.execute("DELETE FROM player_videos WHERE id = %s", (video_id,))


# ---- exercise results --------------------------------------------------------


def save_exercise_result(
    player_id: str,
    week_start: str,
    day: str,
    exercise_id: str,
    exercise_name: str,
    target: str | None,
    result_value: float,
    result_unit: str = "",
    note: str = "",
) -> int:
    with get_db() as conn:
        row = conn.execute(
            """INSERT INTO exercise_results
               (player_id, week_start, day, exercise_id, exercise_name,
                target, result_value, result_unit, note)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
               RETURNING id""",
            (player_id, week_start, day, exercise_id, exercise_name,
             target, result_value, result_unit, note),
        ).fetchone()
        return row["id"]


def get_recent_results(
    player_id: str,
    exercise_ids: list[str] | None = None,
    limit_per_exercise: int = 1,
) -> dict[str, list[dict[str, Any]]]:
    """Return the last N results per exercise_id for a player.

    If exercise_ids is None or empty, return the player's most recent results
    across all exercises (still grouped by exercise_id).
    """
    with get_db() as conn:
        if exercise_ids:
            rows = conn.execute(
                """SELECT * FROM (
                       SELECT *, ROW_NUMBER() OVER (
                           PARTITION BY exercise_id ORDER BY recorded_at DESC
                       ) AS rn
                       FROM exercise_results
                       WHERE player_id = %s AND exercise_id = ANY(%s)
                   ) t
                   WHERE rn <= %s
                   ORDER BY exercise_id, recorded_at DESC""",
                (player_id, exercise_ids, limit_per_exercise),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT * FROM (
                       SELECT *, ROW_NUMBER() OVER (
                           PARTITION BY exercise_id ORDER BY recorded_at DESC
                       ) AS rn
                       FROM exercise_results
                       WHERE player_id = %s
                   ) t
                   WHERE rn <= %s
                   ORDER BY exercise_id, recorded_at DESC""",
                (player_id, limit_per_exercise),
            ).fetchall()
    grouped: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        r.pop("rn", None)
        grouped.setdefault(r["exercise_id"], []).append(r)
    return grouped


# ---- player assessments ------------------------------------------------------


def save_player_assessment(
    player_id: str,
    assessment_date: str,
    assessment_type: str,
    metrics: dict[str, float] | None = None,
    questionnaire: dict[str, str] | None = None,
    suggested_scores: dict[str, float] | None = None,
    applied_scores: dict[str, float] | None = None,
    notes: str = "",
) -> int:
    with get_db() as conn:
        row = conn.execute(
            """INSERT INTO player_assessments
               (player_id, assessment_date, assessment_type, metrics_json,
                questionnaire_json, suggested_scores, applied_scores, notes)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
               RETURNING id""",
            (
                player_id,
                assessment_date,
                assessment_type,
                json.dumps(metrics or {}, ensure_ascii=False),
                json.dumps(questionnaire or {}, ensure_ascii=False),
                json.dumps(suggested_scores or {}, ensure_ascii=False),
                json.dumps(applied_scores or {}, ensure_ascii=False),
                notes,
            ),
        ).fetchone()
        return row["id"]


def get_player_assessments(player_id: str, limit: int = 20) -> list[dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute(
            """SELECT * FROM player_assessments
               WHERE player_id = %s
               ORDER BY assessment_date DESC, created_at DESC
               LIMIT %s""",
            (player_id, limit),
        ).fetchall()

    out: list[dict[str, Any]] = []
    for r in rows:
        r["metrics_json"] = json.loads(r["metrics_json"]) if r["metrics_json"] else {}
        r["questionnaire_json"] = json.loads(r["questionnaire_json"]) if r["questionnaire_json"] else {}
        r["suggested_scores"] = json.loads(r["suggested_scores"]) if r["suggested_scores"] else {}
        r["applied_scores"] = json.loads(r["applied_scores"]) if r["applied_scores"] else {}
        out.append(r)
    return out
