"""Tests for app.core.recommender — dimension-to-exercise mapping and filtering."""

from __future__ import annotations

import pytest


@pytest.fixture
def patched_recommender(monkeypatch, sample_exercises):
    """Patch recommender internals so no YAML/history file I/O happens."""
    from app.core import recommender

    monkeypatch.setattr(recommender, "_all_exercises", lambda: sample_exercises)
    monkeypatch.setattr(recommender, "last_used_map", lambda _path: {})
    return recommender


def test_recommend_for_gaps_maps_passing_dimension_to_passing_or_rondo(patched_recommender):
    gaps = [{"key": "passing"}]

    results = patched_recommender.recommend_for_gaps(
        gaps, max_results=10, age=9, max_players=4
    )

    assert results
    categories = {r["category"] for r in results}
    # EXERCISE_CATEGORY_TO_EPM maps passing → {"rondo", "passing", "positional_play", "receiving"}
    assert categories.issubset({"rondo", "passing", "positional_play", "receiving"})
    # Each returned exercise should list 'passing' as a targeted dimension.
    assert all("passing" in r["targets_dimensions"] for r in results)


def test_recommend_for_gaps_respects_age_filter(patched_recommender):
    # finish_1 age_range=[10, 18] — should be excluded for a 9-year-old.
    gaps = [{"key": "finishing"}]

    results = patched_recommender.recommend_for_gaps(
        gaps, max_results=10, age=9, max_players=4
    )

    assert all(r["id"] != "finish_1" for r in results)


def test_recommend_for_gaps_respects_solo_constraint(patched_recommender):
    """max_players=1 (solo home-training) must exclude drills that need >=2 players."""
    gaps = [{"key": "passing"}]

    results = patched_recommender.recommend_for_gaps(
        gaps, max_results=10, age=9, max_players=1
    )

    # rondo_1 needs min 5 players; pass_1 needs min 2 — both excluded.
    assert all(r["id"] not in {"rondo_1", "pass_1"} for r in results)


def test_recommend_empty_gaps_returns_empty(patched_recommender):
    assert patched_recommender.recommend_for_gaps([], max_results=10, age=9) == []


def test_recommend_unknown_dimension_returns_empty(patched_recommender):
    gaps = [{"key": "not_a_real_dim"}]

    results = patched_recommender.recommend_for_gaps(gaps, max_results=10, age=9)

    assert results == []
