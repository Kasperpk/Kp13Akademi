"""Exercise recommender – selects exercises based on EPM gaps and recency."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

# Allow importing the generator package from project root
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT / "generator") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "generator"))

from library import load_exercises, filter_exercises, score_by_recency  # noqa: E402
from history import last_used_map  # noqa: E402
from models import Exercise, Category  # noqa: E402

from .config import EXERCISES_DIR, HISTORY_FILE  # noqa: E402
from .epm import EXERCISE_CATEGORY_TO_EPM, DIM_BY_KEY  # noqa: E402


def _all_exercises() -> list[Exercise]:
    return load_exercises(EXERCISES_DIR)


def _reverse_mapping() -> dict[str, list[str]]:
    """EPM dimension → list of exercise categories that train it."""
    reverse: dict[str, list[str]] = {}
    for cat, dims in EXERCISE_CATEGORY_TO_EPM.items():
        for dim in dims:
            reverse.setdefault(dim, []).append(cat)
    return reverse


def recommend_exercises(
    target_dimensions: list[str],
    *,
    max_results: int = 10,
    age: int | None = 9,
    max_players: int | None = 2,
) -> list[dict[str, Any]]:
    """Return exercises that target the given EPM dimensions, sorted by recency.

    Parameters
    ----------
    target_dimensions : list of EPM dimension keys to address
    max_results : how many exercises to return
    age : filter by age suitability
    max_players : filter by max player count (e.g. 2 for home training)
    """
    reverse = _reverse_mapping()
    all_ex = _all_exercises()
    history = last_used_map(HISTORY_FILE)

    # Find relevant categories
    target_cats: set[str] = set()
    for dim in target_dimensions:
        for cat in reverse.get(dim, []):
            target_cats.add(cat)

    if not target_cats:
        return []

    # Map string categories to enum
    cat_enums = []
    for c in target_cats:
        try:
            cat_enums.append(Category(c))
        except ValueError:
            pass

    # Filter
    filtered = filter_exercises(
        all_ex,
        categories=cat_enums or None,
        age=age,
        min_players_available=max_players,
    )

    # Score by recency (least recently used first)
    scored = score_by_recency(filtered, history)

    # Build result dicts
    results: list[dict[str, Any]] = []
    for ex, days_since in scored[:max_results]:
        # Compute which target dimensions this exercise addresses
        ex_dims = EXERCISE_CATEGORY_TO_EPM.get(ex.category.value, [])
        matching_dims = [d for d in ex_dims if d in target_dimensions]
        video_url = getattr(ex, "video_url", None)
        video_query = f"{ex.name} football drill"
        video_search_url = f"https://www.youtube.com/results?search_query={quote_plus(video_query)}"

        results.append({
            "id": ex.id,
            "name": ex.name,
            "description": ex.description,
            "category": ex.category.value,
            "duration_min": ex.duration_seconds[1] // 60 if ex.duration_seconds else 5,
            "intensity": ex.intensity.value,
            "space": ex.space.value,
            "equipment": ex.equipment,
            "setup": ex.setup,
            "coaching_points": ex.coaching_points,
            "variations": [{"name": v.name, "description": v.description} for v in ex.variations],
            "targets_dimensions": matching_dims,
            "days_since_used": days_since,
            "video_url": video_url,
            "video_search_query": video_query,
            "video_search_url": video_search_url,
        })

    return results


def recommend_for_gaps(
    gaps: list[dict[str, Any]],
    *,
    max_results: int = 10,
    age: int | None = 9,
    max_players: int | None = 2,
) -> list[dict[str, Any]]:
    """Convenience: recommend exercises based on EPM gap analysis."""
    dim_keys = [g["key"] for g in gaps]
    return recommend_exercises(dim_keys, max_results=max_results, age=age, max_players=max_players)
