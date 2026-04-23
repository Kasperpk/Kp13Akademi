"""Tests for app.core.epm — EMA scoring, confidence, gap/strength identification."""

from __future__ import annotations

import math

import pytest


def test_ema_update_formula(mock_epm_db):
    from app.core import epm

    mock_epm_db[("p1", "first_touch")] = {
        "score": 5.0,
        "confidence": "low",
        "observation_count": 0,
        "updated_at": None,
    }

    result = epm.update_scores_from_observation("p1", {"first_touch": 8.0}, alpha=0.3)

    # new = (1 - 0.3) * 5.0 + 0.3 * 8.0 = 5.9
    assert math.isclose(result["first_touch"]["new_score"], 5.9, abs_tol=1e-6)
    assert result["first_touch"]["previous"] == 5.0
    assert result["first_touch"]["observed"] == 8.0


def test_ema_clamps_to_valid_range(mock_epm_db):
    from app.core import epm
    from app.core.config import EPM_MAX_SCORE, EPM_MIN_SCORE

    mock_epm_db[("p1", "passing")] = {
        "score": 5.0,
        "confidence": "low",
        "observation_count": 0,
        "updated_at": None,
    }

    high = epm.update_scores_from_observation("p1", {"passing": 99.0}, alpha=0.5)
    assert high["passing"]["observed"] == EPM_MAX_SCORE

    mock_epm_db[("p1", "passing")] = {
        "score": 5.0,
        "confidence": "low",
        "observation_count": 0,
        "updated_at": None,
    }
    low = epm.update_scores_from_observation("p1", {"passing": -5.0}, alpha=0.5)
    assert low["passing"]["observed"] == EPM_MIN_SCORE


def test_observation_count_increments(mock_epm_db):
    from app.core import epm

    mock_epm_db[("p1", "agility")] = {
        "score": 5.0,
        "confidence": "low",
        "observation_count": 2,
        "updated_at": None,
    }

    result = epm.update_scores_from_observation("p1", {"agility": 6.0}, alpha=0.3)
    assert result["agility"]["observations"] == 3


def test_unknown_dimension_is_ignored(mock_epm_db):
    from app.core import epm

    result = epm.update_scores_from_observation("p1", {"not_a_real_dim": 7.0}, alpha=0.3)
    assert result == {}


def test_new_dimension_uses_default_baseline(mock_epm_db):
    """A dimension absent from the store starts at 5.0, count 0."""
    from app.core import epm

    result = epm.update_scores_from_observation("p1", {"finishing": 9.0}, alpha=0.5)

    # new = 0.5 * 5.0 + 0.5 * 9.0 = 7.0
    assert math.isclose(result["finishing"]["new_score"], 7.0, abs_tol=1e-6)
    assert result["finishing"]["observations"] == 1


@pytest.mark.parametrize(
    ("count", "expected"),
    [
        (0, "low"),
        (1, "low"),
        (3, "low"),
        (4, "medium"),
        (9, "medium"),
        (10, "high"),
        (50, "high"),
    ],
)
def test_confidence_buckets(count, expected):
    from app.core.epm import _confidence

    assert _confidence(count) == expected


def test_identify_gaps_excludes_joy_and_coachability(mock_epm_db):
    from app.core import epm

    for dim in epm.DIM_KEYS:
        mock_epm_db[("p1", dim)] = {
            "score": 7.0,
            "confidence": "medium",
            "observation_count": 5,
            "updated_at": None,
        }
    # Make joy and coachability the lowest by far.
    mock_epm_db[("p1", "joy")]["score"] = 1.0
    mock_epm_db[("p1", "coachability")]["score"] = 1.0

    gaps = epm.identify_gaps("p1", top_n=3)

    gap_keys = {g["key"] for g in gaps}
    assert "joy" not in gap_keys
    assert "coachability" not in gap_keys


def test_identify_gaps_returns_top_n_ascending(mock_epm_db):
    from app.core import epm

    for dim in epm.DIM_KEYS:
        mock_epm_db[("p1", dim)] = {
            "score": 7.0,
            "confidence": "medium",
            "observation_count": 5,
            "updated_at": None,
        }
    mock_epm_db[("p1", "passing")]["score"] = 3.0
    mock_epm_db[("p1", "finishing")]["score"] = 4.0
    mock_epm_db[("p1", "acceleration")]["score"] = 5.0

    gaps = epm.identify_gaps("p1", top_n=3)

    assert [g["key"] for g in gaps] == ["passing", "finishing", "acceleration"]
    assert gaps[0]["score"] < gaps[1]["score"] < gaps[2]["score"]


def test_identify_strengths_returns_top_n_descending(mock_epm_db):
    from app.core import epm

    for dim in epm.DIM_KEYS:
        mock_epm_db[("p1", dim)] = {
            "score": 5.0,
            "confidence": "medium",
            "observation_count": 5,
            "updated_at": None,
        }
    mock_epm_db[("p1", "ball_mastery")]["score"] = 9.0
    mock_epm_db[("p1", "first_touch")]["score"] = 8.5
    mock_epm_db[("p1", "passing")]["score"] = 8.0

    strengths = epm.identify_strengths("p1", top_n=3)

    assert [s["key"] for s in strengths] == ["ball_mastery", "first_touch", "passing"]
    assert strengths[0]["score"] > strengths[1]["score"] > strengths[2]["score"]
