"""Lightweight, ordered schema-migration runner.

Why not Alembic? This codebase persists through raw ``psycopg`` with a hand-written
schema (``core.database._SCHEMA_STATEMENTS``) and no SQLAlchemy models. Alembic's
value (autogeneration from ORM models) doesn't apply here, and it would add a
heavy dependency for little gain. Instead we keep the project's existing idiom —
lists of single SQL statements — and add the one thing it was missing: a record
of *which* changes have already been applied, so changes run exactly once across
environments.

Each migration module under ``core.migrations`` defines ``VERSION`` and
``STATEMENTS`` (see that package's docstring). Applied versions are recorded in
``schema_migrations``. Run with::

    python -m core.migrate          # apply pending migrations (run from app/)
    python -m core.migrate --status # show applied vs pending, apply nothing

Relationship to ``database.init_db()``: ``init_db`` still creates the baseline
tables (idempotent ``CREATE TABLE IF NOT EXISTS``). Migrations layer versioned
*changes* on top. Run ``init_db`` first (or let app startup do it), then migrate.
"""

from __future__ import annotations

import argparse
import importlib
import pkgutil
from datetime import datetime, timezone

from . import database as db
from . import migrations as _migrations_pkg

_TRACKING_TABLE = """CREATE TABLE IF NOT EXISTS schema_migrations (
    version    TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL
)"""


def _discover() -> list:
    """Return migration modules sorted by VERSION ascending."""
    mods = []
    for info in pkgutil.iter_modules(_migrations_pkg.__path__):
        if not info.name.startswith("m"):
            continue
        mod = importlib.import_module(f"{_migrations_pkg.__name__}.{info.name}")
        if not hasattr(mod, "VERSION") or not hasattr(mod, "STATEMENTS"):
            continue
        mods.append(mod)
    mods.sort(key=lambda m: m.VERSION)
    return mods


def _applied_versions() -> set[str]:
    with db.get_db() as conn:
        conn.execute(_TRACKING_TABLE)
        rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
    return {r["version"] for r in rows}


def pending() -> list:
    """Migration modules not yet recorded as applied."""
    done = _applied_versions()
    return [m for m in _discover() if m.VERSION not in done]


def run_migrations() -> list[str]:
    """Apply all pending migrations in order. Returns the versions applied.

    Each migration runs in its own transaction (via ``get_db``): if any statement
    fails, that migration rolls back and is not recorded, so a fix-and-retry is safe.
    """
    applied: list[str] = []
    for mod in pending():
        with db.get_db() as conn:
            for stmt in mod.STATEMENTS:
                conn.execute(stmt)
            conn.execute(
                "INSERT INTO schema_migrations (version, applied_at) VALUES (%s, %s)",
                (mod.VERSION, datetime.now(timezone.utc).isoformat()),
            )
        applied.append(mod.VERSION)
        print(f"applied {mod.VERSION} — {getattr(mod, 'DESCRIPTION', '')}")
    if not applied:
        print("no pending migrations")
    return applied


def _cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m core.migrate")
    parser.add_argument("--status", action="store_true",
                        help="Show applied/pending migrations without applying.")
    args = parser.parse_args(argv)

    if args.status:
        done = _applied_versions()
        for mod in _discover():
            mark = "applied" if mod.VERSION in done else "PENDING"
            print(f"  [{mark}] {mod.VERSION}  {getattr(mod, 'DESCRIPTION', '')}")
        return 0

    run_migrations()
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
