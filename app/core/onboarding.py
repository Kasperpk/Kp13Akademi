"""Onboarding helpers: convert measurable tests into baseline EPM suggestions.

The goal is not perfect scientific validity in v1; it's a consistent, explainable
baseline that can be re-tested over time and improved with coaching evidence.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MeasurementScale:
    """Defines a linear score mapping from raw value to EPM score (1-10)."""

    low_anchor: float
    high_anchor: float
    lower_is_better: bool


def _clamp_score(score: float) -> float:
    return round(max(1.0, min(10.0, score)), 2)


def map_to_score(value: float, scale: MeasurementScale) -> float:
    """Map a raw metric to a 1-10 score via linear interpolation.

    Anchors define the range where values map from 1 to 10. Values outside the
    range are clamped.
    """
    if scale.low_anchor == scale.high_anchor:
        return 5.0

    if scale.lower_is_better:
        worst = scale.high_anchor
        best = scale.low_anchor
        ratio = (worst - value) / (worst - best)
    else:
        worst = scale.low_anchor
        best = scale.high_anchor
        ratio = (value - worst) / (best - worst)

    return _clamp_score(1.0 + ratio * 9.0)


_MEASUREMENT_SCALES: dict[str, MeasurementScale] = {
    "sprint_10m_seconds": MeasurementScale(low_anchor=1.8, high_anchor=3.2, lower_is_better=True),
    "turn_sprint_no_ball_seconds": MeasurementScale(low_anchor=5.5, high_anchor=9.0, lower_is_better=True),
    "turn_sprint_with_ball_seconds": MeasurementScale(low_anchor=6.5, high_anchor=11.0, lower_is_better=True),
    "ball_tax_seconds": MeasurementScale(low_anchor=0.3, high_anchor=1.8, lower_is_better=True),
    "juggling_alt_count": MeasurementScale(low_anchor=0.0, high_anchor=30.0, lower_is_better=False),
    "taps_right_15s": MeasurementScale(low_anchor=20.0, high_anchor=60.0, lower_is_better=False),
    "taps_left_15s": MeasurementScale(low_anchor=15.0, high_anchor=50.0, lower_is_better=False),
}


def _avg(values: list[float]) -> float:
    return sum(values) / len(values)


def suggest_epm_from_measurements(measurements: dict[str, float]) -> dict[str, float]:
    """Suggest initial EPM dimension scores from onboarding measurements."""
    out: dict[str, float] = {}

    sprint = measurements.get("sprint_10m_seconds")
    if sprint is not None:
        out["acceleration"] = map_to_score(sprint, _MEASUREMENT_SCALES["sprint_10m_seconds"])

    turn_no_ball = measurements.get("turn_sprint_no_ball_seconds")
    if turn_no_ball is not None:
        out["agility"] = map_to_score(
            turn_no_ball,
            _MEASUREMENT_SCALES["turn_sprint_no_ball_seconds"],
        )

    turn_with_ball = measurements.get("turn_sprint_with_ball_seconds")
    if turn_with_ball is not None:
        out["dribbling_speed"] = map_to_score(
            turn_with_ball,
            _MEASUREMENT_SCALES["turn_sprint_with_ball_seconds"],
        )

    ball_mastery_components: list[float] = []

    if turn_no_ball is not None and turn_with_ball is not None:
        ball_tax = max(0.0, turn_with_ball - turn_no_ball)
        ball_mastery_components.append(
            map_to_score(ball_tax, _MEASUREMENT_SCALES["ball_tax_seconds"])
        )

    juggling_alt = measurements.get("juggling_alt_count")
    if juggling_alt is not None:
        ball_mastery_components.append(
            map_to_score(juggling_alt, _MEASUREMENT_SCALES["juggling_alt_count"])
        )

    taps_right = measurements.get("taps_right_15s")
    if taps_right is not None:
        ball_mastery_components.append(
            map_to_score(taps_right, _MEASUREMENT_SCALES["taps_right_15s"])
        )

    if ball_mastery_components:
        out["ball_mastery"] = _clamp_score(_avg(ball_mastery_components))

    taps_left = measurements.get("taps_left_15s")
    if taps_left is not None:
        out["weak_foot"] = map_to_score(taps_left, _MEASUREMENT_SCALES["taps_left_15s"])

    return out


def key_metrics_snapshot(measurements: dict[str, float]) -> dict[str, float]:
    """Return normalized key onboarding metrics for dashboards and history views."""
    keep = {
        "sprint_10m_seconds",
        "long_jump_cm",
        "turn_sprint_no_ball_seconds",
        "turn_sprint_with_ball_seconds",
        "juggling_alt_count",
        "taps_right_15s",
        "taps_left_15s",
    }
    return {k: v for k, v in measurements.items() if k in keep}
