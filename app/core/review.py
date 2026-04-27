"""Shared rubric-presentation helpers.

Used by:
- The coach-led 10-week review (`app/pages/7_10_uger_review.py`)
- The player-facing "Mastery levels" page (`/p/{token}/mastery`) — generic, no personal scores
- The Streamlit "Min Udvikling" page when surfacing the rubric ladder

The rubric content itself lives in `app.core.rubrics`. This module is purely
about how scores map to rubric keys and how the ladder is ordered.
"""

from __future__ import annotations

from .epm import CATEGORIES, CATEGORY_DIMS, DIM_BY_KEY
from .rubrics import RUBRICS

# Stable order of rubric keys, lowest → highest.
RUBRIC_LEVELS: list[str] = ["1-2", "3-5", "6-7", "8-9", "10"]

# Stage label per rubric key — shared with the FastAPI / Streamlit views.
LEVEL_STAGE: dict[str, str] = {
    "1-2": "Discovering",
    "3-5": "Developing",
    "6-7": "Confident",
    "8-9": "Advanced",
    "10":  "Elite",
}


def score_to_rubric_key(score: float) -> str:
    """Map a numeric EPM score to its rubric key."""
    if score <= 2:
        return "1-2"
    if score <= 5:
        return "3-5"
    if score <= 7:
        return "6-7"
    if score <= 9:
        return "8-9"
    return "10"


def next_rubric_key(key: str) -> str | None:
    """Return the next rubric key on the ladder, or None if already at the top."""
    try:
        idx = RUBRIC_LEVELS.index(key)
    except ValueError:
        return None
    return RUBRIC_LEVELS[idx + 1] if idx < len(RUBRIC_LEVELS) - 1 else None


def levels_for_dimension(dim_key: str) -> list[dict[str, str]]:
    """Return the full rubric ladder for a dimension (5 entries, low → high).

    Each entry: {key, stage, description}.
    Used for the player Mastery page where we show the whole ladder generically.
    """
    rubric = RUBRICS.get(dim_key, {})
    out = []
    for level in RUBRIC_LEVELS:
        out.append({
            "key": level,
            "stage": LEVEL_STAGE[level],
            "description": rubric.get(level, ""),
        })
    return out


def grouped_dimensions() -> list[dict]:
    """Return dimensions grouped by category, with metadata + full ladders.

    Shape:
        [
          {"category": "technical", "dimensions": [
              {"key", "name", "description", "levels": [...]},
              ...
          ]},
          ...
        ]
    """
    out = []
    for cat in CATEGORIES:
        dims = []
        for d in CATEGORY_DIMS.get(cat, []):
            dims.append({
                "key": d.key,
                "name": d.name,
                "description": d.description,
                "levels": levels_for_dimension(d.key),
            })
        out.append({"category": cat, "dimensions": dims})
    return out


def current_and_next(score: float, dim_key: str) -> dict:
    """For a given score on a dimension, return current and next rubric levels.

    Used by the 10-week review to show "where you are now" and "what's next."
    """
    cur = score_to_rubric_key(score)
    nxt = next_rubric_key(cur)
    rubric = RUBRICS.get(dim_key, {})
    meta = DIM_BY_KEY.get(dim_key)
    return {
        "key": dim_key,
        "name": meta.name if meta else dim_key,
        "score": score,
        "current": {
            "key": cur,
            "stage": LEVEL_STAGE[cur],
            "description": rubric.get(cur, ""),
        },
        "next": {
            "key": nxt,
            "stage": LEVEL_STAGE[nxt] if nxt else None,
            "description": rubric.get(nxt, "") if nxt else "",
        } if nxt else None,
    }
