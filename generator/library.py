"""Exercise library loader, filtering, and recency-based scoring."""

from __future__ import annotations

import random
from datetime import date
from pathlib import Path
from typing import Optional

import yaml

from models import Category, Exercise, Intensity, SessionTemplate, Space


EXERCISES_DIR = Path(__file__).parent / "exercises"
TEMPLATES_DIR = Path(__file__).parent / "templates"


def load_exercises(directory: Path = EXERCISES_DIR) -> list[Exercise]:
    """Load all exercises from YAML files in *directory*."""
    exercises: list[Exercise] = []
    for path in sorted(directory.glob("*.yaml")):
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data or "exercises" not in data:
            continue
        for entry in data["exercises"]:
            exercises.append(Exercise(**entry))
    return exercises


def load_template(name: str, directory: Path = TEMPLATES_DIR) -> SessionTemplate:
    """Load a session template by filename (without extension)."""
    path = directory / f"{name}.yaml"
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return SessionTemplate(**data)


def list_templates(directory: Path = TEMPLATES_DIR) -> list[str]:
    """Return available template names (without extension)."""
    return [p.stem for p in sorted(directory.glob("*.yaml"))]


# ---------------------------------------------------------------------------
# Filtering helpers
# ---------------------------------------------------------------------------


def filter_exercises(
    exercises: list[Exercise],
    *,
    categories: Optional[list[Category]] = None,
    age: Optional[int] = None,
    max_players: Optional[int] = None,
    min_players_available: Optional[int] = None,
    space_max: Optional[Space] = None,
    intensity: Optional[Intensity] = None,
    require_equipment: Optional[list[str]] = None,
    excluded_ids: Optional[set[str]] = None,
) -> list[Exercise]:
    """Return exercises matching **all** supplied criteria."""
    _space_order = list(Space)

    result: list[Exercise] = []
    for ex in exercises:
        if excluded_ids and ex.id in excluded_ids:
            continue
        if categories and ex.category not in categories:
            continue
        if age is not None:
            if age < ex.age_range[0] or age > ex.age_range[1]:
                continue
        if min_players_available is not None:
            if ex.min_players > min_players_available:
                continue
        if max_players is not None and ex.max_players is not None:
            if max_players > ex.max_players:
                continue
        if space_max is not None:
            if _space_order.index(ex.space) > _space_order.index(space_max):
                continue
        if intensity is not None and ex.intensity != intensity:
            continue
        if require_equipment:
            if not all(item in ex.equipment for item in require_equipment):
                continue
        result.append(ex)
    return result


# ---------------------------------------------------------------------------
# Recency scoring
# ---------------------------------------------------------------------------


def score_by_recency(
    exercises: list[Exercise],
    history_ids: dict[str, date],
    today: Optional[date] = None,
) -> list[tuple[Exercise, int]]:
    """Return exercises sorted by 'days since last used' (descending).

    Exercises never used get the highest score (9999).  Returns a list of
    (exercise, days_since_used) tuples.
    """
    today = today or date.today()
    scored: list[tuple[Exercise, int]] = []
    for ex in exercises:
        last_used = history_ids.get(ex.id)
        if last_used is None:
            scored.append((ex, 9999))
        else:
            scored.append((ex, (today - last_used).days))
    scored.sort(key=lambda t: t[1], reverse=True)
    return scored


def pick_random_weighted(
    exercises: list[Exercise],
    history_ids: dict[str, date],
    count: int = 1,
    today: Optional[date] = None,
) -> list[Exercise]:
    """Pick *count* exercises weighted toward least-recently-used."""
    scored = score_by_recency(exercises, history_ids, today)
    if not scored:
        return []
    weights = [max(s, 1) for _, s in scored]
    pool = [ex for ex, _ in scored]
    count = min(count, len(pool))
    chosen: list[Exercise] = []
    remaining_pool = list(pool)
    remaining_weights = list(weights)
    for _ in range(count):
        if not remaining_pool:
            break
        picks = random.choices(remaining_pool, weights=remaining_weights, k=1)
        pick = picks[0]
        chosen.append(pick)
        idx = remaining_pool.index(pick)
        remaining_pool.pop(idx)
        remaining_weights.pop(idx)
    return chosen
