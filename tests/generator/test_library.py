"""Tests for generator.library — filter_exercises, score_by_recency, pick_random_weighted."""

from __future__ import annotations

import random
from datetime import date


def test_filter_by_category(sample_exercises):
    from library import filter_exercises
    from models import Category

    result = filter_exercises(sample_exercises, categories=[Category.RONDO])

    assert len(result) == 1
    assert result[0].id == "rondo_1"


def test_filter_by_age_excludes_out_of_range(sample_exercises):
    from library import filter_exercises

    # finish_1 age_range=[10, 18] — age=9 should exclude it.
    result = filter_exercises(sample_exercises, age=9)
    assert all(ex.id != "finish_1" for ex in result)

    # age=20 should exclude mastery_1 (age 6-14) and pass_1 (7-12)
    result_adult = filter_exercises(sample_exercises, age=20)
    assert all(ex.id not in {"mastery_1", "pass_1"} for ex in result_adult)


def test_filter_by_min_players_available(sample_exercises):
    """min_players_available caps ex.min_players."""
    from library import filter_exercises

    # Only 1 player available — rondo_1 (min 5) and pass_1 (min 2) excluded.
    result = filter_exercises(sample_exercises, min_players_available=1)
    ids = {ex.id for ex in result}
    assert "rondo_1" not in ids
    assert "pass_1" not in ids
    assert "mastery_1" in ids


def test_filter_excluded_ids_removed(sample_exercises):
    from library import filter_exercises

    result = filter_exercises(sample_exercises, excluded_ids={"mastery_1", "pass_1"})

    ids = {ex.id for ex in result}
    assert ids == {"rondo_1", "finish_1"}


def test_filter_combines_criteria_as_AND(sample_exercises):
    from library import filter_exercises
    from models import Category

    result = filter_exercises(
        sample_exercises,
        categories=[Category.PASSING, Category.RONDO],
        age=9,
        min_players_available=4,
    )

    # age 9 excludes nothing here; 4 players available allows pass_1 (min 2) but not rondo_1 (min 5).
    assert len(result) == 1
    assert result[0].id == "pass_1"


def test_score_by_recency_never_used_first(sample_exercises, today_fixed):
    from library import score_by_recency

    # Only mastery_1 was used; others should score 9999.
    history = {"mastery_1": date(2026, 4, 20)}

    scored = score_by_recency(sample_exercises, history, today=today_fixed)

    # Scored list sorts DESC by days_since — 9999-entries come first.
    assert scored[0][1] == 9999
    # mastery_1 used 3 days ago should be last.
    assert scored[-1][0].id == "mastery_1"
    assert scored[-1][1] == 3


def test_score_by_recency_orders_by_days_desc(sample_exercises, today_fixed):
    from library import score_by_recency

    history = {
        "pass_1": date(2026, 4, 1),    # 22 days ago
        "rondo_1": date(2026, 4, 20),  # 3 days ago
        "mastery_1": date(2026, 4, 10),  # 13 days ago
        "finish_1": date(2026, 4, 22),  # 1 day ago
    }

    scored = score_by_recency(sample_exercises, history, today=today_fixed)

    days = [d for _, d in scored]
    assert days == sorted(days, reverse=True)
    assert scored[0][0].id == "pass_1"
    assert scored[-1][0].id == "finish_1"


def test_pick_random_weighted_returns_requested_count(sample_exercises, today_fixed):
    from library import pick_random_weighted

    random.seed(42)
    picks = pick_random_weighted(sample_exercises, {}, count=2, today=today_fixed)

    assert len(picks) == 2
    # No duplicates within a single pick batch.
    assert len({ex.id for ex in picks}) == 2


def test_pick_random_weighted_count_capped_by_pool(sample_exercises, today_fixed):
    from library import pick_random_weighted

    picks = pick_random_weighted(sample_exercises, {}, count=99, today=today_fixed)

    assert len(picks) == len(sample_exercises)


def test_pick_random_weighted_empty_pool_returns_empty(today_fixed):
    from library import pick_random_weighted

    assert pick_random_weighted([], {}, count=3, today=today_fixed) == []
