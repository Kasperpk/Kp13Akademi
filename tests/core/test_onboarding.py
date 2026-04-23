from app.core.onboarding import MeasurementScale, map_to_score, suggest_epm_from_measurements


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
        "dribble_10m_seconds": 3.1,
        "t_drill_seconds": 11.2,
        "decision_intelligence_pct": 55.0,
        "wall_passes_right_30s": 20.0,
        "wall_passes_left_30s": 14.0,
        "shots_on_target_10": 5.0,
    }

    suggested = suggest_epm_from_measurements(measurements)

    expected_dims = {
        "acceleration",
        "dribbling_speed",
        "ball_mastery",
        "agility",
        "decision_speed",
        "game_reading",
        "passing",
        "weak_foot",
        "finishing",
    }
    assert expected_dims.issubset(set(suggested.keys()))
    assert all(1.0 <= score <= 10.0 for score in suggested.values())
