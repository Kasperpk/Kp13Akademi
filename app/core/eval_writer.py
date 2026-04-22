"""Write calibrated session observations as eval ground-truth cases.

A case captures the inputs the model sees plus the human-calibrated expected
scores for the dimensions Kasper anchored with a rationale. Dimensions without
a rationale are NOT included — only explicit calibration counts as ground truth.
"""

from __future__ import annotations

import json
from datetime import date as _date
from pathlib import Path
from typing import Any

EVAL_CASES_ROOT = (
    Path(__file__).resolve().parents[2]
    / "skills"
    / "epm-extraction"
    / "evals"
    / "cases"
)


def write_eval_case(
    *,
    player_id: str,
    session_date: str | _date,
    session_type: str,
    session_theme: str,
    coach_notes: str,
    player_profile_snapshot: dict[str, Any],
    expected_scores: dict[str, float],
    rationales: dict[str, str],
    score_tolerance: float = 0.5,
) -> Path | None:
    """Write a single eval case JSON. Returns the path written, or None if no
    dimension has both a score and a rationale (nothing to ground-truth).
    """
    if isinstance(session_date, _date):
        session_date = session_date.isoformat()

    grounded = {
        dim: score
        for dim, score in expected_scores.items()
        if rationales.get(dim, "").strip()
    }
    if not grounded:
        return None

    expected_ranges = {
        dim: [round(score - score_tolerance, 2), round(score + score_tolerance, 2)]
        for dim, score in grounded.items()
    }
    rationale_block = {
        dim: rationales[dim].strip() for dim in grounded if rationales.get(dim)
    }

    case = {
        "case_id": f"{player_id}_{session_date}",
        "player_id": player_id,
        "date": session_date,
        "session_type": session_type,
        "session_theme": session_theme,
        "coach_notes": coach_notes,
        "player_profile": player_profile_snapshot,
        "expected": expected_ranges,
        "rationales": rationale_block,
    }

    EVAL_CASES_ROOT.mkdir(parents=True, exist_ok=True)
    out_path = EVAL_CASES_ROOT / f"{player_id}_{session_date}.json"
    out_path.write_text(json.dumps(case, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_path
