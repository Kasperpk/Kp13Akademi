"""Session designer agent — picks and sequences one week of home training.

This agent's sole job is to design a coherent three-session week for a player.
It loads only what it needs:

    - the `session-design` and `weekly-progression` skills
    - the player's profile + EPM scores + recent observations
    - a filtered slice of the exercise library that matches current gaps

Output is a `WeeklySchedule` — the Pydantic contract in `app/core/models.py`,
which is also the FastAPI mobile UI's binding contract.

Invoke from CLI:

    python -m app.core.agents.session_designer --player felix --week 2026-04-22
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import anthropic

from ..config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
from ..epm import get_player_profile, identify_gaps, identify_strengths
from ..models import ScheduledExercise, ScheduledSession, WeeklySchedule
from ..recommender import recommend_exercises
from ..skill_loader import load_skill
from .. import database as db


# ---- prompt assembly ---------------------------------------------------------


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def _format_exercise(ex: dict[str, Any]) -> str:
    parts = [f"  ID: {ex['id']}"]
    parts.append(f"  Name: {ex['name']}")
    parts.append(f"  Category: {ex['category']}")
    parts.append(f"  Description: {ex['description']}")
    parts.append(f"  Duration: {ex['duration_min']} min | Intensity: {ex['intensity']} | Space: {ex['space']}")
    parts.append(f"  Equipment: {', '.join(ex.get('equipment', ['ball']))}")
    if ex.get("setup"):
        parts.append(f"  Setup: {ex['setup']}")
    if ex.get("coaching_points"):
        cps = ex["coaching_points"]
        cp_text = " / ".join(cps) if isinstance(cps, list) else str(cps)
        parts.append(f"  Coaching points: {cp_text}")
    if ex.get("variations"):
        var_text = "; ".join(f"{v['name']}: {v['description']}" for v in ex["variations"][:3])
        parts.append(f"  Variations: {var_text}")
    if ex.get("targets_dimensions"):
        parts.append(f"  Targets EPM: {', '.join(ex['targets_dimensions'])}")
    if ex.get("video_url"):
        parts.append(f"  Video URL: {ex['video_url']}")
    if ex.get("video_search_url"):
        parts.append(f"  Video Search URL: {ex['video_search_url']}")
    return "\n".join(parts)


def _build_system_prompt(player_profile: dict[str, Any]) -> str:
    """Minimal system prompt — only what the session designer needs.

    Intentionally narrower than the `elm._build_system_prompt` (which dumps the
    full dimension catalogue). The designer sees the player's EPM scores in the
    user message; the skill files carry the methodology.
    """
    p = player_profile["player"]
    lines = [
        "You are the KP13 Akademi session designer.",
        "Your single job: design ONE coherent home-training week for the player below.",
        "Output is consumed directly by the player's mobile UI via a structured tool call.",
        "",
        f"CURRENT PLAYER: {p['name']}",
        f"Age group: {p.get('age_group', 'N/A')}",
        f"Position: {p.get('position', 'N/A')}",
        f"Dominant foot: {p.get('dominant_foot', 'N/A')}",
    ]
    return "\n".join(lines) + "\n\n" + load_skill("weekly-progression") + "\n\n" + load_skill("session-design")


# ---- fallback ----------------------------------------------------------------


def _fallback_schedule(
    player_name: str, available_exercises: list[dict[str, Any]]
) -> WeeklySchedule:
    """Deterministic schedule when the LLM is unavailable. Keeps the mobile UI usable."""
    picked = available_exercises[:12] or [{
        "id": "fallback", "name": "Ball mastery basis",
        "description": "Kontrol i små områder.", "duration_min": 5,
    }]

    def _mk(ex: dict[str, Any], default_min: int = 5) -> ScheduledExercise:
        cps = ex.get("coaching_points") or []
        cp_text = " / ".join(cps[:2]) if isinstance(cps, list) else str(cps)
        return ScheduledExercise(
            exercise_id=ex.get("id", "manual_drill"),
            name=ex.get("name", "Teknisk øvelse"),
            description=ex.get("description", "Teknisk træning med fokus på kvalitet i førsteberøring."),
            duration_min=int(ex.get("duration_min", default_min)),
            reps="3 x 45 sek arbejde / 20 sek pause",
            setup=ex.get("setup") or "Sæt 4 kegler i et kvadrat på ca. 4x4 meter med 1 bold.",
            coaching_points=cp_text or "Små kontrollerede berøringer og hovedet oppe før næste aktion.",
            why_this_exercise=f"Matcher {player_name}s nuværende fokusområder og styrker beslutning og udførelse i fart.",
            video_url=ex.get("video_url") or ex.get("video_search_url") or "",
        )

    def _slice(i: int) -> list[dict[str, Any]]:
        chunk = picked[i:i + 4]
        return chunk if chunk else [picked[0]]

    s1, s2, s3 = _slice(0), _slice(4), _slice(8)
    return WeeklySchedule(
        week_focus="Førsteberøring, orientering og tempo i boldbehandling",
        week_rationale=f"Planen holder {player_name} i gang med kvalitetstræning, også når AI-tjenesten er utilgængelig.",
        sessions=[
            ScheduledSession(
                day="Monday",
                theme="Grundmønstre med høj kvalitet",
                duration_min=18,
                warm_up=[_mk(s1[0])],
                main=[_mk(ex) for ex in s1[1:3]],
                cool_down=[_mk(s1[3] if len(s1) > 3 else s1[0], default_min=3)],
                coaches_note="Se efter rolig førsteberøring og øjne oppe før næste handling.",
            ),
            ScheduledSession(
                day="Wednesday",
                theme="Samme mønstre i højere tempo",
                duration_min=18,
                warm_up=[_mk(s2[0])],
                main=[_mk(ex) for ex in s2[1:3]],
                cool_down=[_mk(s2[3] if len(s2) > 3 else s2[0], default_min=3)],
                coaches_note="Se efter at kvaliteten holdes, selv når tempoet stiger.",
            ),
            ScheduledSession(
                day="Friday",
                theme="Kombination under træthed",
                duration_min=18,
                warm_up=[_mk(s3[0])],
                main=[_mk(ex) for ex in s3[1:3]],
                cool_down=[_mk(s3[3] if len(s3) > 3 else s3[0], default_min=3)],
                coaches_note="Se efter beslutninger i fart: første gode løsning, udført rent.",
            ),
        ],
    )


# ---- main entry point --------------------------------------------------------


def _load_context(player_id: str) -> dict[str, Any]:
    """Gather everything the agent needs from the DB + exercise library."""
    profile = get_player_profile(player_id)
    if not profile:
        raise ValueError(f"Unknown player: {player_id}")

    gaps = identify_gaps(player_id, top_n=5)
    strengths = identify_strengths(player_id, top_n=3)
    recent = db.get_observations(player_id, limit=5)

    age_str = profile["player"].get("age_group", "U9")
    try:
        age_int = int("".join(c for c in age_str if c.isdigit()) or "9")
    except ValueError:
        age_int = 9

    gap_dims = [g["key"] for g in gaps]
    exercises = recommend_exercises(gap_dims, max_results=40, age=age_int, max_players=2)

    # Personal bests for the exercises in scope this week, so the LLM can
    # set targets just above what the player already managed.
    exercise_ids = [ex["id"] for ex in exercises if ex.get("id")]
    recent_results = db.get_recent_results(player_id, exercise_ids=exercise_ids)

    return {
        "profile": profile,
        "gaps": gaps,
        "strengths": strengths,
        "recent": recent,
        "exercises": exercises,
        "recent_results": recent_results,
    }


def design_week(player_id: str, week_start: str) -> WeeklySchedule:
    """Design one week of home training for `player_id`.

    `week_start` is an ISO date (Monday). It is passed through to the LLM for
    context but does not otherwise affect selection — the schedule is a rolling
    three-session arc, not calendar-bound beyond the weekday labels.
    """
    ctx = _load_context(player_id)
    profile = ctx["profile"]
    gaps = ctx["gaps"]
    strengths = ctx["strengths"]
    recent = ctx["recent"]
    exercises = ctx["exercises"]
    recent_results = ctx["recent_results"]

    player_info = profile["player"]
    player_name = player_info["name"].split()[0]

    tool = {
        "name": "create_weekly_schedule",
        "description": "Create a structured weekly home training schedule using exercises from the library.",
        "input_schema": WeeklySchedule.model_json_schema(),
    }

    gaps_text = "".join(f"\n  - {g['name']} ({g['key']}): {g['score']:.1f}/10" for g in gaps)
    strengths_text = "".join(f"\n  - {s['name']} ({s['key']}): {s['score']:.1f}/10" for s in strengths)

    recent_text = ""
    for s in recent[:5]:
        recent_text += f"\n  - {s['date']} ({s['session_type']}): {s.get('theme', 'N/A')}"
        if s.get("coach_notes"):
            recent_text += f"\n    {s['coach_notes'][:200]}"

    if recent_results:
        records_lines = []
        for ex_id, results in recent_results.items():
            last = results[0]
            target_part = f" (mål var {last['target']})" if last.get("target") else ""
            unit = (last.get("result_unit") or "").strip()
            value = last.get("result_value")
            value_str = f"{value:g}" if value is not None else "?"
            records_lines.append(
                f"  - {ex_id} ({last['exercise_name']}): seneste resultat {value_str} {unit}{target_part}"
            )
        records_text = "\n".join(records_lines)
    else:
        records_text = "  (ingen tidligere resultater registreret endnu)"

    exercises_text = "\n\n".join(_format_exercise(ex) for ex in exercises)

    user_msg = f"""\
Design {player_name}'s home training week starting {week_start}.
Follow the principles, the three-session arc, and the per-exercise quality bar from the \
weekly-progression skill.

PLAYER CONTEXT:
  Name: {player_info['name']}
  Age group: {player_info.get('age_group', 'U9')}
  Position: {player_info.get('position', 'N/A')}
  Dominant foot: {player_info.get('dominant_foot', 'right')}
  Coach notes: {player_info.get('notes', '')}

EPM GAPS (priority areas):{gaps_text or '  (none identified yet)'}

EPM STRENGTHS (build on these):{strengths_text or '  (baseline)'}

RECENT SESSIONS:
{recent_text if recent_text else '  None yet — this is a fresh start.'}

PERSONLIGE REKORDER (seneste målbare resultater pr. øvelse):
{records_text}

═══════════════════════════════════════════════
EXERCISE LIBRARY — YOU MUST SELECT FROM THESE
═══════════════════════════════════════════════
{exercises_text}

Use the exact exercise_id and name from the library. You may adapt the description and setup \
for the solo home/garden context. The why_this_exercise field must reference {player_name}'s \
actual EPM data (e.g. naming the gap dimension and current score).

For video_url: use the "Video URL" from the exercise card when present; otherwise use the \
"Video Search URL". Never invent links.

TARGET RULE (vigtigt for motivation):
For HVER øvelse med målbar udgang skal du sætte feltet `target` som et konkret tal+enhed \
på dansk — fx "85 toe taps", "30 sekunder", "10 vægpas i træk". Hvis spilleren har et \
tidligere resultat for samme exercise_id (se PERSONLIGE REKORDER ovenfor), skal `target` \
ligge lige over det — typisk +5–10 %. Hvis der ikke er noget tidligere resultat, sæt et \
realistisk udgangspunkt for U9. For øvelser uden målbar udgang (udstrækning, ren teknik-fokus \
uden tælling), sæt `target` til null. Reps-feltet er stadig "sådan udfører du øvelsen"; \
target er overskriften "her er tallet du skal slå".

Use the create_weekly_schedule tool to submit the complete schedule."""

    try:
        response = _client().messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=8000,
            system=_build_system_prompt(profile),
            tools=[tool],
            tool_choice={"type": "tool", "name": "create_weekly_schedule"},
            messages=[{"role": "user", "content": user_msg}],
        )
        for block in response.content:
            if block.type == "tool_use" and block.name == "create_weekly_schedule":
                return WeeklySchedule.model_validate(block.input)
    except Exception:
        return _fallback_schedule(player_name, exercises)

    return _fallback_schedule(player_name, exercises)


# ---- persistence boundary ---------------------------------------------------


def load_schedule(player_id: str, week_start: str) -> WeeklySchedule | None:
    """Return the stored schedule for (player, week) as a validated model.

    The DB stores the JSON dict; validation happens here so callers get a
    typed `WeeklySchedule` instead of a loose dict.
    """
    raw = db.get_weekly_schedule(player_id, week_start)
    if raw is None:
        return None
    return WeeklySchedule.model_validate(raw)


def save_schedule(player_id: str, week_start: str, schedule: WeeklySchedule) -> None:
    """Persist a schedule model as JSON in the `weekly_schedules` table."""
    db.save_weekly_schedule(player_id, week_start, schedule.model_dump())


# ---- CLI ---------------------------------------------------------------------


def _cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.core.agents.session_designer",
        description="Design a weekly home-training schedule for one player.",
    )
    parser.add_argument("--player", required=True, help="Player id, e.g. felix")
    parser.add_argument("--week", required=True, help="Week start ISO date (Monday), e.g. 2026-04-22")
    parser.add_argument("--save", action="store_true", help="Persist the result to the weekly_schedules table")
    args = parser.parse_args(argv)

    schedule = design_week(args.player, args.week)
    print(json.dumps(schedule.model_dump(), indent=2, ensure_ascii=False))

    if args.save:
        save_schedule(args.player, args.week, schedule)
        print(f"\nSaved to weekly_schedules for ({args.player}, {args.week}).", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
