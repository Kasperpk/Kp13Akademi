from app.core.onboarding import (
    MeasurementScale,
    key_metrics_snapshot,
    map_to_score,
    suggest_epm_from_measurements,
)


def test_map_to_score_lower_is_better():
    scale = MeasurementScale(low_anchor=2.0, high_anchor=4.0, lower_is_better=True)
    assert map_to_score(2.0, scale) == 10.0
    assert map_to_score(4.0, scale) == 1.0
    assert 5.4 <= map_to_score(3.0, scale) <= 5.6


def test_map_to_score_higher_is_better():
    scale = MeasurementScale(low_anchor=10.0, high_anchor=30.0, lower_is_better=False)
    assert map_to_score(10.0, scale) == 1.0
    assert map_to_score(30.0, scale) == 10.0
    assert 5.4 <= map_to_score(20.0, scale) <= 5.6


def test_suggest_epm_from_measurements_derives_expected_keys():
    measurements = {
        "sprint_10m_seconds": 2.6,
        "turn_sprint_no_ball_seconds": 7.0,
        "turn_sprint_with_ball_seconds": 8.0,
        "juggling_alt_count": 12.0,
        "taps_right_15s": 35.0,
        "taps_left_15s": 28.0,
    }

    suggested = suggest_epm_from_measurements(measurements)

    expected_dims = {
        "acceleration",
        "agility",
        "dribbling_speed",
        "ball_mastery",
        "weak_foot",
    }
    assert expected_dims == set(suggested.keys())
    assert all(1.0 <= score <= 10.0 for score in suggested.values())


def test_ball_mastery_uses_ball_tax_and_skill_components():
    measurements = {
        "turn_sprint_no_ball_seconds": 6.5,
        "turn_sprint_with_ball_seconds": 7.0,
        "juggling_alt_count": 15.0,
        "taps_right_15s": 40.0,
    }

    suggested = suggest_epm_from_measurements(measurements)
    assert "ball_mastery" in suggested
    assert 1.0 <= suggested["ball_mastery"] <= 10.0


def test_key_metrics_snapshot_filters_to_new_keys():
    measurements = {
        "sprint_10m_seconds": 2.6,
        "long_jump_cm": 145.0,
        "turn_sprint_no_ball_seconds": 7.0,
        "turn_sprint_with_ball_seconds": 8.0,
        "juggling_alt_count": 12.0,
        "taps_right_15s": 35.0,
        "taps_left_15s": 28.0,
        "self_confidence_1v1": 6.0,
        "ball_tax_seconds": 1.0,
    }

    snapshot = key_metrics_snapshot(measurements)
    assert set(snapshot.keys()) == {
        "sprint_10m_seconds",
        "long_jump_cm",
        "turn_sprint_no_ball_seconds",
        "turn_sprint_with_ball_seconds",
        "juggling_alt_count",
        "taps_right_15s",
        "taps_left_15s",
    }
