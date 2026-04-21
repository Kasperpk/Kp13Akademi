"""ELM (Entity Language Model) – Claude integration for coaching intelligence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Generator

import anthropic

from .config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
from .epm import DIMENSIONS, DIM_BY_KEY, CATEGORIES, CATEGORY_DIMS
from .rubrics import all_rubrics_text, rubric_for_dimension

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
    """Generate a personalised daily home-training plan in Danish."""
    client = _client()
    system = _build_system_prompt(player_profile)
    player_name = player_profile["player"]["name"]

    def _fallback_daily_plan() -> str:
        chosen = available_exercises[:3]
        if not chosen:
            return (
                f"## Dagens træning for {player_name}\n\n"
                "### FOKUS\n"
                "Vi arbejder med førsteberøring, orientering og tempo i boldbehandling, så det bliver nemmere at spille fremad i kamp.\n\n"
                "### OPVARMNING (4 min)\n"
                "- 2 x 45 sek toe taps + 15 sek pause\n"
                "- 2 x 45 sek inside-outside touches + 15 sek pause\n\n"
                "### HOVEDBLOK (14 min)\n"
                "- 3 runder: 90 sek arbejde / 30 sek pause\n"
                "- Fokus: første touch væk fra pres, hovedet oppe før hver aktion\n\n"
                "### NEDKØLING (3 min)\n"
                "- Let jonglering og rolig mobilitet for ankler/hofter\n\n"
                "### KASPERS BESKED\n"
                f"{player_name}, gør det i kampfart i korte perioder - kvalitet først, så tempo.\n"
            )

        lines: list[str] = [
            f"## Dagens træning for {player_name}",
            "",
            "### FOKUS",
            "Vi træner konkrete kamphandlinger med høj kvalitet i førsteberøring, orientering og beslutning i fart.",
            "",
            "### OPVARMNING (4-5 min)",
            "- 2 x 45 sek let boldarbejde (inside/outside, toe taps) + 15 sek pause",
            "",
            "### HOVEDBLOK (12-15 min)",
        ]

        for idx, ex in enumerate(chosen, start=1):
            coaching_points = ex.get("coaching_points") or []
            cp_preview = "; ".join(coaching_points[:2]) if coaching_points else "Fokus pa timing, kontrol og retning i første touch"
            video_line = ex.get("video_url") or ex.get("video_search_url") or ""
            lines.extend([
                f"{idx}. **{ex.get('name', 'Øvelse')}** ({ex.get('duration_min', 5)} min)",
                f"   - Hvorfor: {ex.get('description', '')}",
                f"   - Setup: {ex.get('setup') or 'Lav en enkel bane med kegler og 1 bold'}",
                f"   - Coaching: {cp_preview}",
            ])
            if video_line:
                lines.append(f"   - Video: {video_line}")

        lines.extend([
            "",
            "### NEDKØLING (2-3 min)",
            "- Let udstrækning og 30-50 rolige jongleringer",
            "",
            "### KASPERS BESKED",
            f"{player_name}, hold kvaliteten i alle berøringer - det er sådan træning flytter sig til kamp.",
        ])
        return "\n".join(lines)

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
        cp = ex.get("coaching_points") or []
        cp_text = "; ".join(cp[:3]) if cp else ""
        setup_text = ex.get("setup") or ""
        video_line = ex.get("video_url") or ex.get("video_search_url") or ""
        exercises_text += (
            f"\n- {ex['name']}: {ex['description']} ({ex['duration_min']}min, {ex['intensity']})"
            f"\n  Setup: {setup_text}"
            f"\n  Coaching points: {cp_text}"
            f"\n  Video: {video_line}"
        )

    user_msg = f"""\
Lav en hjemmetræningssession for i dag (15-25 minutter).

STØRSTE UDVIKLINGSOMRÅDER: {gaps_text}
STYRKER AT BYGGE VIDERE PÅ: {strengths_text}

SENESTE SESSIONER: {recent_text}

TILGÆNGELIGE ØVELSER:
{exercises_text}

Skriv sessionen i direkte, tydeligt fodboldsprog. Tiltal {player_profile['player']['name']} ved navn.
Struktur:

1. **FOKUS** — En sætning: hvad vi arbejder med, og hvorfor det betyder noget i kamp.
2. **OPVARMNING** (3-5 min) — Simpelt boldarbejde, så kroppen og touch bliver skarp.
3. **HOVEDBLOK** (10-15 min) — 2-3 øvelser med konkrete gentagelser, varighed og opsætning. Vær præcis, så en forælder uden fodboldbaggrund kan gennemføre det.
4. **NEDKØLING** (2-3 min) — Let udstrækning eller jonglering.
5. **KASPERS BESKED** — En sætning, der kobler dagens arbejde til spillerens spil.

Ekstra krav for hver øvelse i HOVEDBLOK:
- Medtag en kort linje: "Sådan gør I" (2-4 konkrete trin)
- Medtag en kort linje: "Det skal du kigge efter" (1-2 coaching cues)
- Medtag en linje med "Video" og brug kun links fra øvelseslisten ovenfor

Vigtigt formatkrav:
- Start direkte ved punkt 1 (FOKUS)
- Skriv IKKE titel, overskrift med spillernavn eller en "Dato:"-linje

Skriv ALT på dansk. Maks 350 ord. Ingen emojis. Ren markdown. Fodboldsprog, ikke fitness-jargon."""

    try:
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )
        return response.content[0].text
    except Exception:
        # Fallback keeps the app usable even if LLM provider/network is unavailable.
        return _fallback_daily_plan()


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
        "video_url": {"type": "string", "description": "Video URL for parent/player reference. Prefer direct exercise video; fallback to provided search URL."},
    },
    "required": ["exercise_id", "name", "description", "duration_min", "reps", "setup", "coaching_points", "why_this_exercise", "video_url"],
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
    if ex.get('video_url'):
        parts.append(f"  Video URL: {ex['video_url']}")
    if ex.get('video_search_url'):
        parts.append(f"  Video Search URL: {ex['video_search_url']}")
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

8. Include a video_url for EVERY exercise. Use "Video URL" from the exercise card if present; \
otherwise use "Video Search URL" from the same card.

9. Vary the exercises across sessions — don't repeat the same exercise in multiple sessions.

Use the create_weekly_schedule tool to submit the complete schedule."""

    def _fallback_weekly_schedule() -> dict[str, Any]:
        # Deterministic fallback if LLM is unavailable: keeps player app usable.
        picked = available_exercises[:12]

        def _mk_ex(ex: dict[str, Any], default_min: int = 5) -> dict[str, Any]:
            cps = ex.get("coaching_points") or []
            cp_text = " / ".join(cps[:2]) if isinstance(cps, list) else str(cps)
            return {
                "exercise_id": ex.get("id", "manual_drill"),
                "name": ex.get("name", "Teknisk øvelse"),
                "description": ex.get("description", "Teknisk træning med fokus på kvalitet i førsteberøring."),
                "duration_min": int(ex.get("duration_min", default_min)),
                "reps": "3 x 45 sek arbejde / 20 sek pause",
                "setup": ex.get("setup") or "Sæt 4 kegler i et kvadrat på ca. 4x4 meter med 1 bold.",
                "coaching_points": cp_text or "Små kontrollerede berøringer og hovedet oppe før næste aktion.",
                "why_this_exercise": f"Matcher {player_name}s nuværende fokusområder og styrker beslutning og udførelse i fart.",
                "video_url": ex.get("video_url") or ex.get("video_search_url") or "",
            }

        # Build 3 short sessions from available pool.
        def _slice(i: int) -> list[dict[str, Any]]:
            chunk = picked[i:i + 4]
            if not chunk:
                chunk = [{"id": "fallback", "name": "Ball mastery basis", "description": "Kontrol i små områder.", "duration_min": 5}]
            return chunk

        s1 = _slice(0)
        s2 = _slice(4)
        s3 = _slice(8)
        return {
            "week_focus": "Førsteberøring, orientering og tempo i boldbehandling",
            "week_rationale": f"Planen holder {player_name} i gang med kvalitetstræning, også når AI-tjenesten er utilgængelig.",
            "sessions": [
                {
                    "day": "Monday",
                    "theme": "Grundmønstre med høj kvalitet",
                    "duration_min": 18,
                    "warm_up": [_mk_ex(s1[0])],
                    "main": [_mk_ex(ex) for ex in s1[1:3]],
                    "cool_down": [_mk_ex(s1[3] if len(s1) > 3 else s1[0], default_min=3)],
                    "coaches_note": "Se efter rolig førsteberøring og øjne oppe før næste handling.",
                },
                {
                    "day": "Wednesday",
                    "theme": "Samme mønstre i højere tempo",
                    "duration_min": 18,
                    "warm_up": [_mk_ex(s2[0])],
                    "main": [_mk_ex(ex) for ex in s2[1:3]],
                    "cool_down": [_mk_ex(s2[3] if len(s2) > 3 else s2[0], default_min=3)],
                    "coaches_note": "Se efter at kvaliteten holdes, selv når tempoet stiger.",
                },
                {
                    "day": "Friday",
                    "theme": "Kombination under træthed",
                    "duration_min": 18,
                    "warm_up": [_mk_ex(s3[0])],
                    "main": [_mk_ex(ex) for ex in s3[1:3]],
                    "cool_down": [_mk_ex(s3[3] if len(s3) > 3 else s3[0], default_min=3)],
                    "coaches_note": "Se efter beslutninger i fart: første gode løsning, udført rent.",
                },
            ],
        }

    try:
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
    except Exception:
        return _fallback_weekly_schedule()

    return _fallback_weekly_schedule()


# ---- Danish weekly training plan ---------------------------------------------

_LA_MASIA_PATH = Path(__file__).resolve().parents[2] / "generator" / "principles" / "la_masia.md"
_KP13_METHODOLOGY_PATH = Path(__file__).resolve().parents[2] / "generator" / "principles" / "kp13_methodology.md"

# Age-group dimension priorities: higher weight = more important at this stage
_AGE_DIM_WEIGHTS: dict[str, dict[str, float]] = {
    "U7": {"ball_mastery": 2.0, "first_touch": 2.0, "weak_foot": 2.0, "joy": 2.0, "agility": 1.5},
    "U8": {"ball_mastery": 2.0, "first_touch": 2.0, "weak_foot": 2.0, "joy": 2.0, "agility": 1.5},
    "U9": {"ball_mastery": 2.0, "first_touch": 2.0, "weak_foot": 2.0, "joy": 1.5, "dribbling_speed": 1.5, "agility": 1.5},
    "U10": {"ball_mastery": 1.8, "first_touch": 1.8, "weak_foot": 1.8, "dribbling_speed": 1.5, "passing": 1.3},
    "U11": {"first_touch": 1.5, "passing": 1.5, "game_reading": 1.5, "decision_speed": 1.5, "ball_mastery": 1.3},
    "U12": {"passing": 1.5, "game_reading": 1.5, "decision_speed": 1.5, "positional_play": 1.3, "finishing": 1.3},
    "U13": {"game_reading": 1.5, "decision_speed": 1.5, "positional_play": 1.5, "passing": 1.3, "finishing": 1.3},
    "U14": {"game_reading": 1.5, "positional_play": 1.5, "finishing": 1.5, "resilience": 1.3, "intensity": 1.3},
    "U15": {"positional_play": 1.5, "game_reading": 1.5, "resilience": 1.5, "intensity": 1.5, "finishing": 1.3},
}


def _age_weighted_gaps(gaps: list[dict[str, Any]], age_group: str) -> list[dict[str, Any]]:
    """Re-rank gaps by multiplying gap size by age-group developmental weight."""
    weights = _AGE_DIM_WEIGHTS.get(age_group, {})
    scored = []
    for g in gaps:
        w = weights.get(g["key"], 1.0)
        scored.append((g, (10.0 - g["score"]) * w))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [g for g, _ in scored]


def _load_la_masia() -> str:
    try:
        return _LA_MASIA_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _load_kp13_methodology() -> str:
    try:
        return _KP13_METHODOLOGY_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def generate_weekly_plan_danish(
    player: dict[str, Any],
    gaps: list[dict[str, Any]],
    strengths: list[dict[str, Any]],
    recent_observations: list[dict[str, Any]],
    sessions_per_week: int,
    available_exercises: list[dict[str, Any]],
    player_goals: str = "",
) -> str:
    """Generate a full weekly training plan in Danish.

    Priority for focus selection:
    1. Coach notes from recent sessions (explicit flags override everything)
    2. Age-weighted EPM gaps (most impactful dimension to improve right now)
    3. Player goals if they align with EPM data
    """
    client = _client()

    age_group = player.get("age_group", "U9")
    player_name = player["name"].split()[0]
    dominant_foot = player.get("dominant_foot", "højre")
    position = player.get("position", "N/A")
    coach_notes_on_player = player.get("notes", "")

    # Age-weighted gap priority
    prioritized_gaps = _age_weighted_gaps(gaps, age_group)
    focus_dims = prioritized_gaps[:2]

    # Build rubric blocks for the top focus dimensions
    rubric_blocks = ""
    for g in focus_dims:
        rubric_blocks += f"\n\n### {g['name']} (nuværende score: {g['score']:.1f}/10)\n"
        rubric_blocks += rubric_for_dimension(g["key"])

    # Build recent session text
    recent_text = ""
    for obs in recent_observations[:3]:
        recent_text += f"\n- {obs['date']} ({obs.get('session_type', 'N/A')}): {obs.get('theme', 'N/A')}"
        if obs.get("coach_notes"):
            recent_text += f"\n  Kaspers noter: {obs['coach_notes'][:300]}"

    # Exercise library for the prompt — IDs kept for reference only, never shown in output
    exercises_text = ""
    for ex in available_exercises[:25]:
        exercises_text += f"\n• {ex['name']} ({ex['duration_min']} min, {ex['intensity']}): {ex['description']}"
        if ex.get("setup"):
            exercises_text += f"\n  Setup: {ex['setup']}"
        if ex.get("coaching_points"):
            cps = ex["coaching_points"]
            if isinstance(cps, list):
                exercises_text += f"\n  Fokuspunkter: {' / '.join(cps[:3])}"

    la_masia = _load_la_masia()
    kp13_methodology = _load_kp13_methodology()

    day_names = {2: "Mandag og Torsdag", 3: "Mandag, Onsdag og Fredag", 4: "Mandag, Tirsdag, Torsdag og Lørdag"}
    days_label = day_names.get(sessions_per_week, f"{sessions_per_week} gange om ugen")

    system = f"""\
Du er KP13 Akademiets AI-træningsmester. Du designer ugentlige HJEMMETRÆNINGSPLANER.

━━━ KONTEKST ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Kasper har sine egne akademi-sessioner (1 time, planlagt af ham selv). \
Disse hjemmeplaner er det {player_name} laver ALENE i løbet af ugen — ingen træner, ingen forælder nødvendigvis. \
Spilleren er alene med sin bold. Design ALLE øvelser så de kan laves 100% solo.

ALDRIG skriv "Kasper siger/råber/kigger/tæller" — han er ikke der. \
ALDRIG forudsæt at der er en forælder til stede. \
Brug "du" til {player_name} direkte. \
Selvtjek skrives som: "Tjek: [hvad du selv kan mærke eller se]"
Hvis der skal bruges et signal: "sæt en timer på [X] sekunder" eller "tæl selv til [X]".

━━━ KP13 TRÆNINGSFILOSOFI ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{kp13_methodology}

━━━ LA MASIA PRINCIPPER ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{la_masia[:800]}

━━━ EVALUERINGSRUBRIKER FOR FOKUSOMRÅDER ━━━━━━━━━━━━━━━━━━
{rubric_blocks}

PRIORITETSRÆKKEFØLGE for fokus:
1. Hvad Kasper eksplicit har nævnt i sine noter (HØJESTE prioritet)
2. Alderstilpassede EPM-huller
3. Spillerens egne mål
"""

    user_msg = f"""\
Lav en komplet ugentlig træningsplan for {player_name}.

SPILLER-PROFIL:
  Navn: {player["name"]}
  Aldersgruppe: {age_group}
  Position: {position}
  Dominerende fod: {dominant_foot}
  Kaspers noter om spilleren: {coach_notes_on_player or "Ingen specifikke noter."}

SPILLERENS MÅL:
{player_goals or "Ingen specifikke mål angivet — brug EPM-data til at sætte fokus."}

AKTUELLE EPM-HULLER (prioriteret efter alder og vigtighed):
{chr(10).join(f"  - {g['name']}: {g['score']:.1f}/10" for g in prioritized_gaps[:4])}

STYRKER (byg videre på disse):
{chr(10).join(f"  - {s['name']}: {s['score']:.1f}/10" for s in strengths[:3])}

SENESTE SESSIONER:
{recent_text if recent_text else "  Ingen tidligere sessioner registreret — dette er en frisk start."}

TILGÆNGELIGE ØVELSER:
{exercises_text}

PLAN-FORMAT:
Lav {sessions_per_week} sessioner ({days_label}). Skriv planen som en sammenhængende, letlæselig tekst \
henvendt direkte til {player_name} og hans forælder. Brug "du" til {player_name}.

For HVER session:

---
## [UGEDAG] — [Fokusområde] · ca. [X] min

**Hvorfor denne session?**
1-2 sætninger til {player_name}: hvad træner du i dag, og hvad betyder det for din næste kamp?

**Opvarmning** (5 min)
Beskriv 1-2 øvelser direkte til {player_name}. Angiv præcis setup (afstande, antal kegler) og reps/tid. \
Skriv klart og konkret — hans forælder skal kunne sætte det op uden fodbolderfaring.

**Hoveddel** (10-15 min)
2 øvelser beskrevet på samme måde. Hvert øvelse på 3-5 sætninger.
Afslut hver øvelse med: *Forældre: hold øje med [konkret, observerbar handling der viser {player_name} gør det rigtigt]*

**Nedvarmning** (2-3 min)
Én kort aktivitet der runder sessionen af med ro og kontrol.

**De bedste spillere gør sådan her:**
2-3 sætninger om hvad elite-spillere på {player_name}s niveau konkret gør anderledes. \
Gør det nærværende og konkret — ikke abstrakt.

**Fodboldkoncept: [Navn på konceptet]**
4-5 sætninger direkte til {player_name} i alderstilpasset sprog. \
Forklar HVORFOR dette koncept gør ham sværere at stoppe i kampen.

*Kaspers besked til {player_name}: "[Én direkte, personlig sætning der forbinder dagens træning til hans spil og næste kamp."]"*

---

VIGTIGE REGLER:
- Skriv ALT på dansk — flydende, naturligt, direkte. Tal til {player_name} som en rigtig træner.
- ALDRIG brug øvelses-ID'er (koder som 'bm_sole_taps') — brug kun det rigtige øvelsesnavn
- ALDRIG skriv "Kasper siger/råber/tæller/kigger" — han er ikke der
- ALDRIG forudsæt en forælder er til stede — alle øvelser laves solo med én bold
- Signaler erstattes af: "sæt en timer på X sekunder" eller "tæl selv til X"
- Selvtjek skrives som: "Tjek: bolden skal blive inden for armlængde"
- KP13-intensitet (Persian Ball-stil): kort, skarp, høj tempo. Ikke langsomme øvelser.
- Brug KP13's øvelsesvokabular: sole rolls, V-drag, L-drag, inside-outside, toe-taps, push-and-go
- Alle sessioner starter med bold mastery — det er fundamentet
- Begge fødder trænes i ALLE sessioner — dette er ikke til forhandling
- Hver øvelse kobles til en konkret kampsituation
- Ugentlig progression: Session 1 = lær mønsteret langsomt med fokus, Session 2 = samme mønster ved spillehastighed, Session 3 = udfordring og kombination under pres
- Vær hyper-specifik: ikke "øv first touch" men "modtag bolden og lad den rulle 45 grader fra dig — aldrig bagud, altid fremad i spilretningen"
- Max 420 ord per session
"""

    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=6000,
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
