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
    "dribble_10m_seconds": MeasurementScale(low_anchor=2.2, high_anchor=4.2, lower_is_better=True),
    "t_drill_seconds": MeasurementScale(low_anchor=8.8, high_anchor=14.0, lower_is_better=True),
    "decision_intelligence_pct": MeasurementScale(low_anchor=20.0, high_anchor=90.0, lower_is_better=False),
    "wall_passes_right_30s": MeasurementScale(low_anchor=8.0, high_anchor=36.0, lower_is_better=False),
    "wall_passes_left_30s": MeasurementScale(low_anchor=4.0, high_anchor=28.0, lower_is_better=False),
    "shots_on_target_10": MeasurementScale(low_anchor=1.0, high_anchor=9.0, lower_is_better=False),
}


def suggest_epm_from_measurements(measurements: dict[str, float]) -> dict[str, float]:
    """Suggest initial EPM dimension scores from onboarding measurements."""
    out: dict[str, float] = {}

    sprint = measurements.get("sprint_10m_seconds")
    if sprint is not None:
        out["acceleration"] = map_to_score(sprint, _MEASUREMENT_SCALES["sprint_10m_seconds"])

    dribble = measurements.get("dribble_10m_seconds")
    if dribble is not None:
        out["dribbling_speed"] = map_to_score(dribble, _MEASUREMENT_SCALES["dribble_10m_seconds"])

    if sprint is not None and dribble is not None:
        delta = max(0.0, dribble - sprint)
        # Smaller delta means less speed loss with the ball.
        out["ball_mastery"] = map_to_score(
            delta,
            MeasurementScale(low_anchor=0.3, high_anchor=1.8, lower_is_better=True),
        )

    t_drill = measurements.get("t_drill_seconds")
    if t_drill is not None:
        out["agility"] = map_to_score(t_drill, _MEASUREMENT_SCALES["t_drill_seconds"])

    decision_pct = measurements.get("decision_intelligence_pct")
    if decision_pct is not None:
        decision_score = map_to_score(
            decision_pct,
            _MEASUREMENT_SCALES["decision_intelligence_pct"],
        )
        out["decision_speed"] = decision_score
        out["game_reading"] = decision_score

    right_passes = measurements.get("wall_passes_right_30s")
    left_passes = measurements.get("wall_passes_left_30s")
    if right_passes is not None:
        out["passing"] = map_to_score(
            right_passes,
            _MEASUREMENT_SCALES["wall_passes_right_30s"],
        )
    if left_passes is not None:
        out["weak_foot"] = map_to_score(
            left_passes,
            _MEASUREMENT_SCALES["wall_passes_left_30s"],
        )

    shots = measurements.get("shots_on_target_10")
    if shots is not None:
        out["finishing"] = map_to_score(shots, _MEASUREMENT_SCALES["shots_on_target_10"])

    return out


def key_metrics_snapshot(measurements: dict[str, float]) -> dict[str, float]:
    """Return normalized key onboarding metrics for dashboards and history views."""
    keep = {
        "sprint_10m_seconds",
        "dribble_10m_seconds",
        "decision_intelligence_pct",
        "t_drill_seconds",
        "shots_on_target_10",
    }
    return {k: v for k, v in measurements.items() if k in keep}
