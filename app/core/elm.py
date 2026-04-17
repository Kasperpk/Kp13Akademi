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


# ---- weekly schedule generation (structured) ---------------------------------

_EXERCISE_IN_SESSION_SCHEMA = {
    "type": "object",
    "properties": {
        "exercise_id": {"type": "string", "description": "ID from the exercise library (e.g. bm_sole_taps)"},
        "name": {"type": "string", "description": "Exercise name from the library"},
        "description": {"type": "string", "description": "What the player does — rewritten for home context if needed"},
        "duration_min": {"type": "integer", "description": "Minutes for this exercise"},
        "reps": {"type": "string", "description": "Specific reps/sets/duration. e.g. '3 x 30 seconds each foot', '8 reps left, 8 reps right'"},
        "setup": {"type": "string", "description": "Exact setup for home/garden: distances, equipment placement. A parent with zero football knowledge must understand this."},
        "coaching_points": {"type": "string", "description": "2-3 key coaching cues from the library, phrased as observable actions"},
        "why_this_exercise": {"type": "string", "description": "One sentence: why THIS exercise for THIS player right now (link to their EPM gap or strength)"},
    },
    "required": ["exercise_id", "name", "description", "duration_min", "reps", "setup", "coaching_points", "why_this_exercise"],
}

_WEEKLY_SCHEDULE_TOOL = {
    "name": "create_weekly_schedule",
    "description": "Create a structured weekly home training schedule using exercises from the library.",
    "input_schema": {
        "type": "object",
        "properties": {
            "week_focus": {
                "type": "string",
                "description": "The main development theme for this week — stated as a footballing problem, not a vague label. e.g. 'Receiving on the half-turn to play forward under pressure'",
            },
            "week_rationale": {
                "type": "string",
                "description": "2-3 sentences: WHY this focus, based on EPM data. What gap are we closing? What did recent sessions reveal?",
            },
            "sessions": {
                "type": "array",
                "description": "Exactly 3 training sessions for the week",
                "items": {
                    "type": "object",
                    "properties": {
                        "day": {"type": "string", "enum": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]},
                        "theme": {"type": "string", "description": "Session's red thread — one specific footballing concept that connects all exercises"},
                        "duration_min": {"type": "integer"},
                        "warm_up": {"type": "array", "items": _EXERCISE_IN_SESSION_SCHEMA},
                        "main": {"type": "array", "items": _EXERCISE_IN_SESSION_SCHEMA},
                        "cool_down": {"type": "array", "items": _EXERCISE_IN_SESSION_SCHEMA},
                        "coaches_note": {"type": "string", "description": "One sentence for the parent: what to watch for that shows progress. Phrased as an observable action."},
                    },
                    "required": ["day", "theme", "duration_min", "warm_up", "main", "cool_down", "coaches_note"],
                },
            },
        },
        "required": ["week_focus", "week_rationale", "sessions"],
    },
}


def _format_exercise_for_prompt(ex: dict[str, Any]) -> str:
    """Format a single exercise dict into a rich text block for the prompt."""
    parts = [f"  ID: {ex['id']}"]
    parts.append(f"  Name: {ex['name']}")
    parts.append(f"  Category: {ex['category']}")
    parts.append(f"  Description: {ex['description']}")
    parts.append(f"  Duration: {ex['duration_min']} min | Intensity: {ex['intensity']} | Space: {ex['space']}")
    parts.append(f"  Equipment: {', '.join(ex.get('equipment', ['ball']))}")
    if ex.get('setup'):
        parts.append(f"  Setup: {ex['setup']}")
    if ex.get('coaching_points'):
        if isinstance(ex['coaching_points'], list):
            parts.append(f"  Coaching points: {' / '.join(ex['coaching_points'])}")
        else:
            parts.append(f"  Coaching points: {ex['coaching_points']}")
    if ex.get('variations'):
        var_text = "; ".join(f"{v['name']}: {v['description']}" for v in ex['variations'][:3])
        parts.append(f"  Variations: {var_text}")
    if ex.get('targets_dimensions'):
        parts.append(f"  Targets EPM: {', '.join(ex['targets_dimensions'])}")
    return "\n".join(parts)


def generate_weekly_schedule(
    player_profile: dict[str, Any],
    gaps: list[dict[str, Any]],
    strengths: list[dict[str, Any]],
    recent_sessions: list[dict[str, Any]],
    available_exercises: list[dict[str, Any]],
) -> dict[str, Any]:
    """Generate a structured weekly home-training schedule using tool_use.

    Uses the real exercise library — Claude selects, sequences, and
    contextualises exercises for this specific player based on EPM data.
    """
    client = _client()
    system = _build_system_prompt(player_profile)

    player_name = player_profile["player"]["name"].split()[0]
    player_info = player_profile["player"]

    # Build rich gap/strength text with context
    gaps_text = ""
    for g in gaps:
        gaps_text += f"\n  - {g['name']} ({g['key']}): {g['score']:.1f}/10"

    strengths_text = ""
    for s in strengths:
        strengths_text += f"\n  - {s['name']} ({s['key']}): {s['score']:.1f}/10"

    recent_text = ""
    for s in recent_sessions[:5]:
        recent_text += f"\n  - {s['date']} ({s['session_type']}): {s.get('theme', 'N/A')}"
        if s.get("coach_notes"):
            recent_text += f"\n    {s['coach_notes'][:200]}"

    # Build full exercise library text with all details
    exercises_text = ""
    for ex in available_exercises:
        exercises_text += f"\n\n{_format_exercise_for_prompt(ex)}"

    player_notes = player_info.get("notes", "")

    user_msg = f"""\
Create {player_name}'s home training schedule for this week.

PLAYER CONTEXT:
  Name: {player_info['name']}
  Age group: {player_info.get('age_group', 'U9')}
  Position: {player_info.get('position', 'N/A')}
  Dominant foot: {player_info.get('dominant_foot', 'right')}
  Coach notes: {player_notes}

EPM GAPS (priority areas):
{gaps_text}

EPM STRENGTHS (build on these):
{strengths_text}

RECENT SESSIONS:
{recent_text if recent_text else "  None yet — this is a fresh start."}

═══════════════════════════════════════════════
EXERCISE LIBRARY — YOU MUST SELECT FROM THESE
═══════════════════════════════════════════════
{exercises_text}

═══════════════════════════════════════════════
RULES
═══════════════════════════════════════════════

1. SELECT exercises from the library above. Use the exact exercise_id and name. \
You may adapt the description and setup for home/garden context (1 player, 1 ball, \
optional wall/cones, small space).

2. EACH SESSION needs a RED THREAD — a single footballing concept that connects \
warm-up through main to cool-down. Not "ball mastery" (too vague) but \
"Quick feet to create space for the first touch forward" (specific, game-connected).

3. THREE SESSIONS that form a WEEKLY PROGRESSION:
   - Session 1 (Monday/Tuesday): Foundation — slow, technical, build the pattern
   - Session 2 (Wednesday/Thursday): Speed — same pattern at game speed, add pressure/decisions
   - Session 3 (Friday/Saturday): Challenge — combine patterns, compete, test under fatigue

4. Each session: 1-2 warm-up exercises, 2-3 main exercises, 1 cool-down. Total 15-20 minutes.

5. The why_this_exercise field must reference the player's actual EPM data. \
e.g. "Driving with Ball at 4.0 — this exercise builds the push-and-go rhythm \
{player_name} needs to carry the ball forward instead of defaulting to the safe pass."

6. Setup instructions must be crystal clear for a parent with ZERO football knowledge. \
Include exact distances, cone placement, where to stand, what "success" looks like.

7. Coaching points should be observable actions, not vague advice. \
"Light touch — ball barely moves" not "Have good technique."

8. Vary the exercises across sessions — don't repeat the same exercise in multiple sessions.

Use the create_weekly_schedule tool to submit the complete schedule."""

    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=8000,
        system=system,
        tools=[_WEEKLY_SCHEDULE_TOOL],
        tool_choice={"type": "tool", "name": "create_weekly_schedule"},
        messages=[{"role": "user", "content": user_msg}],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "create_weekly_schedule":
            return block.input

    return {"week_focus": "General development", "sessions": []}


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
