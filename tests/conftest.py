"""Shared fixtures for the KP13 test suite."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest


@pytest.fixture
def sample_exercises():
    """Build a small set of Exercise instances spanning categories and ages."""
    from models import Category, Exercise, Intensity, Space

    return [
        Exercise(
            id="pass_1",
            name="2-touch passing",
            description="Quick two-touch passing in a diamond.",
            category=Category.PASSING,
            age_range=[7, 12],
            min_players=2,
            max_players=4,
            space=Space.SMALL,
            intensity=Intensity.MODERATE,
            setup="4 cones in a diamond, 6m apart.",
        ),
        Exercise(
            id="rondo_1",
            name="4v1 rondo",
            description="Classic 4v1 possession square.",
            category=Category.RONDO,
            age_range=[8, 18],
            min_players=5,
            max_players=6,
            space=Space.SMALL,
            intensity=Intensity.HIGH,
            setup="6x6m square, 5 players, 1 defender.",
        ),
        Exercise(
            id="mastery_1",
            name="Solo ball mastery",
            description="Inside/outside taps, rolls, stepovers.",
            category=Category.BALL_MASTERY,
            age_range=[6, 14],
            min_players=1,
            max_players=1,
            space=Space.MINIMAL,
            intensity=Intensity.LOW,
            setup="One ball, minimal space.",
        ),
        Exercise(
            id="finish_1",
            name="Finishing after dribble",
            description="1v0 finishing with a dribble entry.",
            category=Category.FINISHING,
            age_range=[10, 18],
            min_players=1,
            max_players=2,
            space=Space.MEDIUM,
            intensity=Intensity.HIGH,
            setup="Goal + 20m approach lane.",
        ),
    ]


@pytest.fixture
def tmp_history_file(tmp_path) -> Path:
    """Create a temporary history log with two entries and return its path."""
    path = tmp_path / "history" / "log.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [
        {
            "date": "2026-04-01",
            "template_name": "solo_30min",
            "exercise_ids": ["mastery_1", "pass_1"],
            "notes": "",
        },
        {
            "date": "2026-04-15",
            "template_name": "solo_30min",
            "exercise_ids": ["mastery_1"],
            "notes": "",
        },
    ]
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


@pytest.fixture
def today_fixed() -> date:
    """A fixed 'today' for deterministic recency math."""
    return date(2026, 4, 23)


@pytest.fixture
def mock_epm_db(monkeypatch):
    """Patch app.core.epm.db with an in-memory score store.

    Returns the backing dict so tests can seed or inspect it.
    """
    from app.core import epm

    store: dict[tuple[str, str], dict] = {}

    def _fake_get_epm_scores(player_id: str) -> dict[str, dict]:
        return {
            dim: dict(entry)
            for (pid, dim), entry in store.items()
            if pid == player_id
        }

    def _fake_set_epm_score(
        player_id: str,
        dimension: str,
        score: float,
        confidence: str = "low",
        observation_count: int = 0,
    ) -> None:
        store[(player_id, dimension)] = {
            "score": score,
            "confidence": confidence,
            "observation_count": observation_count,
            "updated_at": None,
        }

    monkeypatch.setattr(epm.db, "get_epm_scores", _fake_get_epm_scores)
    monkeypatch.setattr(epm.db, "set_epm_score", _fake_set_epm_score)
    return store
