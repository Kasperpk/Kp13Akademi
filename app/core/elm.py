"""ELM (Entity Language Model) – Claude integration for coaching intelligence."""

from __future__ import annotations

import json
from typing import Any, Generator

import anthropic

from .config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
from .epm import DIMENSIONS, DIM_BY_KEY, CATEGORIES, CATEGORY_DIMS
from .rubrics import all_rubrics_text

# ---- client ------------------------------------------------------------------

def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


# ---- system prompt -----------------------------------------------------------

_ACADEMY_CONTEXT = """\
You are the intelligence engine for KP13 Akademi, an elite private football academy \
coaching young players (ages 7-12) individually and in small groups.

Coaching philosophy:
- La Masia principles: possession as identity, positional play, rondo as foundation, \
  both-feet development, game-realistic decision-making, small-sided games.
- Constraints-Led Approach: manipulate task/environment constraints so players discover \
  solutions instead of being told.
- Ecological dynamics: representative learning design, nonlinear pedagogy.
- Every session has a "red thread" — a single theme progressing through all phases.

The EPM (Entity Propensity Model) tracks 16 dimensions per player:
"""

def _build_system_prompt(player_profile: dict[str, Any] | None = None) -> str:
    parts = [_ACADEMY_CONTEXT]

    # List all dimensions
    for cat in CATEGORIES:
        dims = CATEGORY_DIMS[cat]
        parts.append(f"\n{cat.upper()}:")
        for d in dims:
            parts.append(f"  - {d.name} ({d.key}): {d.description}")

    if player_profile:
        p = player_profile["player"]
        parts.append(f"\n\nCURRENT PLAYER: {p['name']}")
        parts.append(f"Age group: {p.get('age_group', 'N/A')}")
        parts.append(f"Position: {p.get('position', 'N/A')}")
        parts.append(f"Dominant foot: {p.get('dominant_foot', 'N/A')}")
        parts.append(f"Club: {p.get('club', 'N/A')}")

        parts.append("\nEPM SCORES:")
        for cat, dims in player_profile["scores"].items():
            parts.append(f"  {cat.upper()}:")
            for d in dims:
                conf_tag = f" [{d['confidence']}]" if d["confidence"] != "high" else ""
                parts.append(f"    {d['name']}: {d['score']:.1f}/10{conf_tag}")

    return "\n".join(parts)


# ---- tool definitions for structured extraction ------------------------------

_EXTRACT_TOOL = {
    "name": "record_session_scores",
    "description": (
        "Extract EPM dimension scores (1-10) from coaching session notes. "
        "Only score dimensions that were clearly observed in the session. "
        "Use null for dimensions not observed or not applicable."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            d.key: {
                "type": ["number", "null"],
                "description": f"{d.name}: {d.description}. Score 1-10 or null if not observed.",
            }
            for d in DIMENSIONS
        },
        "required": [],
    },
}


# ---- extraction from coach notes --------------------------------------------

def extract_scores_from_notes(
    coach_notes: str,
    session_theme: str,
    session_type: str,
    player_profile: dict[str, Any],
) -> dict[str, float]:
    """Use Claude tool_use to extract structured EPM scores from free-text notes.

    Returns dict of {dimension_key: score} for observed dimensions only.
    """
    client = _client()
    system = _build_system_prompt(player_profile)

    user_msg = f"""\
Session type: {session_type}
Session theme: {session_theme}

Coach notes:
{coach_notes}

SCORING RUBRIC — use these observable behaviours to calibrate your scores:
{all_rubrics_text()}

Based on the coaching observations above, extract scores (1-10) for every dimension \
where the notes provide clear behavioural evidence. Match what you read in the notes \
to the rubric levels above. Only score dimensions you can confidently rate. \
Use the record_session_scores tool to submit your ratings."""

    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=1024,
        system=system,
        tools=[_EXTRACT_TOOL],
        tool_choice={"type": "tool", "name": "record_session_scores"},
        messages=[{"role": "user", "content": user_msg}],
    )

    # Parse tool_use response
    for block in response.content:
        if block.type == "tool_use" and block.name == "record_session_scores":
            raw = block.input
            return {k: float(v) for k, v in raw.items() if v is not None}
    return {}


# ---- daily plan generation ---------------------------------------------------

def generate_daily_plan(
    player_profile: dict[str, Any],
    gaps: list[dict[str, Any]],
    strengths: list[dict[str, Any]],
    recent_sessions: list[dict[str, Any]],
    available_exercises: list[dict[str, Any]],
) -> str:
    """Generate a personalised daily home-training plan."""
    client = _client()
    system = _build_system_prompt(player_profile)

    recent_text = ""
    for s in recent_sessions[:5]:
        recent_text += f"\n- {s['date']} ({s['session_type']}): {s.get('theme', 'N/A')}"
        if s.get("coach_notes"):
            notes_preview = s["coach_notes"][:200]
            recent_text += f"\n  Notes: {notes_preview}"

    gaps_text = ", ".join(f"{g['name']} ({g['score']:.1f})" for g in gaps)
    strengths_text = ", ".join(f"{s['name']} ({s['score']:.1f})" for s in strengths)

    exercises_text = ""
    for ex in available_exercises[:20]:
        exercises_text += f"\n- {ex['name']}: {ex['description']} ({ex['duration_min']}min, {ex['intensity']})"

    user_msg = f"""\
Generate a home training session for today (15-25 minutes).

TOP GAPS to address: {gaps_text}
STRENGTHS to build on: {strengths_text}

RECENT SESSIONS: {recent_text}

AVAILABLE EXERCISES:
{exercises_text}

Write the session plan in direct, football language. Address {player_profile['player']['name']} by name.
Structure:

1. **FOCUS** — One sentence: what we're working on and why it matters in the game.
2. **WARM-UP** (3-5 min) — Simple ball work to get sharp.
3. **MAIN BLOCK** (10-15 min) — 2-3 exercises with specific reps, durations, and setup. Be precise — a parent with zero football knowledge should be able to run this.
4. **COOL-DOWN** (2-3 min) — Stretching or juggling.
5. **COACH'S NOTE** — One sentence connecting today's work to the player's game.

Keep it under 350 words. No emojis. Clean markdown. Football language, not fitness jargon."""

    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": user_msg}],
    )
    return response.content[0].text


# ---- weekly parent summary ---------------------------------------------------

def generate_weekly_summary(
    player_profile: dict[str, Any],
    week_observations: list[dict[str, Any]],
    epm_history: list[dict[str, Any]],
    gaps: list[dict[str, Any]],
    strengths: list[dict[str, Any]],
) -> str:
    """Generate a natural-language weekly summary for parents."""
    client = _client()
    system = _build_system_prompt(player_profile)

    obs_text = ""
    for obs in week_observations:
        obs_text += f"\n### {obs['date']} — {obs['session_type']}: {obs.get('theme', 'N/A')}"
        if obs.get("coach_notes"):
            obs_text += f"\n{obs['coach_notes']}"
        if obs.get("extracted_scores"):
            scores_str = ", ".join(f"{k}: {v}" for k, v in obs["extracted_scores"].items())
            obs_text += f"\nScores: {scores_str}"

    gaps_text = ", ".join(f"{g['name']} ({g['score']:.1f})" for g in gaps)
    strengths_text = ", ".join(f"{s['name']} ({s['score']:.1f})" for s in strengths)

    user_msg = f"""\
Write a weekly progress report for {player_profile['player']['name']}'s parent.

THIS WEEK'S SESSIONS:
{obs_text if obs_text else "No sessions logged this week."}

CURRENT STRENGTHS: {strengths_text}
CURRENT GAPS: {gaps_text}

Write in a warm but direct tone. Use the player's first name throughout.
Use development stage language where possible — for example, "{player_profile['player']['name']} is \
moving from Developing to Confident in first touch" rather than raw numbers.

Include:
1. WHAT WE WORKED ON — brief summary of the week's sessions
2. WHAT I SAW — key observations, specific moments, improvements
3. WHAT'S NEXT — where we're heading next week
4. HOW YOU CAN HELP — one specific, easy thing the parent can do at home

Keep it concise (250-350 words). Be honest but encouraging. No emojis. \
If joy or engagement concerns exist, flag them clearly."""

    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=1500,
        system=system,
        messages=[{"role": "user", "content": user_msg}],
    )
    return response.content[0].text


# ---- coach session prep ------------------------------------------------------

def generate_session_prep(
    player_profile: dict[str, Any],
    gaps: list[dict[str, Any]],
    recent_sessions: list[dict[str, Any]],
    available_exercises: list[dict[str, Any]],
) -> str:
    """Generate a session preparation brief for the coach."""
    client = _client()
    system = _build_system_prompt(player_profile)

    recent_text = ""
    for s in recent_sessions[:5]:
        recent_text += f"\n- {s['date']} ({s['session_type']}): {s.get('theme', 'N/A')}"
        if s.get("coach_notes"):
            notes_preview = s["coach_notes"][:300]
            recent_text += f"\n  {notes_preview}"

    gaps_text = ", ".join(f"{g['name']} ({g['score']:.1f})" for g in gaps)

    user_msg = f"""\
Prepare a coaching brief for the next individual session.

DEVELOPMENT GAPS: {gaps_text}

RECENT SESSIONS:
{recent_text}

Suggest:
1. SESSION THEME — one clear red thread for the session
2. KEY FOCUS — the #1 thing to develop today and why (link to causal model)
3. WATCH FOR — what to observe that indicates progress or continued struggle
4. TRANSFER CHECK — what to look for in the next team session to see if today's work sticks
5. SUGGESTED EXERCISES — 3-4 exercises from the library that target today's theme

Be direct and coaching-focused. This is for the coach, not the parent."""

    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=1500,
        system=system,
        messages=[{"role": "user", "content": user_msg}],
    )
    return response.content[0].text
