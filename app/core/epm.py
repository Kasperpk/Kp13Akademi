"""EPM (Entity Propensity Model) – dimension definitions and scoring engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .config import EPM_ALPHA, EPM_MAX_SCORE, EPM_MIN_SCORE
from . import database as db

# ---- dimension catalogue -----------------------------------------------------

@dataclass(frozen=True)
class DimensionMeta:
    key: str
    name: str
    category: str          # technical | physical | cognitive | mental
    description: str


DIMENSIONS: list[DimensionMeta] = [
    # Technical
    DimensionMeta("first_touch",     "Første Touch",        "technical", "Modtagerkvalitet — kontrol i rum, på halvvending, under pres"),
    DimensionMeta("passing",         "Pasning",             "technical", "Vægt, præcision og beslutningstagning i aflevering"),
    DimensionMeta("ball_mastery",    "Boldbeherskelse",     "technical", "Tæt boldkontrol, komfort på bolden, teknisk repertoire"),
    DimensionMeta("dribbling_speed", "Dribling med Fart",   "technical", "Bære bolden i tempo, skub-og-løb, dynamisk boldføring"),
    DimensionMeta("finishing",       "Afslutning",          "technical", "Skudteknik, ro og præcision foran mål"),
    DimensionMeta("weak_foot",       "Svagt Ben",           "technical", "Færdigheder med ikke-dominante fod på tværs af alle teknikker"),
    # Physical
    DimensionMeta("acceleration",    "Acceleration",        "physical",  "Første 3-5 skridt, eksplosive starter, reaktiv hastighed"),
    DimensionMeta("agility",         "Smidighed",           "physical",  "Retningsskift, lateral bevægelse, kropskoordination"),
    DimensionMeta("endurance",       "Udholdenhed",         "physical",  "Vedvarende intensitet gennem session eller kamp"),
    # Cognitive
    DimensionMeta("game_reading",    "Spilforståelse",      "cognitive", "Positionsbevidsthed, scanning, forudseenhed på banen"),
    DimensionMeta("decision_speed",  "Beslutningshastighed","cognitive", "Valg af den rigtige handling under pres"),
    DimensionMeta("positional_play", "Positionsspil",       "cognitive", "Forståelse af rum og bevægelse uden bold"),
    # Mental
    DimensionMeta("resilience",      "Robusthed",           "mental",    "Reaktion på modgang, fejl og turneringspres"),
    DimensionMeta("intensity",       "Intensitet",          "mental",    "Indsats, tempo og urgency i træning"),
    DimensionMeta("coachability",    "Trænarbarhed",        "mental",    "Villighed til at prøve nyt og reagere på feedback"),
    DimensionMeta("joy",             "Glæde",               "mental",    "Engagement, entusiasme og glæde ved spillet"),
]

DIM_BY_KEY: dict[str, DimensionMeta] = {d.key: d for d in DIMENSIONS}
DIM_KEYS: list[str] = [d.key for d in DIMENSIONS]
CATEGORIES: list[str] = ["technical", "physical", "cognitive", "mental"]

CATEGORY_DIMS: dict[str, list[DimensionMeta]] = {}
for _d in DIMENSIONS:
    CATEGORY_DIMS.setdefault(_d.category, []).append(_d)

# ---- exercise → EPM mapping -------------------------------------------------

EXERCISE_CATEGORY_TO_EPM: dict[str, list[str]] = {
    "warmup":          ["ball_mastery", "agility"],
    "ball_mastery":    ["ball_mastery", "first_touch", "weak_foot"],
    "rondo":           ["passing", "first_touch", "decision_speed", "game_reading"],
    "positional_play": ["positional_play", "game_reading", "passing"],
    "passing":         ["passing", "first_touch"],
    "receiving":       ["first_touch", "positional_play"],
    "finishing":       ["finishing", "dribbling_speed"],
    "agility":         ["acceleration", "agility"],
    "small_sided_games": ["decision_speed", "game_reading", "intensity", "resilience"],
    "one_v_one":       ["dribbling_speed", "acceleration", "resilience", "decision_speed"],
    "cool_down":       ["joy"],
    "strength":        ["acceleration", "endurance"],
}


# ---- confidence levels -------------------------------------------------------

def _confidence(count: int) -> str:
    if count >= 10:
        return "high"
    if count >= 4:
        return "medium"
    return "low"


# ---- scoring engine ----------------------------------------------------------

def initialise_player_epm(player_id: str, baseline: dict[str, float] | None = None) -> None:
    """Set all 16 dimensions to a baseline score (default 5.0) for a new player."""
    baseline = baseline or {}
    for dim in DIM_KEYS:
        score = baseline.get(dim, 5.0)
        db.set_epm_score(player_id, dim, score, confidence="low", observation_count=0)


def update_scores_from_observation(
    player_id: str,
    observed: dict[str, float],
    alpha: float = EPM_ALPHA,
) -> dict[str, dict[str, Any]]:
    """Apply EMA update for each observed dimension. Returns updated scores.

    observed = {"first_touch": 7.5, "passing": 8.0, ...}
    Only dimensions present in *observed* are updated.
    """
    current = db.get_epm_scores(player_id)
    updated: dict[str, dict[str, Any]] = {}

    for dim_key, new_value in observed.items():
        if dim_key not in DIM_BY_KEY:
            continue
        new_value = max(EPM_MIN_SCORE, min(EPM_MAX_SCORE, new_value))

        if dim_key in current:
            old_score = current[dim_key]["score"]
            old_count = current[dim_key]["observation_count"]
        else:
            old_score = 5.0
            old_count = 0

        # Exponential moving average
        ema_score = round((1 - alpha) * old_score + alpha * new_value, 2)
        new_count = old_count + 1
        conf = _confidence(new_count)

        db.set_epm_score(player_id, dim_key, ema_score, conf, new_count)
        updated[dim_key] = {
            "previous": old_score,
            "observed": new_value,
            "new_score": ema_score,
            "confidence": conf,
            "observations": new_count,
        }

    return updated


def get_player_profile(player_id: str) -> dict[str, Any]:
    """Return a full player profile with EPM scores grouped by category."""
    player = db.get_player(player_id)
    if not player:
        return {}

    scores = db.get_epm_scores(player_id)
    by_category: dict[str, list[dict[str, Any]]] = {}
    for dim in DIMENSIONS:
        entry = scores.get(dim.key, {})
        item = {
            "key": dim.key,
            "name": dim.name,
            "description": dim.description,
            "score": entry.get("score", 5.0),
            "confidence": entry.get("confidence", "low"),
            "observations": entry.get("observation_count", 0),
        }
        by_category.setdefault(dim.category, []).append(item)

    return {
        "player": player,
        "scores": by_category,
        "flat_scores": {dim.key: scores.get(dim.key, {}).get("score", 5.0) for dim in DIMENSIONS},
    }


def identify_gaps(player_id: str, top_n: int = 3) -> list[dict[str, Any]]:
    """Return the top-N lowest-scoring dimensions (excluding joy/coachability)."""
    scores = db.get_epm_scores(player_id)
    _skip = {"joy", "coachability"}
    items = []
    for dim in DIMENSIONS:
        if dim.key in _skip:
            continue
        s = scores.get(dim.key, {}).get("score", 5.0)
        items.append({"key": dim.key, "name": dim.name, "score": s, "category": dim.category})
    items.sort(key=lambda x: x["score"])
    return items[:top_n]


def identify_strengths(player_id: str, top_n: int = 3) -> list[dict[str, Any]]:
    """Return the top-N highest-scoring dimensions."""
    scores = db.get_epm_scores(player_id)
    items = []
    for dim in DIMENSIONS:
        s = scores.get(dim.key, {}).get("score", 5.0)
        items.append({"key": dim.key, "name": dim.name, "score": s, "category": dim.category})
    items.sort(key=lambda x: x["score"], reverse=True)
    return items[:top_n]
